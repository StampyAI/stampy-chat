#!/usr/bin/env python3
"""
Simple API client for testing the Stampy chat server.
"""

import json
import uuid
import requests
import csv
import subprocess
import hashlib
import os
import glob
import re
from datetime import datetime
from typing import Any, Optional
from frozendict import frozendict

from stampy_chat import settings

import anthropic
from google import genai


def strip_version_suffix(filename_without_ext: str) -> str:
    """Remove version suffix pattern -[0-9]+-[a-zA-Z0-9]{6} from filename."""
    pattern = r'-\d+-[a-zA-Z0-9]{6}$'
    return re.sub(pattern, '', filename_without_ext)


def _resolve_prompt_name(incoming_name: str, prompts: dict[str, str]) -> str:
    """Resolve prompt name, with fallback matching for versioned prompts.

    If incoming_name doesn't exist in prompts, look for prompts that match
    the pattern incoming_name + version suffix, and return the maximum match.
    """
    # If exact match exists, return it
    if incoming_name in prompts:
        return incoming_name

    # Pattern to match versioned prompts: incoming_name followed by -timestamp-hash
    pattern = f"^{re.escape(incoming_name)}-[0-9]+-[a-zA-Z0-9]{{6}}$"

    matching_prompts = []
    for prompt_name in prompts.keys():
        if re.match(pattern, prompt_name):
            matching_prompts.append(prompt_name)

    if matching_prompts:
        # Return the maximum (latest) matching prompt
        return max(matching_prompts)

    # If no matches found, return the original name
    return incoming_name


def parse_config(config: str, prompts: dict[str, str]) -> frozendict:
    """Parse config string into a frozendict structure.

    Args:
        config: String with model and settings separated by |
        prompts: dict of available prompts for name matching
    """
    parts = config.lower().split('|')
    result = {'model': None, 'data': None}

    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            # Handle prompt name matching for any key if prompts dict is provided
            value = _resolve_prompt_name(value, prompts)
            result[key] = value
        else:
            # Handle parts without '=' - assume they're model or context names
            models = ('claude', 'gpt', 'gemini', 'deepseek', 'gemma', 'llama', 'mistral', 'o1', 'o3', 'o4', 'qwen')
            if any(part.startswith(model) for model in models):
                result['model'] = part
            else:
                result['data'] = part

    return frozendict(result)

def format_config(config: frozendict[str, str]) -> str:
    res = []
    config = dict(config)

    model = config.pop("model")
    data = config.pop("data", None)
    res.append(model)
    if data: res.append(data)

    for key, value in sorted(config.items(), key=lambda x: (len(x), x)):
        res.append(f"{key}={value}")

    return "|".join(res)


def load_prompts() -> dict[str, str]:
    """Load all prompts from ~/prompts directory with versioned names."""
    prompts = {}
    prompts_dir = os.path.expanduser("~/prompts")

    # Create prompts directory if it doesn't exist
    if not os.path.exists(prompts_dir):
        os.makedirs(prompts_dir, exist_ok=True)

    # First, process settings prompts
    settings_stat = os.stat(os.path.abspath(settings.__file__))
    settings_time = datetime.fromtimestamp(settings_stat.st_mtime)
    time_str = settings_time.strftime("%y%m%d%H%M")

    # Load from settings.DEFAULT_PROMPTS (skip non-string values like 'modes')
    for prompt_name, prompt_content in settings.DEFAULT_PROMPTS.items():
        if isinstance(prompt_content, str):
            _process_settings_prompt(prompts_dir, prompt_name.lower(), prompt_content, time_str, prompts)

    # Now find all .md and .txt files in the prompts directory
    for pattern_ext in ["*.md", "*.txt"]:
        for file_path in glob.glob(os.path.join(prompts_dir, pattern_ext)):
            # Load file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Get file stats
            file_stat = os.stat(file_path)

            # Generate SHA256 hash of content
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:6]

            # Get filename without extension and strip any existing version suffix
            filename = os.path.basename(file_path)
            name_without_ext = os.path.splitext(filename)[0]
            clean_name = strip_version_suffix(name_without_ext)

            # Format modification time as yymmddHHMM
            mtime = datetime.fromtimestamp(file_stat.st_mtime)
            file_time_str = mtime.strftime("%y%m%d%H%M")

            # Create versioned key and new filename
            key = f"{clean_name}-{file_time_str}-{content_hash}"
            new_filename = f"{key}{os.path.splitext(filename)[1]}"
            new_file_path = os.path.join(prompts_dir, new_filename)

            # Rename the file if the new name is different
            if file_path != new_file_path:
                os.rename(file_path, new_file_path)

            prompts[key] = content

    return prompts


def _process_settings_prompt(prompts_dir: str, name: str, content: str, time_str: str, prompts: dict[str, str]) -> None:
    """Process a settings prompt: check for duplicates and save if new."""
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:6]

    # Check if any existing file has matching hash and content
    for pattern_ext in ["*.md", "*.txt"]:
        for existing_file in glob.glob(os.path.join(prompts_dir, pattern_ext)):
            # Skip if hash in filename doesn't match
            existing_filename = os.path.basename(existing_file)
            if content_hash not in existing_filename:
                continue

            with open(existing_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()

            existing_hash = hashlib.sha256(existing_content.encode()).hexdigest()[:6]
            if existing_hash == content_hash and existing_content == content:
                # Found duplicate, don't save but add to prompts
                filename = os.path.basename(existing_file)
                name_without_ext = os.path.splitext(filename)[0]
                clean_name = strip_version_suffix(name_without_ext)

                file_stat = os.stat(existing_file)
                mtime = datetime.fromtimestamp(file_stat.st_mtime)
                file_time_str = mtime.strftime("%y%m%d%H%M")

                key = f"{clean_name}-{file_time_str}-{content_hash}"
                prompts[key] = content
                return

    # No duplicate found, save new file
    key = f"stampy-{name}-{time_str}-{content_hash}"
    filename = f"{key}.txt"
    file_path = os.path.join(prompts_dir, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    prompts[key] = content


def load_csv(file_path: str, prompts: dict[str, str]) -> dict[str, dict[str, str]]:
    """Load CSV file into question-major dict representation."""
    result = {}

    configs_dict = {}
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = row.get('', '')  # First column should be empty header for questions
            if not question:
                continue

            question_responses = {}
            for config, response in row.items():
                if config == '': continue # question column

                if config in configs_dict:
                    config = configs_dict[config]
                else:
                    config = configs_dict[config] = parse_config(config, prompts)

                # Add all configs, even with empty responses
                question_responses[config] = response

            if question_responses:
                result[question] = question_responses

    return result


def save_csv(data: dict[str, dict[str, str]], file_path: str) -> None:
    """Save question-major dict to CSV format."""
    if not data:
        return

    # Collect all unique config across all questions
    all_configs = set()
    for question_responses in data.values():
        all_configs.update(question_responses.keys())

    all_configs = sorted(list(all_configs), key=lambda x: format_config(x))

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        # Write header
        writer = csv.writer(f)
        writer.writerow([''] + [format_config(config) for config in all_configs])

        # Write data rows
        for question, responses in data.items():
            row = [question]
            for config in all_configs:
                row.append(responses.get(config, ''))
            writer.writerow(row)


def stampy(
    *,
    messages: list[str],
    system: str = settings.SOURCE_PROMPT,
    history_prompt: str = settings.HISTORY_PROMPT,
    pre_question: str = settings.QUESTION_PROMPT,
    question_marker: str = settings.QUESTION_MARKER,
    modes: Optional[dict] = None,
    session_id: Optional[str] = None,
    url: str = "http://127.0.0.1:3001/chat",
    mode: str = "default",
    model: str = "claude-sonnet-4-20250514",
    stream: bool = False,
    **kwargs
) -> dict[str, Any]:
    if len(messages) % 2 == 0:
        raise ValueError("Messages list must have odd length (ending with user message)")

    our_modes = dict(settings.PROMPT_MODES)
    if modes:
        our_modes = dict(our_modes, **modes)

    # Convert alternating messages to history format
    history = []
    for i, content in enumerate(messages[:-1]):  # All but the last message
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": content})

    # Last message is the current query
    query = messages[-1]

    # Build settings
    request_settings = {
        "prompts": {
            "context": system,
            "history": history_prompt,
            "history_summary": history_prompt,  # TODO: this should probably be different
            "question": pre_question,
            "question_marker": question_marker,
            "modes": our_modes
        },
        "mode": mode,
        "completions": model,
        "encoder": "cl100k_base",
        "topKBlocks": 50,
        "maxNumTokens": 8000,
        "tokensBuffer": 50,
        "maxHistory": 10,
        "maxHistorySummaryTokens": 200,
        "historyFraction": 0.25,
        "contextFraction": 0.5,
        **kwargs
    }

    # Build request payload
    payload = {
        "sessionId": session_id or str(uuid.uuid4()),
        "query": query,
        "history": history,
        "settings": request_settings,
        "stream": stream
    }


    # Make request
    response = requests.post(
        url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json"
        }
    )

    response.raise_for_status()

    if stream:
        # Parse streaming response
        return _parse_streaming_response(response.text)
    else:
        # Non-streaming response - note: server may always return streaming format
        try:
            return {"reply": response.json(), "full_context": ""}
        except:
            # Fallback to parsing as streaming response if JSON parse fails
            return _parse_streaming_response(response.text)


def _parse_streaming_response(response_text: str) -> dict[str, Any]:
    """Parse the streaming response format."""
    lines = response_text.strip().split('\n')

    citations = []
    prompt = ""
    content_parts = []
    followups = []

    for line in lines:
        if line.startswith('data: '):
            data_str = line[6:]  # Remove 'data: ' prefix
            if data_str.strip():
                try:
                    data = json.loads(data_str)
                    if data.get("state") == "citations":
                        citations = data.get("citations", [])
                    elif data.get("state") == "prompt":
                        prompt = data.get("prompt", "")
                    elif data.get("state") == "streaming":
                        content = data.get("content", "")
                        if content:
                            content_parts.append(content)
                    elif data.get("state") == "followups":
                        followups = data.get("followups", [])
                except json.JSONDecodeError:
                    continue

    reply = "".join(content_parts)

    return {
        "reply": reply,
        "full_context": prompt,
        "citations": citations,
        "followups": followups
    }


def _prepare_messages(messages: list[str], fm_template: str, fm_head_inject: Optional[str], fm_bottom_inject: Optional[str]):
    if len(messages) % 2 == 0:
        raise ValueError("Messages list must have odd length (ending with user message)")

    # Convert alternating messages to OpenAI/Anthropic/etc format
    api_messages = []
    for i, content in enumerate(messages[:-1]):  # All but the last message
        role = "user" if i % 2 == 0 else "assistant"
        api_messages.append({"role": role, "content": content})

    # Handle the final message with template and injections
    final_message = messages[-1]
    chunks = [fm_template.format(final_message=final_message)]
    if fm_head_inject:
        chunks.insert(0, fm_head_inject)
    if fm_bottom_inject:
        chunks.append(fm_bottom_inject)
    final_message_content = "\n\n".join(chunks)

    api_messages.append({"role": "user", "content": final_message_content})

    return api_messages


def anthropic_client(
    messages: list[str],
    final_message_template: str = "<user-message>\n{final_message}\n</user-message>",
    final_head_inject: Optional[str] = None,
    final_bottom_inject: Optional[str] = None,
    system: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
) -> dict[str, Any]:
    """Direct Anthropic API client with alternating message format.

    Args:
        messages: list of alternating user/assistant messages (must be odd length, ending with user message)
        final_message_template: Template for formatting the final message
        final_head_inject: Optional content to inject at the head of the final message
        final_bottom_inject: Optional content to inject at the bottom of the final message
        system: Optional system prompt
        model: Anthropic model to use
        max_tokens: Maximum tokens in response
        temperature: Optional temperature parameter (0.0-1.0)
        top_p: Optional top_p parameter (0.0-1.0)
        **kwargs: Additional parameters for the Anthropic API

    Returns:
        dict with 'reply' key containing the response text
    """
    api_messages = _prepare_messages(messages, final_message_template, final_head_inject, final_bottom_inject)

    # Build API call parameters
    api_params = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": api_messages,
    }

    if system:
        api_params["system"] = system
    if temperature is not None:
        api_params["temperature"] = temperature
    if top_p is not None:
        api_params["top_p"] = top_p

    # Make API call
    client = anthropic.Anthropic()
    response = client.messages.create(**api_params)

    # Extract reply text
    reply = ""
    for block in response.content:
        if hasattr(block, 'text'):
            reply += block.text

    return {
        "reply": reply,
        "full_context": None,
        "citations": None,
        "followups": None
    }


def gemini_client(
    messages: list[str],
    final_message_template: str = "<user-message>\n{final_message}\n</user-message>",
    final_head_inject: Optional[str] = None,
    final_bottom_inject: Optional[str] = None,
    system: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    max_tokens: int = 4096,
    thinking_budget: int = 0,  # Disable thinking by default for speed
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
) -> dict[str, Any]:
    """Direct Gemini API client with alternating message format.

    Args:
        messages: list of alternating user/assistant messages (must be odd length, ending with user message)
        final_message_template: Template for formatting the final message
        final_head_inject: Optional content to inject at the head of the final message
        final_bottom_inject: Optional content to inject at the bottom of the final message
        system_instruction: Optional system instruction
        model: Gemini model to use
        max_tokens: Maximum tokens in response
        thinking_budget: Thinking budget (0 to disable thinking)
        temperature: Optional temperature parameter (0.0-2.0)
        top_p: Optional top_p parameter (0.0-1.0)
        top_k: Optional top_k parameter
        **kwargs: Additional parameters for the Gemini API

    Returns:
        dict with 'reply' key containing the response text
    """
    api_messages = _prepare_messages(messages, final_message_template, final_head_inject, final_bottom_inject)

    # Convert to Gemini's Content format
    contents = []
    for msg in api_messages:
        # Map assistant to model for Gemini
        role = "model" if msg["role"] == "assistant" else msg["role"]
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Make API call
    client = genai.Client()

    # Build config parameters
    config_params = {
        "max_output_tokens": max_tokens,
        "thinking_config": genai.types.ThinkingConfig(thinking_budget=thinking_budget),
    }

    if temperature is not None:
        config_params["temperature"] = temperature
    if top_p is not None:
        config_params["top_p"] = top_p
    if top_k is not None:
        config_params["top_k"] = top_k

    # Add system instruction if provided
    if system:
        config_params["system_instruction"] = system

    config = genai.types.GenerateContentConfig(**config_params)

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config
    )

    return {
        "reply": response.text,
        "full_context": None,
        "citations": None,
        "followups": None
    }


def test_csv_functions():
    """Test CSV load/save functionality."""
    import tempfile
    import os

    # Test data
    test_data = {
        'What is AI alignment?': {
            'claude-sonnet-4|data=stampy-full': 'AI alignment is the field...',
            'gpt-4|data=stampy-miri': 'AI alignment refers to...'
        },
        'What are x-risks?': {
            'claude-sonnet-4|data=stampy-full': 'X-risks are existential risks...',
            'gemini-pro|data=miri_the_question': 'Existential risks...'
        }
    }

    # Test save and load
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        csv_path = f.name

    try:
        # Test prompts loading
        prompts = load_prompts()
        print(f'  Loaded prompts: {len(prompts)}')

        save_csv(test_data, csv_path)
        loaded_data = load_csv(csv_path, prompts)

        print('CSV test results:')
        print(f'  Original questions: {len(test_data)}')
        print(f'  Loaded questions: {len(loaded_data)}')
        print(f'  Data matches: {test_data == loaded_data}')

        # Test parse_config with prompt matching
        test_settings = 'claude-sonnet-4|stampy-full|system=SOURCE_PROMPT'
        parsed = parse_config(test_settings, prompts)
        print(f'  Parsed settings: {parsed}')

        # Test prompt name resolution
        print('  Testing prompt name resolution:')

        # Create test prompts for matching
        test_prompts = {
            'my-prompt-241201123-abc123': 'Test prompt 1',
            'my-prompt-241202145-def456': 'Test prompt 2',
            'my-prompt-241203156-ghi789': 'Test prompt 3',
            'other-prompt-241201123-xyz999': 'Other prompt'
        }

        # Test exact match
        result = _resolve_prompt_name('my-prompt-241201123-abc123', test_prompts)
        print(f'    Exact match: {result}')

        # Test pattern match (should return the latest version)
        result = _resolve_prompt_name('my-prompt', test_prompts)
        print(f'    Pattern match: {result}')

        # Test no match
        result = _resolve_prompt_name('non-existent', test_prompts)
        print(f'    No match: {result}')

        return True

    except Exception as e:
        print(f'Test failed: {e}')
        return False
    finally:
        if os.path.exists(csv_path):
            os.unlink(csv_path)


if __name__ == "__main__":
    import sys
    import time

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_csv_functions()
    else:
        if len(sys.argv) < 2:
            print("Usage: python stampy_client.py <csv_path>")
            sys.exit(1)

        csv_path = sys.argv[1]
        prompts = load_prompts()
        print(f'  Loaded prompts: {len(prompts)}')

        data = load_csv(csv_path, prompts)
        print(f"  Loaded data: {len(data)} questions")
        for q, r in data.items():
            print(f"    Question: {q!r}, Responses: {len(r)}")
        all_configs: set[frozendict[str,str]] = set()
        for responses in data.values():
            all_configs.update(responses.keys())
        print(f"  All model configs: {len(all_configs)}")

        for question, answers in data.items():
            question_parts = re.split(r"\s*-{4,}\s*", question)
            for config in all_configs:
                response = answers.get(config)
                if response and response != "invalid":
                    continue

                start_time = time.time()

                match dict(config): # dict() to simplify type
                    case {"data": data_name} if data_name in ["stampy-full", "stampy-miri"]:
                        result = stampy(
                            messages=question_parts,
                            #use_miri=data_name == "stampy-miri" # TODO: blocked on serverside work, including preparing vector db
                            system=prompts.get(config.get('system'), ''),
                            model=config.get("model", "claude-sonnet-4-20250514")
                        )
                    case {"model": model} if model.startswith("claude"):
                        result = anthropic_client(
                            messages=question_parts,
                            system=prompts.get(config.get('system'), ''),
                            model=model,
                            temperature=float(config.get("temperature", 0.8)),
                            top_p=float(config.get("top_p", 1.0))
                        )
                    case {"model": model} if model.startswith("gemini"):
                        result = gemini_client(
                            messages=question_parts,
                            system=prompts.get(config.get('system'), ''),
                            model=model,
                            temperature=float(config.get("temperature", 0.8)),
                            top_p=float(config.get("top_p", 1.0)),
                            top_k=int(config["top_k"]) if "top_k" in config else None,
                            thinking_budget=int(config.get("thinking_budget", 0))
                        )
                    case _:
                        answers[config] = "invalid"
                        continue


                elapsed = time.time() - start_time

                response = result[config.get("field", "reply")]
                response = f"{response}\n\n[Response time: {elapsed:.2f}s]"

                answers[config] = response

        save_csv(data, csv_path)
