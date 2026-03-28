#!/usr/bin/env python3
"""
Stampy Chat MCP Server

Provides search and retrieval tools for AI alignment research via MCP.
Sources: LessWrong, Alignment Forum, curated arxiv safety papers, EA Forum, blogs, more.
~25k articles. Updated within days of publication.
"""

import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from fastmcp import FastMCP
from sqlalchemy import create_engine, table, column, select
from stampy_chat.citations import get_top_k_blocks, Block
from stampy_chat.prompts import format_blocks
from stampy_chat import logging
from stampy_chat.env import DB_CONNECTION_URI

logger = logging.getLogger(__name__)

mcp = FastMCP("Stampy Backend RAG")

# alignment_research_dataset lives in the same MySQL instance, different db
ARD_URI = DB_CONNECTION_URI.rsplit("/", 1)[0] + "/alignment_research_dataset"
ard_engine = create_engine(ARD_URI, echo=False)

articles = table("articles",
    column("hash_id"), column("title"), column("url"),
    column("source"), column("authors"), column("text"),
    column("date_published"),
)

# Import ARD text cleaner directly (bypasses align_data.__init__ and its heavy deps)
_clean_spec = importlib.util.spec_from_file_location(
    "ard_clean", Path(__file__).resolve().parent.parent / "ard" / "align_data" / "embeddings" / "clean.py"
)
_clean_mod = importlib.util.module_from_spec(_clean_spec)
_clean_spec.loader.exec_module(_clean_mod)
clean_text = _clean_mod.clean_text

# 99th percentile cleaned article length is ~130k chars
MAX_DOC_CHARS = 130_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search(query, k=20, filter=None, format="formatted", snippets_per_doc=1):
    """Core search logic shared by search and recent tools."""
    if filter:
        filter = _convert_date_fields(filter)
        filter = _remap_quality_fields(filter)

    logger.info(f"MCP search: query='{query}' k={k} format={format} snippets_per_doc={snippets_per_doc} filter={filter}")

    k = max(1, min(50, k))
    snippets_per_doc = max(1, min(10, snippets_per_doc))

    blocks = get_top_k_blocks(query, k, filter, snippets_per_doc)
    logger.info(f"MCP search returned {len(blocks)} results")

    if format == "json": return [dict(b) for b in blocks]
    return format_blocks(blocks)


def _get_article(*, id=None, url=None, title=None):
    """Look up a single article using SQLAlchemy Core (no string building)."""
    q = select(articles).limit(1)
    if id: q = q.where(articles.c.hash_id == id)
    if title: q = q.where(articles.c.title == title)
    if url:
        escaped = url.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        q = q.where(articles.c.url.like(f"%{escaped}%", escape="\\"))

    with ard_engine.connect() as conn:
        return conn.execute(q).mappings().first()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool
def lw_af_arxivsafety_search(
    query: str, k: int = 20, filter: dict | None = None, format: str = "formatted",
    snippets_per_doc: int = 1,
) -> str | list[dict]:
    """Semantic search over 25k AI safety posts from LessWrong, Alignment Forum, arxiv (curated safety-relevant subset), EA Forum, blogs, and more. Updated within days of publication. Use for: finding prior alignment work, checking if an idea has been explored, retrieving specific researchers' writings, understanding current thinking on safety topics, finding counterarguments or failure modes for alignment proposals.

Key researchers: John Wentworth (johnswentworth; natural abstractions, natural latents, research methodology), Richard Ngo ("Richard Ngo"; coalitional/scale-free agency, AI governance), Abram Demski (abramdemski; logical induction, embedded agency, decision theory), Vanessa Kosoy (infra-Bayesianism, learning-theoretic alignment). Also covers: mechanistic interpretability, singular learning theory, computational mechanics, governance/policy, RLHF safety, scalable oversight, and more.

Filters: author, date range, source (lesswrong/alignmentforum/arxiv), quality score. Use filter={"authors": {"$in": ["Name"]}} for author search, filter={"date_published": {"$gte": "2024-01-01"}} for date ranges.

    Args:
        query: Natural language search query. Semantic search, so describe what you're looking for.
        k: Number of results (unset=20, max 50)
        format: unset="formatted" (XML with citations) or "json" (raw dicts with hash_id)
        snippets_per_doc: default 1, max 10
        filter: Pinecone metadata filter. Fields: title, authors, date_published (int|ISO str), url, source, needs_tech, quality_score (0-10). Operators: $eq $ne $gt $gte $lt $lte $in $nin $and $or.
    """
    return _search(query, k, filter, format, snippets_per_doc)


@mcp.tool
def lw_af_arxivsafety_recent(
    query: str, days: int = 90, k: int = 20, filter: dict | None = None,
    format: str = "formatted", snippets_per_doc: int = 1,
) -> str | list[dict]:
    """Search recent AI safety posts (default: last 90 days). Same corpus as lw_af_arxivsafety_search but pre-filtered to recent content. Use when you need current work, recent developments, or want to check what's been published lately on a topic.

    Args:
        query: Natural language search query.
        days: How far back to search, unset=90.
        k: Number of results (unset=20, max 50)
        format: unset="formatted" (XML) or "json" (raw dicts)
        snippets_per_doc: default 1, max 10
        filter: Pinecone metadata filter. Fields: title, authors, date_published (int|ISO str), url, source, needs_tech, quality_score (0-10). Operators: $eq $ne $gt $gte $lt $lte $in $nin $and $or (date constraint is added automatically).
    """
    cutoff = datetime.now() - timedelta(days=days)
    date_filter = {"date_published": {"$gte": int(cutoff.timestamp())}}

    if filter: filter = {"$and": [date_filter, filter]}
    else: filter = date_filter

    return _search(query, k, filter, format, snippets_per_doc)


@mcp.tool
def lw_af_arxivsafety_get_doc(
    id: str | None = None, url: str | None = None, title: str | None = None,
    max_chars: int = MAX_DOC_CHARS, offset: int = 0,
) -> str:
    """Retrieve full text of a single article from the alignment research corpus. Use after finding an interesting result via search to read the complete document. Accepts hash_id, URL, or exact title. Non-semantic content (base64, SVGs, Plotly data) is stripped; long articles are truncated (default 130k chars). Use offset to paginate through longer articles.

    Args:
        id: Article hash_id (shown as hash_id in formatted results, or 'id' in json results). Preferred lookup method.
        url: Article URL. Partial match.
        title: Exact article title.
        max_chars: Max characters to return (default 130000). The cleaned text length is reported in the response so you can decide whether to request more.
        offset: Character offset into cleaned text (default 0). Use to retrieve subsequent pages of a long article.
    """
    if not any([id, url, title]):
        return "Error: provide at least one of: id, url, title"

    row = _get_article(id=id, url=url, title=title)
    if not row:
        return f"Article not found (searched: id={id} url={url} title={title})"

    authors = row["authors"] or ""
    date = row["date_published"].strftime("%Y-%m-%d") if row["date_published"] else "unknown"

    body = clean_text(row["text"] or "")
    total = len(body)
    chunk = body[offset:offset + max_chars]

    parts = [
        f'<article hash_id="{row["hash_id"]}" source="{row["source"]}" cleaned_length="{total}">',
        f'<title>{row["title"]}</title>',
        f'<authors>{authors}</authors>',
        f'<date>{date}</date>',
        f'<url>{row["url"]}</url>',
        f'<text offset="{offset}" length="{len(chunk)}">',
        chunk,
        f'</text>',
    ]
    if offset + max_chars < total:
        parts.append(f'<remaining chars="{total - offset - len(chunk)}" next_offset="{offset + len(chunk)}" />')
    parts.append('</article>')
    return "\n".join(parts)


@mcp.tool
def lw_af_posts_sorted() -> str:
    """Browse and list AI safety articles: by author, by recency, by source, by quality. Coming soon -- use lw_af_arxivsafety_search with filters for now."""
    return "Not yet implemented. Use lw_af_arxivsafety_search with filter parameter instead. Example: filter={\"authors\": {\"$in\": [\"John Wentworth\"]}} or filter={\"source\": \"lesswrong\", \"date_published\": {\"$gte\": \"2024-01-01\"}}"


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def _parse_date_to_timestamp(value: str | int) -> int:
    """Convert ISO date/datetime string to Unix timestamp, or pass through int."""
    if isinstance(value, int): return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                return int(dt.timestamp())
            except ValueError:
                continue
        try: return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError: pass
        raise ValueError(f"Cannot parse date: {value!r}")
    return value


def _convert_date_fields(filter: dict) -> dict:
    """Recursively convert ISO date strings in date_published to Unix timestamps."""
    if not filter: return filter

    result = {}
    for key, value in filter.items():
        if key == "date_published":
            if isinstance(value, dict):
                result[key] = {op: _parse_date_to_timestamp(v) for op, v in value.items()}
            else:
                result[key] = _parse_date_to_timestamp(value)
        elif key in ("$and", "$or"):
            result[key] = [_convert_date_fields(f) for f in value]
        else:
            result[key] = value
    return result


def _remap_quality_fields(filter: dict) -> dict:
    """Remap MCP client-facing quality_* fields to internal miri_* fields."""
    if not filter: return filter

    result = {}
    for key, value in filter.items():
        if key == "quality_score":
            result["miri_confidence"] = value
        elif key == "quality_distance":
            raise ValueError("quality_distance filter is deprecated and no longer supported")
        elif key in ("$and", "$or"):
            result[key] = [_remap_quality_fields(f) for f in value]
        else:
            result[key] = value
    return result


if __name__ == "__main__":
    logger.info("Starting Stampy Chat MCP server on port 3002")
    mcp.run(transport="http", host="127.0.0.1", port=3002)
