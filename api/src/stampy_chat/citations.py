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

    if VOYAGEAI_EMBEDDINGS_MODEL == "voyage-context-3":
        # voyage-context-3 requires contextualized API with single-chunk documents
        result = voyageai_client.contextualized_embed(
            inputs=[[query]],
            model=VOYAGEAI_EMBEDDINGS_MODEL,
            input_type="query",
        )
        return result.results[0].embeddings[0]
    else:
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


def retrieve_docs(query: str, settings: Settings, filter: dict | None = None, snippets_per_doc: int = 1) -> list[Block]:
    """Retrieve the documents for the query, keeping up to snippets_per_doc chunks per document."""
    pc = Pinecone(
        api_key=PINECONE_API_KEY,
        environment=PINECONE_ENVIRONMENT,
    )

    index = pc.Index(PINECONE_INDEX_NAME)

    vector = embed_query(query, settings)

    # Use custom filter if provided, otherwise use settings filters
    query_filter = filter if filter is not None else settings.miri_filters

    results = index.query_namespaces(
        vector=list(vector),
        metric="cosine",
        top_k=50,
        include_metadata=True,
        namespaces=[PINECONE_NAMESPACE],
        filter=query_filter,
    )

    # Track chunks per document, deduplicating by title and URL separately
    # seen_docs: key -> list of (score, match) tuples, sorted by score desc
    seen_docs = {}  # key: normalized_key, value: list[(score, match)]
    doc_refs = {}   # key: normalized_key, value: reference_num
    seen_titles = {}  # title -> normalized_key
    seen_urls = {}   # base_url -> normalized_key
    reference_counter = 1

    for match in results.matches:
        metadata = match.metadata
        title = metadata.get("title", "").strip()
        url = metadata.get("url", "")

        # Remove fragment from URL for deduplication
        parsed_url = urllib.parse.urlparse(url)
        base_url = urllib.parse.urlunparse(parsed_url._replace(fragment=""))

        score = match.score

        # Check if we've seen this document before (by title or URL)
        doc_key = None
        if title and title in seen_titles:
            doc_key = seen_titles[title]
        elif base_url and base_url in seen_urls:
            doc_key = seen_urls[base_url]

        if doc_key is None:
            # New document
            doc_key = (title, base_url)
            if title: seen_titles[title] = doc_key
            if base_url: seen_urls[base_url] = doc_key
            seen_docs[doc_key] = [(score, match)]
            doc_refs[doc_key] = reference_counter
            reference_counter += 1
        else:
            # Existing doc - add chunk if under limit
            chunks = seen_docs[doc_key]
            if len(chunks) < snippets_per_doc:
                chunks.append((score, match))
                chunks.sort(key=lambda x: x[0], reverse=True)

    # Flatten and sort by score
    all_chunks = []
    for doc_key, chunks in seen_docs.items():
        ref_num = doc_refs[doc_key]
        for score, match in chunks:
            all_chunks.append((score, match, ref_num))
    all_chunks.sort(key=lambda x: x[0], reverse=True)

    return [clean_block(ref_num, match.metadata) for _, match, ref_num in all_chunks]


def get_top_k_blocks(query: str, k: int, filter: dict | None = None, snippets_per_doc: int = 1) -> list[Block]:
    return retrieve_docs(query, Settings(), filter, snippets_per_doc)[:k]

def fix_text(received_text: str|None) -> str|None:
    """
    discard the title format received from the vector db.
    """
    if received_text is None: return None
    return re.sub(r'^ *###(?:.(?!=###\n))*###\s+"""|"""\s*$', '', received_text).strip()
