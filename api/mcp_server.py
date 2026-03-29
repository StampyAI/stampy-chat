#!/usr/bin/env python3
"""
Stampy Chat MCP Server

Provides search and retrieval tools for AI alignment research via MCP.
Sources: LessWrong, Alignment Forum, curated arxiv safety papers, EA Forum, blogs, more.
~25k articles. Updated within days of publication.
"""

import importlib.util
import json as _json
import re
from datetime import datetime, timedelta
from pathlib import Path
from fastmcp import FastMCP
from sqlalchemy import create_engine, table, column, select, func, case, literal_column, text as sa_text
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
    column("date_published"), column("miri_confidence"),
    column("pinecone_status"), column("metadata"),
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


SNIPPET_CHARS = 50
SNIPPET_RAW = 200  # pull extra from DB, trim after cleanup
BROWSE_DEFAULTS = [
    "hash_id", "title", "authors", "date", "source", "url",
    "lw_karma", "karma_per_vote", "stampy_score", "tags",
    "snippet_start",
]


def _nulls_last(col):
    """MySQL-compatible nulls-last: returns (null_flag, col DESC) order clauses."""
    return [case((col.is_(None), 1), else_=0), col.desc()]


def _snippet(raw, max_len=SNIPPET_CHARS):
    """Collapse whitespace and truncate to max_len with ellipsis."""
    if not raw: return ""
    s = re.sub(r'\s+', ' ', raw).strip()
    if len(s) > max_len: s = s[:max_len - 1] + "…"
    return s


def _snippet_cols():
    """SQL columns for extracting start/middle/end text snippets."""
    return [
        func.left(articles.c.text, SNIPPET_RAW).label("text_start"),
        func.substring(
            articles.c.text,
            func.greatest(1, func.length(articles.c.text) // 2 - SNIPPET_RAW // 2),
            SNIPPET_RAW,
        ).label("text_mid"),
        func.right(articles.c.text, SNIPPET_RAW).label("text_end"),
    ]


_KARMA = literal_column("CAST(articles.metadata->>'$.karma' AS SIGNED)").label("lw_karma")
_KPV = literal_column(
    "CAST(articles.metadata->>'$.karma' AS SIGNED)"
    " / NULLIF(CAST(articles.metadata->>'$.votes' AS SIGNED), 0)"
).label("karma_per_vote")
_TAGS = literal_column("articles.metadata->>'$.tags'").label("tags_json")


# SQL expressions that normalize each blend field to [0, 1]. Hardcoded corpus bounds.
_NORMED = {
    "karma":          "COALESCE(CAST(articles.metadata->>'$.karma' AS SIGNED), 0) / 846.0",
    "karma_per_vote": "COALESCE(CAST(articles.metadata->>'$.karma' AS SIGNED)"
                      " / NULLIF(CAST(articles.metadata->>'$.votes' AS SIGNED), 0), 0) / 14.0",
    "stampy_score":   "(COALESCE(articles.miri_confidence, 0) - 1.0) / 8.0",
    "newness":        "TIMESTAMPDIFF(SECOND, '1951-05-15',"
                      " COALESCE(articles.date_published, '1951-05-15'))"
                      " / TIMESTAMPDIFF(SECOND, '1951-05-15', NOW())",
    "oldness":        "1 - TIMESTAMPDIFF(SECOND, '1951-05-15',"
                      " COALESCE(articles.date_published, '1951-05-15'))"
                      " / TIMESTAMPDIFF(SECOND, '1951-05-15', NOW())",
}


def _parse_lerp(expr):
    """Parse 'lerp_normed(field_a, field_b, t)' -> (a, b, t) or None."""
    m = re.match(r'lerp_normed\(\s*(\w+)\s*,\s*(\w+)\s*,\s*([\d.]+)\s*\)$', expr.strip())
    if not m: return None
    a, b, t = m.group(1), m.group(2), float(m.group(3))
    for f in (a, b):
        if f not in _NORMED:
            raise ValueError(f"Unknown blend field '{f}'. Available: {', '.join(sorted(_NORMED))}")
    if not 0 <= t <= 1:
        raise ValueError("lerp_normed weight must be 0.0-1.0")
    return a, b, t


def _lerp_order(a, b, t):
    """SQL ORDER BY: (1-t)*norm(a) + t*norm(b) DESC. t=0 gives pure a, t=1 gives pure b."""

    return sa_text(
        f"(1 - :t) * ({_NORMED[a]}) + :t * ({_NORMED[b]}) DESC"
    ).bindparams(t=t)


def _browse_stmt(sort_by, source, author, tag, after, before, need_snippets):
    """Build the full SELECT..WHERE..ORDER BY for browse queries."""
    cols = [
        articles.c.hash_id, articles.c.title, articles.c.url,
        articles.c.source, articles.c.authors, articles.c.date_published,
        articles.c.miri_confidence, _KARMA, _KPV, _TAGS,
    ]
    if need_snippets: cols.extend(_snippet_cols())

    stmt = select(*cols).where(articles.c.pinecone_status == "added")
    if source: stmt = stmt.where(articles.c.source == source)
    if author: stmt = stmt.where(articles.c.authors.like(f"%{author}%"))
    if tag:
    
        stmt = stmt.where(sa_text("JSON_CONTAINS(articles.metadata->'$.tags', JSON_QUOTE(:tag))").bindparams(tag=tag))
    if after: stmt = stmt.where(articles.c.date_published >= after)
    if before: stmt = stmt.where(articles.c.date_published <= before)

    # Determine ordering
    if sort_by == "date":
        stmt = stmt.order_by(*_nulls_last(articles.c.date_published))
    elif sort_by == "karma":
        stmt = stmt.order_by(*_nulls_last(_KARMA))
    elif sort_by == "karma_per_vote":
        stmt = stmt.order_by(*_nulls_last(_KPV))
    elif sort_by == "stampy_score":
        stmt = stmt.order_by(*_nulls_last(articles.c.miri_confidence))
    elif sort_by.startswith("lerp_normed("):
        parsed = _parse_lerp(sort_by)
        if not parsed:
            raise ValueError("Invalid lerp_normed syntax. Example: lerp_normed(newness, karma, 0.7)")
        stmt = stmt.order_by(_lerp_order(*parsed))
    else:
        # Numeric shorthand: 0.0-1.0 blends newness and karma
        try: w = float(sort_by)
        except ValueError:
            raise ValueError(
                "sort_by must be 'date', 'karma', 'karma_per_vote', 'stampy_score',"
                " a number 0.0-1.0 (shorthand for lerp_normed(newness, karma, t)),"
                " or lerp_normed(field_a, field_b, t)")
        if not 0 <= w <= 1:
            raise ValueError("blend weight must be between 0.0 and 1.0")
        stmt = stmt.order_by(_lerp_order("newness", "karma", w))

    return stmt


def _format_row(r, include):
    """Extract requested fields from a DB row dict."""
    out = {}
    for f in include:
        if f == "title": out["title"] = r.get("title", "")
        elif f == "authors": out["authors"] = r.get("authors", "")
        elif f == "date": out["date"] = r["date_published"].strftime("%Y-%m-%d") if r.get("date_published") else ""
        elif f == "source": out["source"] = r.get("source", "")
        elif f == "url": out["url"] = r.get("url", "")
        elif f == "lw_karma": out["lw_karma"] = r.get("lw_karma")
        elif f == "karma_per_vote": out["karma_per_vote"] = float(round(r["karma_per_vote"], 2)) if r.get("karma_per_vote") else None
        elif f == "stampy_score": out["stampy_score"] = r.get("miri_confidence")
        elif f == "tags":
            raw = r.get("tags_json")
            out["tags"] = _json.loads(raw) if raw else []
        elif f == "hash_id": out["hash_id"] = r.get("hash_id", "")
        elif f == "snippet_start": out["snippet_start"] = _snippet(r.get("text_start"))
        elif f == "snippet_middle": out["snippet_middle"] = _snippet(r.get("text_mid"))
        elif f == "snippet_end": out["snippet_end"] = _snippet(r.get("text_end"))
    return out


@mcp.tool
def lw_af_posts_sorted(
    sort_by: str = "date",
    n: int = 20,
    author: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    after: str | None = None,
    before: str | None = None,
    include: list[str] | None = None,
) -> list[dict]:
    """Browse AI safety articles sorted by date, karma, or a custom blend. Returns metadata and short text snippets (no full text -- use get_doc for that).

    Args:
        sort_by: Simple sorts: "date", "karma", "karma_per_vote", "stampy_score". Shorthand blend: a number 0.0-1.0 (0=newest, 1=highest karma). Custom blend: lerp_normed(field_a, field_b, t) where t=0 gives pure field_a, t=1 gives pure field_b. Fields: newness, oldness, karma, karma_per_vote, stampy_score. Examples: lerp_normed(newness, karma_per_vote, 0.7) for trending posts with strong agreement; lerp_normed(oldness, karma_per_vote, 0.3) for foundational work the community considers settled (good for literature review or understanding canonical alignment thinking); lerp_normed(karma, stampy_score, 0.5) for posts that are both popular and editorially valued.
        n: Number of results (1-200, default 20).
        author: Filter to articles by this author (substring match).
        source: Filter to one source: lesswrong, alignmentforum, arxiv, eaforum, blogs, arbital, etc.
        tag: Filter to articles with this tag (exact match, e.g. "Interpretability (ML & AI)"). Use lw_af_tags to see all tags.
        after: Only articles published on or after this date (ISO format, e.g. "2024-01-01").
        before: Only articles published on or before this date.
        include: Fields to return. Default: hash_id, title, authors, date, source, url, lw_karma, karma_per_vote, stampy_score, tags, snippet_start. Also available: snippet_middle, snippet_end.
    """
    if include is None: include = list(BROWSE_DEFAULTS)
    n = max(1, min(200, n))
    need_snippets = any(f.startswith("snippet_") for f in include)

    stmt = _browse_stmt(sort_by, source, author, tag, after, before, need_snippets)
    stmt = stmt.limit(n)

    with ard_engine.connect() as conn:
        rows = [dict(r) for r in conn.execute(stmt).mappings()]

    return [_format_row(r, include) for r in rows]


@mcp.tool
def lw_af_authors(
    n: int = 50,
    offset: int = 0,
    source: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> list[dict]:
    """List authors in the AI safety corpus, sorted by number of articles (most prolific first). Authors field is split on commas, so co-authored articles count for each author.

    Args:
        n: Max authors to return (1-500, default 50).
        offset: Skip this many authors for pagination (default 0).
        source: Filter to one source: lesswrong, alignmentforum, arxiv, eaforum, blogs, arbital, etc.
        after: Only count articles published on or after this date (ISO format, e.g. "2024-01-01").
        before: Only count articles published on or before this date.
    """
    n = max(1, min(500, n))
    stmt = select(articles.c.authors).where(articles.c.pinecone_status == "added")
    if source: stmt = stmt.where(articles.c.source == source)
    if after: stmt = stmt.where(articles.c.date_published >= after)
    if before: stmt = stmt.where(articles.c.date_published <= before)

    with ard_engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()

    counts = {}
    for (authors_str,) in rows:
        for a in (authors_str or "").split(","):
            a = a.strip()
            if a: counts[a] = counts.get(a, 0) + 1

    ranked = sorted(counts.items(), key=lambda x: -x[1])
    page = ranked[offset:offset + n]
    return [{"author": name, "articles": count} for name, count in page]


_LW_TAG_CATS = None
def _load_tag_cats():
    global _LW_TAG_CATS
    if _LW_TAG_CATS is None:
        cat_path = Path(__file__).resolve().parent / "lw_tag_categories.json"
        with open(cat_path) as f:
            _LW_TAG_CATS = _json.load(f)
    return _LW_TAG_CATS


@mcp.tool
def lw_af_tags() -> dict[str, list[str]]:
    """All tags in the AI safety corpus, grouped by LessWrong wiki category. Categories: AI, Rationality, World Modeling, World Optimization, Practical, Community, Site Meta, Other. Use tag names as the tag filter in lw_af_posts_sorted."""

    with ard_engine.connect() as conn:
        rows = conn.execute(sa_text(
            "SELECT DISTINCT jt.tag FROM articles,"
            " JSON_TABLE(metadata->'$.tags', '$[*]' COLUMNS (tag VARCHAR(200) PATH '$')) AS jt"
            " WHERE metadata->'$.tags' IS NOT NULL ORDER BY jt.tag"
        )).fetchall()

    cats = _load_tag_cats()
    grouped = {}
    for (tag,) in rows:
        cat = cats.get(tag, "Other")
        grouped.setdefault(cat, []).append(tag)
    # Sort categories in a sensible order
    order = ["AI", "Rationality", "World Modeling", "World Optimization", "Practical", "Community", "Site Meta", "Other"]
    return {c: grouped.get(c, []) for c in order if c in grouped}


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
