from dataclasses import asdict
from typing import Any, Dict, Iterable, List

from langchain.chains import OpenAIModerationChain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.memory import ChatMessageHistory, ConversationSummaryBufferMemory
from langchain.prompts import (
    BaseChatPromptTemplate,
    ChatMessagePromptTemplate,
    ChatPromptTemplate, MessagesPlaceholder
)
from langchain.schema import BaseMessage, ChatMessage, SystemMessage
from langchain.vectorstores import Pinecone
from langchain.prompts import MessagesPlaceholder

from stampy_chat.followups import multisearch_authored
from stampy_chat import logging
from stampy_chat.env import OPENAI_API_KEY, PINECONE_INDEX, PINECONE_NAMESPACE
from stampy_chat.settings import Settings
from stampy_chat.citations import get_top_k_blocks


logger = logging.getLogger(__name__)
embeddings = OpenAIEmbeddings()
vectorstore = Pinecone(PINECONE_INDEX, embeddings.embed_query, "hash_id", namespace=PINECONE_NAMESPACE)


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

    max_history: int = 10

    def set_messages(self, history: List[dict]) -> None:
        """Replace the current list of messages with `history`, pruning as needed."""
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


class PrefixedPrompt(BaseChatPromptTemplate):
    """A prompt that will prefix any messages with a system prompt, but only if messages provided."""

    messages_field: str
    prompt: str  # the system prompt to be used

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        history = kwargs[self.messages_field]
        if history and self.prompt:
            return [SystemMessage(content=self.prompt)] + history
        return []


class ChatMultiItemPrompt(MessagesPlaceholder):

    template: ChatPromptTemplate

    def format_messages(self, **kwargs: Any) -> List[BaseMessage]:
        items = kwargs[self.variable_name]
        return [message for item in items for message in self.template.format_messages(**item)]


def get_model(**kwargs):
    return ChatOpenAI(openai_api_key=OPENAI_API_KEY, **kwargs)


def make_prompt(settings: Settings) -> ChatPromptTemplate:
    context_template = "[{{reference}}] {{title}} {{authors | join(', ')}} - {{date}} {{text}}"
    context_prompt = ChatMultiItemPrompt(
        template=ChatPromptTemplate.from_template(context_template, template_format="jinja2"),
        variable_name='context'
    )
    history_prompt = PrefixedPrompt(input_variables=['history'], messages_field='history', prompt=settings.history_prompt)

    query_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=settings.question_prompt),
        ChatMessagePromptTemplate.from_template(template='Q: {query}', role='user'),
    ])

    return ChatPromptTemplate.from_messages([
        SystemMessage(content=settings.context_prompt),
        context_prompt,
        history_prompt,
        query_prompt,
    ])


def prune_history(history: List[Dict], settings: Settings) -> List[BaseMessage]:
    memory = LimitedConversationSummaryBufferMemory(
        llm=get_model(),
        max_token_limit=settings.history_tokens,
        max_history=settings.maxHistory,
        chat_memory=ChatMessageHistory(),
        return_messages=True,
    )
    memory.set_messages(history)
    return memory.chat_memory.messages


def get_citations(query: str, settings: Settings):
    model = get_model()
    blocks = get_top_k_blocks(query, settings.topKBlocks)
    context = [dict(vals, index=i, reference=chr(i + 97)) for i, vals in enumerate(blocks)]

    tokensLeft = settings.context_tokens
    citations = []
    for c in context:
        tokens = model.get_num_tokens(c.get('text'))
        if tokens > tokensLeft:
            break
        tokensLeft -= tokens
        citations.append(c)
    return citations


def run_query(session_id: str, query: str, history: List[Dict], settings: Settings) -> Iterable[Dict[str, Any]]:
    try:
        yield {"state": "loading", "phase": "semantic"}
        context = get_citations(query, settings)
        yield {
            "state": "citations",
            "citations": [
                {'title': c.get('title'), 'author': c.get('authors'), 'date': c.get('date'), 'url': c.get('url')}
                for c in context
            ]
        }

        yield {"state": "loading", "phase": "checking history"}
        args = {'query': query, 'history': prune_history(history, settings), 'context': context}
        yield {"state": "loading", "phase": "prompt"}
        prompt = make_prompt(settings)
        prompt_text = prompt.format(**args)

        yield {"state": "loading", "phase": "moderation"}
        moderation_chain = OpenAIModerationChain(error=True)
        try:
            moderation_chain.run(prompt_text)
        except ValueError as e:
            raise ModerationError(e)

        chat_model = get_model(streaming=True, max_tokens=settings.max_response_tokens)
        response = ''
        for chunk in chat_model.stream(input=prompt_text):
            response += chunk.content
            print(chunk.content)
            yield {"state": "streaming", "content": chunk.content}

        yield {"state": "loading", "phase": "logging query"}
        logger.interaction(session_id, query, response, history, prompt_text, context)

        yield {"state": "loading", "phase": "followups"}
        followups = multisearch_authored([query, response])
        followups = list(map(asdict, followups))
        yield {"state": "followups", "followups": followups}

        yield {"state": "done"}
    except Exception as e:
        yield {"state": "error", "error": str(e)}
