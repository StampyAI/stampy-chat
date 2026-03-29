#!/usr/bin/env python3
"""
Stampy Chat MCP Server

Thin wrappers around tools defined in stampy_chat.tools.
Provides search and retrieval tools for AI alignment research via MCP.
"""

from fastmcp import FastMCP
from stampy_chat import logging
from stampy_chat import tools

logger = logging.getLogger(__name__)

mcp = FastMCP("Stampy Backend RAG")


@mcp.tool
def lw_af_arxivsafety_search(
    query: str, k: int = 20, filter: dict | None = None,
    snippets_per_doc: int = 1,
) -> str:
    """Semantic search over 25k AI safety posts from LessWrong, Alignment Forum, arxiv (curated safety-relevant subset), EA Forum, blogs, and more. Updated within days of publication. Use for: finding prior alignment work, checking if an idea has been explored, retrieving specific researchers' writings, understanding current thinking on safety topics, finding counterarguments or failure modes for alignment proposals.

Key researchers: John Wentworth (johnswentworth; natural abstractions, natural latents, research methodology), Richard Ngo ("Richard Ngo"; coalitional/scale-free agency, AI governance), Abram Demski (abramdemski; logical induction, embedded agency, decision theory), Vanessa Kosoy (infra-Bayesianism, learning-theoretic alignment). Also covers: mechanistic interpretability, singular learning theory, computational mechanics, governance/policy, RLHF safety, scalable oversight, and more.

Filters: author, date range, source (lesswrong/alignmentforum/arxiv), quality score. Use filter={"authors": {"$in": ["Name"]}} for author search, filter={"date_published": {"$gte": "2024-01-01"}} for date ranges.

    Args:
        query: Natural language search query. Semantic search, so describe what you're looking for.
        k: Number of results (unset=20, max 50)
        snippets_per_doc: default 1, max 10
        filter: Pinecone metadata filter. Fields: title, authors, date_published (int|ISO str), url, source, needs_tech, quality_score (0-10). Operators: $eq $ne $gt $gte $lt $lte $in $nin $and $or.
    """
    model_output, _ui = tools.lw_af_arxivsafety_search(query, k, filter, snippets_per_doc)
    return model_output


@mcp.tool
def lw_af_arxivsafety_recent(
    query: str, days: int = 90, k: int = 20, filter: dict | None = None,
    snippets_per_doc: int = 1,
) -> str:
    """Search recent AI safety posts (default: last 90 days). Same corpus as lw_af_arxivsafety_search but pre-filtered to recent content. Use when you need current work, recent developments, or want to check what's been published lately on a topic.

    Args:
        query: Natural language search query.
        days: How far back to search, unset=90.
        k: Number of results (unset=20, max 50)
        snippets_per_doc: default 1, max 10
        filter: Pinecone metadata filter. Fields: title, authors, date_published (int|ISO str), url, source, needs_tech, quality_score (0-10). Operators: $eq $ne $gt $gte $lt $lte $in $nin $and $or (date constraint is added automatically).
    """
    model_output, _ui = tools.lw_af_arxivsafety_recent(query, days, k, filter, snippets_per_doc)
    return model_output


@mcp.tool
def lw_af_arxivsafety_get_doc(
    id: str | None = None, url: str | None = None, title: str | None = None,
    max_chars: int = tools.MAX_DOC_CHARS, offset: int = 0,
) -> str:
    """Retrieve full text of a single article from the alignment research corpus. Use after finding an interesting result via search to read the complete document. Accepts hash_id, URL, or exact title. Non-semantic content (base64, SVGs, Plotly data) is stripped; long articles are truncated (default 130k chars). Use offset to paginate through longer articles.

    Args:
        id: Article hash_id (shown as hash_id in formatted results, or 'id' in json results). Preferred lookup method.
        url: Article URL. Partial match.
        title: Exact article title.
        max_chars: Max characters to return (default 130000). The cleaned text length is reported in the response so you can decide whether to request more.
        offset: Character offset into cleaned text (default 0). Use to retrieve subsequent pages of a long article.
    """
    model_output, _ui = tools.lw_af_arxivsafety_get_doc(id, url, title, max_chars, offset)
    return model_output


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
) -> str:
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
    model_output, _ui = tools.lw_af_posts_sorted(sort_by, n, author, source, tag, after, before, include)
    return model_output


@mcp.tool
def lw_af_authors(
    n: int = 50,
    offset: int = 0,
    source: str | None = None,
    after: str | None = None,
    before: str | None = None,
) -> str:
    """List authors in the AI safety corpus, sorted by number of articles (most prolific first). Authors field is split on commas, so co-authored articles count for each author.

    Args:
        n: Max authors to return (1-500, default 50).
        offset: Skip this many authors for pagination (default 0).
        source: Filter to one source: lesswrong, alignmentforum, arxiv, eaforum, blogs, arbital, etc.
        after: Only count articles published on or after this date (ISO format, e.g. "2024-01-01").
        before: Only count articles published on or before this date.
    """
    model_output, _ui = tools.lw_af_authors(n, offset, source, after, before)
    return model_output


@mcp.tool
def lw_af_tags() -> str:
    """All tags in the AI safety corpus, grouped by LessWrong wiki category. Categories: AI, Rationality, World Modeling, World Optimization, Practical, Community, Site Meta, Other. Use tag names as the tag filter in lw_af_posts_sorted."""
    model_output, _ui = tools.lw_af_tags()
    return model_output


if __name__ == "__main__":
    logger.info("Starting Stampy Chat MCP server on port 3002")
    mcp.run(transport="http", host="0.0.0.0", port=3002)
