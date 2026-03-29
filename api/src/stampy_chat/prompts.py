from pathlib import Path
from typing import Sequence
import datetime

from stampy_chat.citations import Block, Message
from stampy_chat.settings import Settings, num_tokens
from xml.sax.saxutils import escape

from stampy_chat import logging

logger = logging.getLogger(__name__)

logger.info("Loading prompts dir...")
try:
    PROMPTS_DIR = Path(__file__).absolute().parent.parent.parent.parent / "prompts"
    ALL_PROMPTS = {
        x.name.rsplit(".", 1)[0]: x.read_text() for x in PROMPTS_DIR.iterdir()
    }
except FileNotFoundError:
    logger.error(
        "Cannot start stampy with no prompts! please restore the prompts/ directory."
    )
    raise SystemExit(1)
logger.info("Done loading prompts")


def truncate_history(history: list[Message], max_tokens: int) -> list[Message]:
    """Truncate the history to the given number of tokens."""
    truncated = []
    all_tokens = 0
    for item in history[::-1]:
        if item.get("role") in ["deleted", "error"]:
            continue

        content = item.get("content", "")
        if isinstance(content, str):
            all_tokens += num_tokens(content)
        # block-structured content -- estimate from all text fields
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    for key in ("text", "thinking", "model_output"):
                        val = block.get(key, "")
                        if isinstance(val, str):
                            all_tokens += num_tokens(val)

        if all_tokens > max_tokens:
            return truncated

        truncated = [item] + truncated
    if truncated and truncated[0].get("role") == "assistant":
        truncated = truncated[1:]
    return truncated


def _strip_thinking(content):
    """Strip thinking blocks from assistant message content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return [b for b in content if not (isinstance(b, dict) and b.get("type") == "thinking")]
    return content


def _is_human_text(message: Message) -> bool:
    """Check if a message is human text (vs tool_result blocks)."""
    content = message.get("content", "")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)
    return True


def _expand_blocks(blocks: list, tool_counter: list[int]) -> list[Message]:
    """Expand flat client blocks into alternating Anthropic API messages.

    Client stores one assistant turn as a flat list of blocks:
      [text, tool_use, tool_result, text, tool_use, tool_result, text]

    Anthropic API requires alternating roles with tool_use/tool_result split:
      assistant: [text, tool_use]  →  user: [tool_result]  →  assistant: [text]

    tool_counter is a mutable [int] for generating synthetic tool_use IDs
    when the client didn't send them (old history).

    >>> blocks = [
    ...     {"type": "text", "text": "hi"},
    ...     {"type": "tool_use", "id": "t1", "name": "s", "input": {}},
    ...     {"type": "tool_result", "tool_use_id": "t1", "model_output": "xml"},
    ...     {"type": "text", "text": "done"},
    ... ]
    >>> msgs = _expand_blocks(blocks, [0])
    >>> [m["role"] for m in msgs]
    ['assistant', 'user', 'assistant']
    >>> msgs[0]["content"][1]["type"]
    'tool_use'
    >>> msgs[1]["content"][0]["tool_use_id"]
    't1'
    >>> msgs[2]["content"][0]["text"]
    'done'

    Thinking blocks are stripped:
    >>> _expand_blocks([{"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "ok"}], [0])
    [{'role': 'assistant', 'content': [{'type': 'text', 'text': 'ok'}]}]
    """
    messages = []
    assistant_content = []

    for block in blocks:
        btype = block.get("type") if isinstance(block, dict) else None
        if btype == "thinking":
            continue
        elif btype == "text":
            assistant_content.append({"type": "text", "text": block["text"]})
        elif btype == "tool_use":
            tool_id = block.get("id") or f"toolu_hist_{tool_counter[0]}"
            tool_counter[0] += 1
            assistant_content.append({
                "type": "tool_use", "id": tool_id,
                "name": block["name"], "input": block.get("input", {}),
            })
        elif btype == "tool_result":
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})
                assistant_content = []
            tool_use_id = block.get("tool_use_id") or f"toolu_hist_{tool_counter[0] - 1}"
            messages.append({"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": block.get("model_output", ""),
            }]})

    if assistant_content:
        messages.append({"role": "assistant", "content": assistant_content})

    return messages


def format_history(
    query: str,
    history: list[Message],
    settings: Settings,
    vals: dict,
) -> list[Message]:
    """Convert client history to Anthropic API messages.

    Input (from client -- assistant turns have flat block lists):
      [{"role": "user", "content": "question"},
       {"role": "assistant", "content": [       ← list = blocks
          {"type": "text", ...},
          {"type": "tool_use", "id": "...", ...},
          {"type": "tool_result", "model_output": "...", ...},
          {"type": "text", ...}]},
       {"role": "user", "content": "followup"}]

    Output (for Anthropic API -- tool_use/tool_result split into separate messages):
      [{"role": "user", "content": "<wrapped>question</wrapped>"},
       {"role": "assistant", "content": [text, tool_use]},
       {"role": "user", "content": [{"type": "tool_result", ...}]},
       {"role": "assistant", "content": [text]},
       {"role": "user", "content": "<wrapped>followup</wrapped>"}]

    Also: strips thinking blocks, wraps human text in <from-public-user> tags,
    appends current query with prompt injection as final user message.

    - Expands block-structured assistant messages into API tool_use/tool_result pairs
    - Strips thinking blocks from assistant messages
    - Wraps human text in <from-public-user> tags
    - Appends the current query with prompt injection as the final user message
    """
    history = truncate_history(history, settings.history_tokens)

    formatted = []
    tool_counter = [0]  # mutable counter for synthetic tool IDs
    for i, msg in enumerate(history):
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "assistant":
            if isinstance(content, list):
                # Block-structured content from client -- expand into API messages
                formatted.extend(_expand_blocks(content, tool_counter))
            else:
                formatted.append({"role": "assistant", "content": content})
        elif role == "user":
            if _is_human_text(msg) and isinstance(content, str):
                wrapped = settings.message_format.format(
                    message_id=i, message=escape(content), **ALL_PROMPTS
                )
                formatted.append({"role": "user", "content": wrapped})
            else:
                # tool_result blocks -- pass through unchanged
                formatted.append(msg)
        else:
            formatted.append(msg)

    # Build the final user message with prompt injection
    last_parts = []
    vals = {**vals, "mode": format_prompts(settings.mode_prompt, vals), "message_id": len(formatted)}

    if settings.pre_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=format_prompts(settings.pre_message_prompt, vals).strip()
        )
        last_parts.append(wrapped)

    last_parts.append(
        settings.message_format.format(message_id=len(formatted), message=escape(query), **ALL_PROMPTS)
    )

    if settings.post_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=format_prompts(settings.post_message_prompt, vals).strip()
        )
        last_parts.append(wrapped)

    formatted.append({"role": "user", "content": "\n\n".join(last_parts)})
    return formatted


def format_prompts(template: str, vals: dict) -> str:
    return template.format(**vals, **ALL_PROMPTS).format(**vals)


def inline_all_templates(prompts: dict) -> dict:
    "implements the inline all templates button in the ui"
    vals = dict(
        modelname='{modelname}',
        date='{date}',
        mode='{mode}',
        message='{message}',
        message_id='{message_id}'
    )

    inlined = {}
    for key, value in prompts.items():
        if isinstance(value, str):
            inlined[key] = format_prompts(value, vals)
        elif isinstance(value, dict):
            inlined[key] = inline_all_templates(value)
        else:
            inlined[key] = value
    return inlined
