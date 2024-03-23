from typing import Any, Callable, Dict, List

from langchain.chains import LLMChain, OpenAIModerationChain
from langchain_community.chat_models import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.memory import ChatMessageHistory, ConversationSummaryBufferMemory
from langchain.prompts import (
    BaseChatPromptTemplate,
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain.pydantic_v1 import Extra
from langchain.schema import AIMessage, BaseMessage, HumanMessage, PromptValue, SystemMessage

from stampy_chat.env import OPENAI_API_KEY, ANTHROPIC_API_KEY, COMPLETIONS_MODEL, LANGCHAIN_API_KEY, LANGCHAIN_TRACING_V2
from stampy_chat.settings import Settings, MODELS, OPENAI, ANTRHROPIC
from stampy_chat.callbacks import StampyCallbackHandler, BroadcastCallbackHandler, LoggerCallbackHandler
from stampy_chat.followups import StampyChain
from stampy_chat.citations import make_example_selector

from langsmith import Client

if LANGCHAIN_TRACING_V2 == "true":
    if not LANGCHAIN_API_KEY:
        raise Exception("Langsmith tracing is enabled but no api key was provided. Please set LANGCHAIN_API_KEY in the .env file.")
    client = Client()

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


def ChatMessage(m):
    if m['role'] == 'assistant':
        return AIMessage(**m)
    return HumanMessage(**m)


class PrefixedPrompt(BaseChatPromptTemplate):
    """A prompt that will prefix any messages with a system prompt, but only if messages are provided."""

    transformer: Callable[[Any], BaseMessage] = lambda i: i
    messages_field: str
    prompt: str  # the system prompt to be used

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        history = kwargs[self.messages_field]
        if history and self.prompt:
            return [AIMessage(content=self.prompt)] + [self.transformer(i) for i in history]
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

        messages = [ChatMessage(m) for m in history if m.get('role') != 'deleted']
        # If there are more than `max_history` messages, first summarize the older ones. If there
        # are n messages (where n > max_history), then the first `n - max_history + 1` should be
        # summarized and inserted as the first item in the history, so as to ensure there are
        # `max_history` items.
        if len(messages) > self.max_history :
            offset = -self.max_history + 1

            pruned = messages[:offset]
            summary = AIMessage(role='assistant', content=self.predict_new_summary(pruned, ''))

            messages = [summary] + messages[offset:]

        self.clear()
        self.chat_memory = ChatMessageHistory(messages=messages)
        self.prune()

        for callback in self.callbacks:
            callback.on_memory_set_end(self.chat_memory)

    def prune(self) -> None:
        """Prune buffer if it exceeds max token limit.

        This is the original Langchain version copied with a fix to handle the case when
        all messages are longer than the max_token_limit
        """
        buffer = self.chat_memory.messages
        curr_buffer_length = self.llm.get_num_tokens_from_messages(buffer)
        if curr_buffer_length > self.max_token_limit:
            pruned_memory = []
            while buffer and curr_buffer_length > self.max_token_limit:
                pruned_memory.append(buffer.pop(0))
                curr_buffer_length = self.llm.get_num_tokens_from_messages(buffer)
            self.moving_summary_buffer = self.predict_new_summary(
                pruned_memory, self.moving_summary_buffer
            )

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Because of how wonderfully LangChain is written, this method was blowing up.
        It's not needed, so it's getting the chop.
        """


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


class ChatAnthropicWrapper(ChatAnthropic):
    """Make sure the Anthropic endpoint can handle prompts.

    Anthropic only allows alternating human - ai messages, so join them up first.
    So much for langchain being plug'n'play...
    """
    def _format_params(self, *args, **kwargs):
        first = kwargs['messages'][0]
        # Anthropic requires the first message to be either a system or human message
        if isinstance(first, AIMessage):
            first = SystemMessage(content=first.content)

        messages = [first]
        for m in kwargs['messages'][1:]:
            if m.type != messages[-1].type:
                messages.append(m)
            else:
                messages[-1].content += '\n\n' + m.content
        kwargs['messages'] = messages
        return super()._format_params(*args, **kwargs)


def get_model(**kwargs):
    model = MODELS.get(kwargs.get('model'))
    if not model:
        raise ValueError("No model provided")
    if model.publisher == ANTRHROPIC:
        return ChatAnthropicWrapper(anthropic_api_key=ANTHROPIC_API_KEY, **kwargs)
    if model.publisher == OPENAI:
        return ChatOpenAI(openai_api_key=OPENAI_API_KEY, **kwargs)
    raise ValueError(f'Unsupported model: {kwargs.get("model")}')


class LLMInputsChain(LLMChain):

    inputs: Dict[str, Any] = {}

    def _call(self, inputs: Dict[str, Any], run_manager=None):
        self.inputs = inputs
        return super()._call(inputs, run_manager)

    def _acall(self, inputs: Dict[str, Any], run_manager=None):
        self.inputs = inputs
        return super()._acall(inputs, run_manager)

    def create_outputs(self, llm_result) -> List[Dict[str, Any]]:
        result = super().create_outputs(llm_result)
        return [dict(self.inputs, **r) for r in result]


def make_history_summary(settings):
    model = get_model(
        streaming=False,
        max_tokens=settings.maxHistorySummaryTokens,
        model=settings.completions
    )
    summary_prompt = PrefixedPrompt(
        input_variables=['history'],
        messages_field='history',
        prompt=settings.history_summary_prompt,
        transformer=ChatMessage,
    )
    return LLMInputsChain(
        llm=model,
        verbose=False,
        output_key='history_summary',
        prompt=ModeratedChatPrompt.from_messages([
            summary_prompt,
            ChatPromptTemplate.from_messages([
                HumanMessagePromptTemplate.from_template(template='Q: {query}', role='user'),
            ]),
            HumanMessage(content="Reply in one sentence only"),
        ]),
    )


def make_prompt(settings, chat_model, callbacks):
    """Create a proper prompt object will all the nessesery steps."""
    # 1. Create the context prompt from items fetched from pinecone
    context_template = "[{{reference}}] {{title}} {{authors | join(', ')}} - {{date_published}} {{text}}"
    context_prompt = MessageBufferPromptTemplate(
        example_selector=make_example_selector(k=settings.topKBlocks, callbacks=callbacks),
        example_prompt=ChatPromptTemplate.from_template(context_template, template_format="jinja2"),
        get_num_tokens=chat_model.get_num_tokens,
        max_tokens=settings.context_tokens,
        input_variables=['query', 'history'],
    )

    # 2. The history items will be passed in from the memory
    history_prompt = PrefixedPrompt(input_variables=['history'], messages_field='history', prompt=settings.history_prompt)

    # 3. Construct the main query
    query_prompt = ChatPromptTemplate.from_messages(
        [
            HumanMessage(content=settings.question_prompt),
            HumanMessagePromptTemplate.from_template(template='Q: {history_summary}: {query}', role='user'),
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
        llm=get_model(model=COMPLETIONS_MODEL),  # used for summarization
        max_token_limit=settings.history_tokens,
        max_history=settings.maxHistory,
        chat_memory=ChatMessageHistory(),
        return_messages=True,
        callbacks=callbacks
    )
    memory.set_messages([i for i in history if i.get('role') != 'deleted'])
    return memory


def merge_history(history):
    """Merge subsequent messages into a single one.

    ChatGPT works pretty much by alternating assistant and user queries. On the other
    hand, systems like Slack or Discord will often have multiple messages as responses,
    as people tend to write a few shorter messages rather than one big one. This function
    will transform the later type of history into the former, so the LLM has an easier job.
    """
    if not history:
        return history

    messages = []
    current_message = history[0]
    for message in history[1:]:
        if message.get('role') == 'deleted':
            continue
        if message.get('role') != current_message.get('role'):
            messages.append(current_message)
            current_message = message
        else:
            current_message['content'] += '\n' + message.get('content', '')
    messages.append(current_message)
    return messages


def run_query(session_id: str, query: str, history: List[Dict], settings: Settings, callback: Callable[[Any], None] = None, followups=True) -> Dict[str, str]:
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

    history = merge_history(history)
    chat_model = get_model(
        streaming=True,
        callbacks=callbacks,
        max_tokens=settings.max_response_tokens,
        model=settings.completions
    )

    chain = make_history_summary(settings) | LLMChain(
        llm=chat_model,
        verbose=False,
        prompt=make_prompt(settings, chat_model, callbacks),
        memory=make_memory(settings, history, callbacks)
    )
    if followups:
        chain = chain | StampyChain(callbacks=callbacks)
    result = chain.invoke({"query": query, 'history': history}, {'callbacks': []})
    if callback:
        callback({'state': 'done'})
        callback(None)  # make sure the callback handler know that things have ended
    return result
