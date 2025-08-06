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

        all_tokens += num_tokens(item.get("content", ""))
        if all_tokens > max_tokens:
            return truncated

        truncated = [item] + truncated
    if truncated and truncated[0].get("role") == "assistant":
        truncated = truncated[1:]
    return truncated


def format_block(block: Block) -> str:
    return f'<result-fragment id={block.get("reference")} title="{block.get("title")}" authors="{", ".join(block["authors"])}" timestamp="{block["date_published"]}">\n...\n{block["text"]}\n...\n</result-fragment>'


def format_blocks(blocks: list[Block]) -> str:
    return "\n\n".join([format_block(block) for block in blocks])


def format_history(history: list[Message], settings: Settings) -> list[Message]:
    return [
        (
            {
                "role": "user",
                "content": settings.message_format.format(
                    message=escape(message["content"]), **ALL_PROMPTS
                ),
            }
            if message["role"] == "user"
            else message
        )
        for message in history
    ]


def validate_history(history: list[Message]):
    if not history:
        raise ValueError("history can't be empty")

    if history[0]["role"] != "user":
        raise ValueError(
            "history[0] should be user message, but instead I see {''.join(x.get('role', '?')[0] for x in history)}"
        )
    if history[-1]["role"] != "user":
        raise ValueError(
            f"history[-1] should be user message, but instead I see {''.join(x.get('role', '?')[0] for x in history)}"
        )

    roles = [x.get("role") for x in history]
    if extra_roles := (set(roles) - {"user", "assistant"}):
        raise ValueError(f"user and assistant only please, got {extra_roles}")

    if any(a == b for a, b in zip(history, history[1:])):
        raise ValueError(
            f"alternating role, please, got same role multiple times in a row: {roles}"
        )


def inject_guidance(
    query: str,
    history: list[Message],
    docs: list[Block],
    settings: Settings,
) -> Sequence[Message]:
    history = truncate_history(history, settings.history_tokens)
    history = format_history(history, settings)

    last_parts = []
    last_parts.append(format_blocks(docs))
    vals = dict(
        modelname=settings.completions_provider,
        date=datetime.datetime.now().strftime("%B %d, %Y"),
    )
    vals['mode'] = format_prompts(settings.mode_prompt, vals)
    if settings.pre_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=format_prompts(
                settings.pre_message_prompt, vals
            ).strip()
        )
        last_parts.append(wrapped)

    last_parts.append(
        settings.message_format.format(message=escape(query), **ALL_PROMPTS)
    )

    if settings.post_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=format_prompts(
                settings.post_message_prompt, vals
            ).strip()
        )
        last_parts.append(wrapped)

    history.append(Message(role="user", content="\n\n".join(last_parts)))
    validate_history(history)

    return [
        Message(
            role="system",
            content=format_prompts(settings.system_prompt, vals),
        ),
        Message(
            role="system",
            content=format_prompts(settings.history_prompt, vals),
        ),
    ] + history


def inject_guidance_hyde(
    query: str,
    history: list[Message],
    settings: Settings,
) -> Sequence[Message]:
    history = truncate_history(history, settings.history_tokens)
    history = format_history(history, settings)

    last_parts = []
    vals = dict(
        modelname=settings.completions_provider,
        date=datetime.datetime.now().strftime("%B %d, %Y"),
        mode=""
    )
    if settings.hyde_pre_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=format_prompts(
                settings.hyde_pre_message_prompt, vals
            ).strip()
        )
        last_parts.append(wrapped)

    last_parts.append(
        settings.message_format.format(message=escape(query), **ALL_PROMPTS)
    )

    if settings.hyde_post_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=format_prompts(
                settings.hyde_post_message_prompt, vals
            ).strip()
        )
        last_parts.append(wrapped)

    history.append(Message(role="user", content="\n\n".join(last_parts)))
    validate_history(history)

    return [
        Message(
            role="system",
            content=format_prompts(settings.hyde_system_prompt, vals),
        ),
        Message(
            role="system",
            content=format_prompts(settings.history_prompt, vals),
        ),
    ] + history


def format_prompts(template: str, vals: dict) -> str:
    return template.format(**vals, **ALL_PROMPTS).format(**vals)


def inline_all_templates(prompts: dict) -> dict:
    "implements the inline all templates button in the ui"
    vals = dict( # don't format these
        modelname='{modelname}',
        date='{date}',
        mode='{mode}',
        message='{message}'
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
