from typing import TypedDict, Literal, Generator

from anthropic import Anthropic
from openai import OpenAI
from stampy_chat.settings import ANTHROPIC, OPENAI, Settings
from stampy_chat.env import OPENAI_API_KEY, ANTHROPIC_API_KEY


class LLMChunk(TypedDict):
    type: Literal["thinking", "response"]
    text: str


def can_think(model: str, thinking_budget: int) -> bool:
    return (
        model.startswith("claude-sonnet-3.7")
        or model.startswith("claude-sonnet-4")
        or model.startswith("claude-opus-4")
    ) and thinking_budget >= 1024


def call_anthropic(
    prompt: str, model: str, max_tokens: int, thinking_budget: int = 0
) -> Generator[LLMChunk, None, None]:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    params = {}
    if can_think(model, thinking_budget):
        params["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

    response = client.messages.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        stream=True,
        **params,
    )
    for event in response:
        if event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                yield LLMChunk(type="thinking", text=event.delta.thinking)
            elif event.delta.type == "text_delta":
                yield LLMChunk(type="response", text=event.delta.text)


def call_openai(
    prompt: str, model: str, max_tokens: int, thinking_budget: int = 0
) -> Generator[LLMChunk, None, None]:
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": prompt}],
        max_output_tokens=max_tokens,
        reasoning={"effort": "medium"} if thinking_budget else None,
        stream=True,
    )
    for event in response:
        if event.type == "response.output_text.delta":
            yield LLMChunk(type="response", text=event.delta)


def query_llm(prompt: str, settings: Settings) -> Generator[LLMChunk, None, None]:
    provider = settings.completions_model_provider
    if provider == ANTHROPIC:
        func = call_anthropic
    elif provider == OPENAI:
        func = call_openai
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return func(
        prompt,
        settings.completions_model_name,
        settings.max_response_tokens,
        settings.thinking_budget,
    )
