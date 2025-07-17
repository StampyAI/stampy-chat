from stampy_chat.citations import Block, Message
from stampy_chat.settings import Settings, num_tokens


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
    return truncated


def format_block(block: Block) -> str:
    return f"\n\n[{block.get('reference')}] {block['title']} {', '.join(block['authors'])} - {block['date_published']} {block['text']}\n\n"


def format_blocks(blocks: list[Block]) -> str:
    return "\n\n".join([format_block(block) for block in blocks])


def format_history(history: list[Message], settings: Settings) -> str:
    history = truncate_history(history, settings.history_tokens)
    return "\n\n".join([format_message(message) for message in history])


def format_message(message: Message) -> str:
    return f"{message['role']}: {message['content']}"


def construct_prompt(
    query: str, history: list[Message], docs: list[Block], settings: Settings
) -> str:
    return f"""
    {settings.context_prompt}
    {format_blocks(docs)}
    {settings.history_prompt}
    {format_history(history, settings)}
    {settings.question_prompt}
    {query}
    """
