from unittest.mock import patch
from langchain_community.llms import FakeListLLM
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate


from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from stampy_chat.settings import Settings
from stampy_chat.callbacks import StampyCallbackHandler
from stampy_chat.chat import (
    LimitedConversationSummaryBufferMemory,
    MessageBufferPromptTemplate,
    PrefixedPrompt,
    make_memory,
    merge_history,
)


def make_prompt_template(max_tokens, examples):
    template = ChatPromptTemplate.from_template("{content}")
    return MessageBufferPromptTemplate(
        example_prompt=template,
        get_num_tokens=lambda s: len(s),
        max_tokens=max_tokens,
        examples=examples,
    )


def test_MessageBufferPromptTemplate_format_messages():
    template = make_prompt_template(
        100,
        [
            {"content": "bla bla bla"},
            {"content": "ble ble ble"},
            {"content": "and some more"},
        ],
    )
    assert template.format_messages() == [
        HumanMessage(content="bla bla bla"),
        HumanMessage(content="ble ble ble"),
        HumanMessage(content="and some more"),
    ]


def test_MessageBufferPromptTemplate_format_messages_truncated():
    template = make_prompt_template(
        20,
        [
            {"content": "bla bla bla"},
            {"content": "ble ble ble"},
            {"content": "and some more"},
        ],
    )
    assert template.format_messages() == [
        HumanMessage(content="bla bla bla"),
    ]


def test_MessageBufferPromptTemplate_format_all_messages_truncated():
    template = make_prompt_template(
        10,
        [
            {"content": "bla bla bla"},
            {"content": "ble ble ble"},
            {"content": "and some more"},
        ],
    )
    assert template.format_messages() == []


def test_PrefixedPrompt_format_messages():
    prompt = PrefixedPrompt(
        messages_field="history", prompt="bla bla bla", input_variables=[]
    )
    history = [HumanMessage(content=f"human message {i}") for i in range(5)]
    assert prompt.format_messages(history=history) == [
        HumanMessage(content="bla bla bla"),
        HumanMessage(content="human message 0"),
        HumanMessage(content="human message 1"),
        HumanMessage(content="human message 2"),
        HumanMessage(content="human message 3"),
        HumanMessage(content="human message 4"),
    ]


def test_PrefixedPrompt_format_messages_no_history():
    prompt = PrefixedPrompt(
        messages_field="history", prompt="bla bla bla", input_variables=[]
    )
    assert prompt.format_messages(history=[]) == []


def test_LimitedConversationSummaryBufferMemory_set_empty():
    llm = FakeListLLM(responses=["this is a summary of what was before"])
    memory = LimitedConversationSummaryBufferMemory(llm=llm)
    memory.chat_memory = InMemoryChatMessageHistory(
        messages=[HumanMessage(content="bla bla bla")]
    )

    memory.set_messages([])
    assert memory.chat_memory == InMemoryChatMessageHistory(messages=[])


def test_LimitedConversationSummaryBufferMemory_set():
    llm = FakeListLLM(responses=["this is a summary of what was before"])
    memory = LimitedConversationSummaryBufferMemory(llm=llm)

    memory.set_messages(
        [
            SystemMessage(content="a system message"),
            HumanMessage(content="bla bla bla"),
        ]
    )
    assert memory.chat_memory == InMemoryChatMessageHistory(
        messages=[
            SystemMessage(content="a system message"),
            HumanMessage(content="bla bla bla"),
        ]
    )


def test_LimitedConversationSummaryBufferMemory_set_more():
    llm = FakeListLLM(responses=["this is a summary of what was before"])
    memory = LimitedConversationSummaryBufferMemory(llm=llm, max_history=4)

    memory.set_messages(
        [
            SystemMessage(content="a system message"),
            HumanMessage(content="message 1 - should be summarized"),
            HumanMessage(content="message 2 - should be summarized"),
            HumanMessage(content="message 3 - should be kept"),
            HumanMessage(content="message 4 - should be kept"),
            HumanMessage(content="message 5 - should be kept"),
        ]
    )
    assert memory.chat_memory == InMemoryChatMessageHistory(
        messages=[
            AIMessage(content="this is a summary of what was before"),
            HumanMessage(content="message 3 - should be kept"),
            HumanMessage(content="message 4 - should be kept"),
            HumanMessage(content="message 5 - should be kept"),
        ]
    )


def test_LimitedConversationSummaryBufferMemory_set_with_callbacks():
    callback_calls = {}

    class DummyCallback(StampyCallbackHandler):
        def on_memory_set_start(self, history):
            callback_calls["start"] = history

        def on_memory_set_end(self, messages):
            callback_calls["end"] = messages

    llm = FakeListLLM(responses=["this is a summary of what was before"])
    memory = LimitedConversationSummaryBufferMemory(
        llm=llm, callbacks=[DummyCallback()]
    )
    history = [
        SystemMessage(content="a system message"),
        HumanMessage(content="bla bla bla"),
    ]

    memory.set_messages(history)
    assert memory.chat_memory == InMemoryChatMessageHistory(
        messages=[
            SystemMessage(content="a system message"),
            HumanMessage(content="bla bla bla"),
        ]
    )
    assert callback_calls == {
        "start": history,
        "end": memory.chat_memory,
    }


def test_merge_history_empty():
    assert merge_history([]) == []


def test_merge_history_no_merges():
    history = [
        {"content": "this should be kept", "role": "system"},
        {"content": "as should this", "role": "human"},
        {"content": "this will be ignored", "role": "deleted"},
        {"content": "bla bla bla", "role": "assistant"},
        {"content": "remove me!!", "role": "deleted"},
    ]
    assert merge_history(history) == [
        SystemMessage(content="this should be kept"),
        HumanMessage(content="as should this"),
        AIMessage(content="bla bla bla"),
    ]


def test_merge_history_merges():
    history = [
        {"role": "user", "content": "question 1"},
        {"role": "assistant", "content": "answer 1 part 1"},
        {"role": "assistant", "content": "answer 1 part 2"},
        {"role": "user", "content": "question 2 part 1"},
        {"role": "user", "content": "question 2 part 2"},
        {"role": "user", "content": "question 2 part 3"},
        {"role": "assistant", "content": "answer 2"},
        {"role": "user", "content": "question 3"},
        {"role": "assistant", "content": "answer 3"},
        {"role": "user", "content": "question 4 part 1"},
        {"role": "user", "content": "question 4 part 2"},
    ]
    assert merge_history(history) == [
        HumanMessage(content="question 1"),
        AIMessage(content="answer 1 part 1\nanswer 1 part 2"),
        HumanMessage(content="question 2 part 1\nquestion 2 part 2\nquestion 2 part 3"),
        AIMessage(content="answer 2"),
        HumanMessage(content="question 3"),
        AIMessage(content="answer 3"),
        HumanMessage(content="question 4 part 1\nquestion 4 part 2"),
    ]
