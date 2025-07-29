from typing import TypedDict, Literal, Generator
from dataclasses import dataclass

import anthropic
import openai
from google import genai
from stampy_chat.settings import ANTHROPIC, OPENAI, GOOGLE, Settings
from stampy_chat.env import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY
from stampy_chat.citations import Message


class LLMChunk(TypedDict):
    type: Literal["thinking", "response"]
    text: str


def can_think(model: str, thinking_budget: int) -> bool:
    return (
        model.startswith("claude-sonnet-3.7")
        or model.startswith("claude-sonnet-4")
        or model.startswith("claude-opus-4")
    ) and thinking_budget >= 1024


def split_system(history: list[Message]) -> list[Message]:
    system = "\n\n".join([x["content"] for x in history if x["role"] == "system"])
    history = [x for x in history if x["role"] != "system"]
    return system, history


def call_anthropic(
    history: list[Message], model: str, max_tokens: int, thinking_budget: int = 0, stream: bool = True
) -> Generator[LLMChunk, None, None]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    params = {}
    if can_think(model, thinking_budget):
        params["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

    system, history = split_system(history)

    try:
        response = client.messages.create(
            model=model,
            messages=history,
            system=system,
            max_tokens=max_tokens,
            stream=stream,
            **params,
        )
    except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
        print("WARNING: falling back to google due to anthropic api error:", e)
        return call_google(history, model, max_tokens, thinking_budget, stream)

    if stream: return anthropic_stream(response)
    else:      return response.content[0].text

def anthropic_stream(response):
    for event in response:
        if event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                yield LLMChunk(type="thinking", text=event.delta.thinking)
            elif event.delta.type == "text_delta":
                yield LLMChunk(type="response", text=event.delta.text)


def call_openai(
    history: list[Message], model: str, max_tokens: int, thinking_budget: int = 0, stream: bool = False
) -> Generator[LLMChunk, None, None]:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    system, history = split_system(history)
    response = client.responses.create(
        model=model,
        input=([{"role": "system", "content": system}] if system else [])
            + history,
        max_output_tokens=max_tokens,
        reasoning={"effort": "medium"} if thinking_budget else None,
        stream=True,
    )
    if stream: return openai_stream(response)
    else:      return response.choices[0].message.content

def openai_stream(response):
    for event in response:
        if event.type == "response.output_text.delta":
            yield LLMChunk(type="response", text=event.delta)


def call_google(
    history: list[Message], model: str, max_tokens: int, thinking_budget: int = 0
) -> Generator[LLMChunk, None, None]:
    client = genai.Client(api_key=GOOGLE_API_KEY)
    system, history = split_system(history)
    
    # Convert to Gemini's Content format
    contents = []
    for msg in history:
        # Map assistant to model for Gemini
        role = "model" if msg["role"] == "assistant" else msg["role"]
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Build config parameters
    config_params = {
        "max_output_tokens": max_tokens,
        "thinking_config": genai.types.ThinkingConfig(thinking_budget=thinking_budget),
    }

    # Add system instruction if provided
    if system:
        config_params["system_instruction"] = system

    config = genai.types.GenerateContentConfig(**config_params)

    # Use streaming API
    if stream:
        response = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config
        )

        def do_stream():
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield LLMChunk(type="response", text=chunk.text)
        return do_stream()
    else:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

        return response.text


def query_llm(history: list[Message], settings: Settings, stream: bool = True, max_tokens: int|None=None, thinking_budget: int|None = None) -> Generator[LLMChunk, None, None]:
    provider = settings.completions_model_provider
    if provider == ANTHROPIC:
        func = call_anthropic
    elif provider == OPENAI:
        func = call_openai
    elif provider == GOOGLE:
        func = call_google
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return func(
        history,
        settings.completions_model_name,
        max_tokens if max_tokens is not None else settings.max_response_tokens,
        thinking_budget if thinking_budget is not None else settings.thinking_budget,
        stream=stream
    )
