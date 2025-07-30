from pathlib import Path
from typing import Sequence

from stampy_chat.citations import Block, Message
from stampy_chat.settings import Settings, num_tokens
from xml.sax.saxutils import escape

from stampy_chat import logging

logger = logging.getLogger(__name__)

logger.info("Loading prompts dir...")
PROMPTS_DIR = Path(__file__).absolute().parent.parent.parent.parent / "prompts"
if PROMPTS_DIR.exists():
    ALL_PROMPTS = {
        x.name.rsplit(".", 1)[0]: x.read_text() for x in PROMPTS_DIR.iterdir()
    }
else:
    ALL_PROMPTS = {}
logger.info("Done loading prompts")


def truncate_history(history: list[Message], max_tokens: int) -> list[Message]:
    """Truncate the history to the given number of tokens."""
    truncated = []
    all_tokens = 0
    for item in history[::-1]:
        if item.get("role") in ["deleted", "error"]:
            continue

        if not (content := item.get("content")):
            continue

        all_tokens += num_tokens(content)
        if all_tokens > max_tokens:
            return truncated

        truncated = [item] + truncated
    if len(truncated) and truncated[0].get("role") == "assistant":
        truncated = truncated[1:]
    return truncated


def format_block(block: Block) -> str:
    return f'<source-fragment id={block.get("reference")} title="{block.get("title")}" authors="{", ".join(block["authors"])}" timestamp="{block["date_published"]}">\n...\n{block["text"]}\n...\n</source-fragment>'


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
    # todo: something besides runtimeerror? it's a clientside mistake, need to return an api error
    if not len(history):
        raise RuntimeError("history can't be empty")
    if history[0]["role"] != "user":
        raise RuntimeError("history[0] should be user message")
    if history[-1]["role"] != "user":
        raise RuntimeError("history[-1] should be user message")
    last_role = None
    for msg in history:
        if msg["role"] not in ["user", "assistant"]:
            raise RuntimeError("user and assistant only please")
        if msg["role"] == last_role:
            raise RuntimeError("alternating role, please")
        last_role = msg["role"]


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
    modelname = settings.completions_provider
    mode = settings.mode_prompt.format(**ALL_PROMPTS)
    if settings.pre_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=settings.pre_message_prompt.format(
                mode=mode, modelname=modelname, **ALL_PROMPTS
            ).strip()
        )
        last_parts.append(wrapped)

    last_parts.append(
        settings.message_format.format(message=escape(query), **ALL_PROMPTS)
    )

    if settings.post_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=settings.post_message_prompt.format(
                mode=mode, modelname=modelname, **ALL_PROMPTS
            ).strip()
        )
        last_parts.append(wrapped)

    history.append(Message(role="user", content="\n\n".join(last_parts)))
    validate_history(history)

    return [
        Message(
            role="system",
            content=settings.system_prompt.format(modelname=modelname, **ALL_PROMPTS),
        ),
        Message(
            role="system",
            content=settings.history_prompt.format(modelname=modelname, **ALL_PROMPTS),
        ),
    ] + history


def inject_guidance_hyde(
    query: str,
    history: list[Message],
    settings: Settings,
) -> Sequence[Message]:
    history = truncate_history(history, settings.history_tokens)
    history = format_history(history, settings)

    mode = ""

    last_parts = []
    modelname = settings.completions_provider
    if settings.hyde_pre_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=settings.hyde_pre_message_prompt.format(
                mode=mode, modelname=modelname, **ALL_PROMPTS
            ).strip()
        )
        last_parts.append(wrapped)

    last_parts.append(
        settings.message_format.format(message=escape(query), **ALL_PROMPTS)
    )

    if settings.hyde_post_message_prompt:
        wrapped = settings.instruction_wrapper.format(
            content=settings.hyde_post_message_prompt.format(
                mode=mode, modelname=modelname, **ALL_PROMPTS
            ).strip()
        )
        last_parts.append(wrapped)

    history.append(Message(role="user", content="\n\n".join(last_parts)))
    validate_history(history)

    return [
        Message(
            role="system",
            content=settings.hyde_system_prompt.format(
                modelname=modelname, **ALL_PROMPTS
            ),
        ),
        Message(
            role="system",
            content=settings.history_prompt.format(modelname=modelname, **ALL_PROMPTS),
        ),
    ] + history
