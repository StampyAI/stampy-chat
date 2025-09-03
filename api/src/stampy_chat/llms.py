from typing import TypedDict, Literal, Generator, Sequence

import anthropic
import openai
from google import genai
from stampy_chat.settings import ANTHROPIC, OPENAI, GOOGLE, OPENROUTER, MODELS, Settings
from stampy_chat.env import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENROUTER_API_KEY
from stampy_chat.citations import Message


class LLMChunk(TypedDict):
    type: Literal["thinking", "response"]
    text: str


def split_system(history: Sequence[Message]) -> tuple[str, list[Message]]:
    system = "\n\n".join([x["content"] for x in history if x["role"] == "system"])
    history = [x for x in history if x["role"] != "system"]
    return system, history


def call_anthropic(
    history: Sequence[Message],
    model: str,
    max_tokens: int,
    thinking_budget: int = 0,
    stream: bool = True,
) -> Generator[LLMChunk, None, None]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    params = {}
    if thinking_budget > 0:
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

    if stream:
        return anthropic_stream(response)
    else:
        return response.content[0].text


def anthropic_stream(response):
    for event in response:
        if event.type == "content_block_delta":
            if event.delta.type == "thinking_delta":
                yield LLMChunk(type="thinking", text=event.delta.thinking)
            elif event.delta.type == "text_delta":
                yield LLMChunk(type="response", text=event.delta.text)


def call_openai(
    history: Sequence[Message],
    model: str,
    max_tokens: int,
    thinking_budget: int = 0,
    stream: bool = False,
) -> Generator[LLMChunk, None, None]:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    system, history = split_system(history)
    params = {}
    if thinking_budget > 0:
        params["reasoning"] = {"effort": "medium"}

    response = client.responses.create(
        model=model,
        instructions=system,
        input=history,
        max_output_tokens=max_tokens,
        stream=True,
        **params,
    )
    if stream:
        return openai_stream(response)
    else:
        return response.choices[0].message.content


def openai_stream(response):
    for event in response:
        if event.type == "response.output_text.delta":
            yield LLMChunk(type="response", text=event.delta)


def call_google(
    history: Sequence[Message],
    model: str,
    max_tokens: int,
    thinking_budget: int = 0,
    stream: bool = False,
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
            model=model, contents=contents, config=config
        )

        def do_stream():
            for chunk in response:
                if hasattr(chunk, "text") and chunk.text:
                    yield LLMChunk(type="response", text=chunk.text)

        return do_stream()
    else:
        response = client.models.generate_content(
            model=model, contents=contents, config=config
        )

        return response.text


def call_openrouter(
    history: Sequence[Message],
    model: str,
    max_tokens: int,
    thinking_budget: int = 0,
    stream: bool = True,
) -> Generator[LLMChunk, None, None]:
    # Remove "openrouter/" prefix to get the actual model name
    if model.startswith("openrouter/"):
        model = model[len("openrouter/"):]
    
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    
    system, history = split_system(history)
    
    # Build messages
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.extend(history)
    
    # Build parameters
    params = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    
    # Add reasoning/thinking support for compatible models  
    extra_body = {}
    if thinking_budget > 0:
        # Use exact token count for more precise control (minimum 1024 per OpenRouter docs)
        extra_body["reasoning"] = {"max_tokens": thinking_budget}
        
    # Optional headers for attribution
    extra_headers = {}
    
    try:
        if extra_headers:
            params["extra_headers"] = extra_headers
        if extra_body:
            params["extra_body"] = extra_body
        
        response = client.chat.completions.create(**params)
        
        if stream:
            return openrouter_stream(response)
        else:
            return response.choices[0].message.content
    except Exception as e:
        print(f"WARNING: OpenRouter API error: {e}")
        # Could implement fallback to other providers like Anthropic does
        raise


def openrouter_stream(response):
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta:
            delta = chunk.choices[0].delta
            # Handle reasoning tokens if present
            if hasattr(delta, 'reasoning') and delta.reasoning:
                yield LLMChunk(type="thinking", text=delta.reasoning)
            # Handle regular content
            if delta.content:
                yield LLMChunk(type="response", text=delta.content)


def query_llm(
    history: Sequence[Message],
    settings: Settings,
    stream: bool = True,
    max_tokens: int | None = None,
    thinking_budget: int | None = None,
) -> Generator[LLMChunk, None, None]:
    provider = settings.model_provider
    if provider == ANTHROPIC:
        func = call_anthropic
    elif provider == OPENAI:
        func = call_openai
    elif provider == GOOGLE:
        func = call_google
    elif provider == OPENROUTER:
        func = call_openrouter
    else:
        raise ValueError(f"Unknown provider: {provider}")

    model_info = MODELS[settings.model]
    thinking_budget = thinking_budget or 0
    if model_info.can_think == "always" or (model_info.can_think and thinking_budget > 0):
        thinking_budget = max(model_info.min_think, thinking_budget)
    else:
        thinking_budget = 0

    return func(
        history,
        settings.model_id,
        max_tokens if max_tokens is not None else settings.max_response_tokens,
        thinking_budget,
        stream=stream,
    )
