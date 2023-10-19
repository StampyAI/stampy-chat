from typing import Any, Callable, Dict, List

from langchain.chains import LLMChain, OpenAIModerationChain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ChatMessageHistory, ConversationSummaryBufferMemory
from langchain.prompts import (
    BaseChatPromptTemplate,
    ChatMessagePromptTemplate,
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate
)
from langchain.pydantic_v1 import Extra
from langchain.schema import BaseMessage, ChatMessage, PromptValue, SystemMessage

from stampy_chat.env import OPENAI_API_KEY
from stampy_chat.settings import Settings
from stampy_chat.callbacks import StampyCallbackHandler, BroadcastCallbackHandler, LoggerCallbackHandler
from stampy_chat.followups import StampyChain
from stampy_chat.citations import make_example_selector


class ModerationError(ValueError):
    pass


class MessageBufferPromptTemplate(FewShotChatMessagePromptTemplate):
    """A prompt template that will return no more than `max_tokens` tokens.

    This will format any provided messages according to the provided prompt, then
    return the first n formatted messages such that `sum(tokens(messages)) < max_tokens`.
    """

    get_num_tokens: Callable[[str], int]  # the function used to calculate the number of tokens in a string
    max_tokens: int

    class Config:
        """This is needed for extra fields to be added..."""
        extra = Extra.forbid
        arbitrary_types_allowed = True

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        """Format the provided messages and return as many as possible without going over the allowed number of tokens."""
        all_messages = super().format_messages(**kwargs)

        messages = []
        remaining_tokens = self.max_tokens
        for message in all_messages:
            tokens = self.get_num_tokens(message.content)
            if tokens > remaining_tokens:
                break

            remaining_tokens -= tokens
            messages.append(message)
        return messages


class PrefixedPrompt(BaseChatPromptTemplate):
    """A prompt that will prefix any messages with a system prompt, but only if messages provided."""

    messages_field: str
    prompt: str  # the system prompt to be used

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        history = kwargs[self.messages_field]
        if history and self.prompt:
            return [SystemMessage(content=self.prompt)] + history
        return []


class LimitedConversationSummaryBufferMemory(ConversationSummaryBufferMemory):
    """A Summary Buffer with both a limit on the number of messages in history, and a summary if limits are exeeded.

    The basic ConversationSummaryBufferMemory will make a LLM summary of the history if the current
    list of messages is too large (in tokens, not messages). This class expands that with an additional
    limit on the number of messages. So if the history has more than `max_history` entries, the first
    `n - max_history + 1` items will be summarized and used as the first history entry. Of course, if
    that's still too large (in tokens), the whole history may be summarized.

    This class can also be provided with optional callbacks, which will be notified before and after
    any memory replacements happen.
    """

    callbacks: List[StampyCallbackHandler] = []
    max_history: int = 10

    def set_messages(self, history: List[dict]) -> None:
        """Replace the current list of messages with `history`, pruning as needed."""
        for callback in self.callbacks:
            callback.on_memory_set_start(history)

        messages = [ChatMessage(**m) for m in history]
        # If there are more than `max_history` messages, first summarize the older ones. If there
        # are n messages (where n > max_history), then the first `n - max_history + 1` should be
        # summarized and inserted as the first item in the history, so as to ensure there are
        # `max_history` items.
        if len(messages) > self.max_history :
            offset = -self.max_history + 1

            pruned = messages[:offset]
            summary = ChatMessage(role='assistant', content=self.predict_new_summary(pruned, ''))

            messages = [summary] + messages[offset:]

        self.clear()
        self.chat_memory = ChatMessageHistory(messages=messages)
        self.prune()

        for callback in self.callbacks:
            callback.on_memory_set_end(self.chat_memory)


class ModeratedChatPrompt(ChatPromptTemplate):
    """Wraps a prompt with an OpenAI moderation check which will raise an exception if fails."""

    moderation_chain: OpenAIModerationChain = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.moderation_chain:
            self.moderation_chain = OpenAIModerationChain(error=True, openai_api_key=OPENAI_API_KEY)

    def format_prompt(self, **kwargs: Any) -> PromptValue:
        """Raise an exception if the prompt is flagged as offensive by OpenAI."""
        prompt = super().format_prompt(**kwargs)
        try:
            self.moderation_chain.run(prompt.to_string())
        except ValueError as e:
            raise ModerationError(e)
        return prompt


def get_model(**kwargs):
    return ChatOpenAI(openai_api_key=OPENAI_API_KEY, **kwargs)


def make_prompt(settings, chat_model, callbacks):
    """Create a proper prompt object will all the nessesery steps."""
    # 1. Create the context prompt from items fetched from pinecone
    context_template = "[{{reference}}] {{title}} {{authors | join(', ')}} - {{date_published}} {{text}}"
    context_prompt = MessageBufferPromptTemplate(
        example_selector=make_example_selector(k=settings.topKBlocks, callbacks=callbacks),
        example_prompt=ChatPromptTemplate.from_template(context_template, template_format="jinja2"),
        get_num_tokens=chat_model.get_num_tokens,
        max_tokens=settings.context_tokens,
        input_variables=['query'],
    )

    # 2. The history items will be passed in from the memory
    history_prompt = PrefixedPrompt(input_variables=['history'], messages_field='history', prompt=settings.history_prompt)

    # 3. Construct the main query
    query_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=settings.question_prompt),
            ChatMessagePromptTemplate.from_template(template='Q: {query}', role='user'),
        ]
    )

    # 4. ModeratedChatPrompt will cause the whole chain to fail if untoward values are provided
    return ModeratedChatPrompt.from_messages([
        SystemMessage(content=settings.context_prompt),
        context_prompt,
        history_prompt,
        query_prompt,
    ])


def make_memory(settings, history, callbacks):
    """Create a memory object to store the chat history."""
    memory = LimitedConversationSummaryBufferMemory(
        llm=get_model(),
        max_token_limit=settings.history_tokens,
        max_history=settings.maxHistory,
        chat_memory=ChatMessageHistory(),
        return_messages=True,
        callbacks=callbacks
    )
    memory.set_messages([i for i in history if i.get('role') != 'deleted'])
    return memory


def run_query(session_id: str, query: str, history: List[Dict], settings: Settings, callback: Callable[[Any], None] = None) -> Dict[str, str]:
    """Execute the query.

    :param str query: the phrase that was input by the user
    :param List[Dict] history: any previous interactions with the user
    :param Settings settings: the system settings
    :param Callable[[Any], None] callback: an optional callback that will be called at various key parts of the chain
    :returns: the result of the chain
    """
    callbacks = [LoggerCallbackHandler(session_id=session_id, query=query, history=history)]
    if callback:
        callbacks += [BroadcastCallbackHandler(callback)]
    chat_model = get_model(
        streaming=True,
        callbacks=callbacks,
        max_tokens=settings.max_response_tokens,
        model=settings.completions
    )

    chain = LLMChain(
        llm=chat_model,
        verbose=False,
        prompt=make_prompt(settings, chat_model, callbacks),
        memory=make_memory(settings, history, callbacks)
    ) | StampyChain(callbacks=callbacks)
    result = chain.invoke({"query": query, 'history': history}, {'callbacks': []})

    if callback:
        callback({'state': 'done'})
        callback(None)  # make sure the callback handler know that things have ended
    return result
