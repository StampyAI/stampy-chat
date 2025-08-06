from typing import TypedDict, Literal
import re
import urllib.parse

from stampy_chat.settings import Settings
from pinecone import Pinecone
import voyageai
from stampy_chat.env import (
    VOYAGEAI_API_KEY,
    VOYAGEAI_EMBEDDINGS_MODEL,
    PINECONE_NAMESPACE,
    PINECONE_API_KEY,
    PINECONE_ENVIRONMENT,
    PINECONE_INDEX_NAME,
)
from datetime import datetime, date


class Message(TypedDict):
    role: Literal["user", "assistant", "system", "deleted", "error"]
    content: str


class Block(TypedDict):
    id: str
    reference: str
    date_published: str
    authors: list[str]
    title: str
    url: str
    tags: list[str]
    text: str


def embed_query(query: str, settings: Settings) -> list[float] | list[int]:
    """Embed the query."""
    voyageai_client = voyageai.Client(api_key=VOYAGEAI_API_KEY)
    return voyageai_client.embed([query], model=VOYAGEAI_EMBEDDINGS_MODEL).embeddings[0]


def clean_block(reference: int, block) -> Block:
    block_id = block.get("hash_id") or block.get("id")
    date_published = block.get("date_published") or block.get("date")

    if isinstance(date_published, datetime):
        date_published = date_published.date().isoformat()
    elif isinstance(date_published, date):
        date_published = date_published.isoformat()
    elif isinstance(date_published, (int, float)):
        date_published = datetime.fromtimestamp(date_published).date().isoformat()

    authors = block.get("authors")
    if not authors and block.get("author"):
        authors = [block.get("author")]

    text = fix_text(block["text"])

    url_with_frag = set_text_fragment(block["url"], text)

    return Block(
        reference=str(reference),
        id=block_id,
        date_published=date_published,
        authors=authors,
        title=block["title"],
        url=url_with_frag,
        tags=block.get("tags"),
        text=text,
    )


def set_text_fragment(url, text, max_length=24):
    parsed = urllib.parse.urlparse(url)
    quoted_text = urllib.parse.quote(text, safe='')
    words = text.split()

    if len(words) <= max_length:
        fragment = f":~:text={quoted_text}"
    else:
        # Split into start/end for long text
        text_start = ' '.join(words[:max_length//2])
        text_end = ' '.join(words[-max_length//2:])
        fragment = f":~:text={urllib.parse.quote(text_start, safe='')},{urllib.parse.quote(text_end, safe='')}"

    return urllib.parse.urlunparse(parsed._replace(fragment=fragment))


def retrieve_docs(query: str, settings: Settings) -> list[Block]:
    """Retrieve the documents for the query."""
    pc = Pinecone(
        api_key=PINECONE_API_KEY,
        environment=PINECONE_ENVIRONMENT,
    )

    index = pc.Index(PINECONE_INDEX_NAME)

    vector = embed_query(query, settings)
    results = index.query_namespaces(
        vector=list(vector),
        metric="cosine",
        include_metadata=True,
        namespaces=[PINECONE_NAMESPACE],
        filter=settings.miri_filters,
    )
    return [clean_block(i, r.metadata) for i, r in enumerate(results.matches, 1)]


def get_top_k_blocks(query: str, k: int) -> list[Block]:
    return retrieve_docs(query, Settings())[:k]

def fix_text(received_text: str|None) -> str|None:
    """
    discard the title format received from the vector db.
    """
    if received_text is None: return None
    return re.sub(r'^ *###(?:.(?!=###\n))*###\s+"""|"""\s*$', '', received_text).strip()
