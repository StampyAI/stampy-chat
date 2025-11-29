#!/usr/bin/env python3
"""
Stampy Chat MCP Server

Provides RAG search tools via Model Context Protocol for remote access.
"""

from fastmcp import FastMCP
from stampy_chat.citations import get_top_k_blocks, Block
from stampy_chat.prompts import format_blocks
from stampy_chat import logging

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Stampy Backend RAG")


@mcp.tool
def search_alignment_research(
    query: str, k: int = 20, filter: dict | None = None, format: str = "formatted"
) -> str | list[dict]:
    """
    Search AI alignment research database for relevant content.

    Args:
        query: The search query string
        k: Number of results to return (default: 20, max: 50)
        format: Output format - "formatted" returns XML citation blocks, "json" returns raw dicts (default: "formatted")
        filter: Optional Pinecone metadata filter dict. Supports operators: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, $or

                Available metadata fields:
                - title (str): Document title
                - authors (list[str]): Author names
                - date_published (str): ISO date string
                - tags (list[str]): Topic tags
                - url (str): Source URL
                - needs_tech (bool): True = doc damaged, needs import fix
                - quality_score (int): Content quality/relevance 0-10

                Examples:
                {"quality_score": {"$gte": 8}}
                {"needs_tech": false}
                {"$and": [{"date_published": {"$gte": "2020-01-01"}}, {"quality_score": {"$gte": 7}}]}

    Returns:
        If format="formatted": Formatted XML blocks with search results and citations
        If format="json": List of block dictionaries with metadata and text
    """
    # Remap quality_* fields to internal miri_* fields
    if filter:
        filter = _remap_quality_fields(filter)

    logger.info(f"MCP search request: query='{query}' k={k} format={format} filter={filter}")

    # Clamp k to reasonable bounds
    k = max(1, min(50, k))

    try:
        blocks = get_top_k_blocks(query, k, filter)
        logger.info(f"MCP search returned {len(blocks)} results")

        if format == "json":
            return [dict(block) for block in blocks]
        else:
            return format_blocks(blocks)
    except Exception as e:
        logger.error(f"MCP search error: {e}", exc_info=True)
        if format == "json":
            raise
        else:
            return f"<error>Search failed: {str(e)}</error>"


def _remap_quality_fields(filter: dict) -> dict:
    """Remap MCP client-facing quality_* fields to internal miri_* fields."""
    if not filter:
        return filter

    # Deep copy to avoid mutating input
    result = {}

    for key, value in filter.items():
        if key == "quality_score":
            result["miri_confidence"] = value
        elif key == "quality_distance":
            raise ValueError("quality_distance filter is deprecated and no longer supported")
        elif key in ("$and", "$or"):
            # Recursively remap nested filters
            result[key] = [_remap_quality_fields(f) for f in value]
        else:
            result[key] = value

    return result


if __name__ == "__main__":
    logger.info(f"Starting Stampy Chat MCP server on port 3002")
    # Run as HTTP server for remote access via Caddy reverse proxy
    mcp.run(transport="http", host="127.0.0.1", port=3002)
