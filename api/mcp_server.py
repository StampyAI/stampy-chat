#!/usr/bin/env python3
"""
Stampy Chat MCP Server

Provides RAG search tools via Model Context Protocol for remote access.
"""

from datetime import datetime
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
                - authors (list[str]): Author names. Use $in for membership, eg {"authors": {"$in": ["Eliezer Yudkowsky"]}}
                - date_published (int|str): Unix timestamp or ISO date string (eg "2020-01-01", "2020-01-01T00:00:00Z"). Use $gte/$lte for date ranges
                - url (str): Source URL
                - source (str): Data source, eg "alignmentforum", "lesswrong", "arxiv"
                - needs_tech (bool): True = doc has formatting issues, awaiting reimport
                - quality_score (int): Content quality/relevance 0-10

                Examples:
                {"quality_score": {"$gte": 8}}
                {"needs_tech": false}
                {"date_published": {"$gte": 1577836800}}  (Jan 1, 2020)
                {"date_published": {"$gte": "2020-01-01"}}  (same, using ISO date)
                {"$and": [{"date_published": {"$gte": 1577836800}}, {"quality_score": {"$gte": 7}}]}

    Returns:
        If format="formatted": Formatted XML blocks with search results and citations
        If format="json": List of block dictionaries with metadata and text
    """
    # Debug logging to see what type we actually receive
    logger.info(f"MCP search raw filter parameter: type={type(filter)} value={filter!r}")

    # Convert ISO dates and remap quality_* fields to internal miri_* fields
    if filter:
        filter = _convert_date_fields(filter)
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


def _parse_date_to_timestamp(value: str | int) -> int:
    """Convert ISO date/datetime string to Unix timestamp, or pass through int."""
    if isinstance(value, int): return value
    if isinstance(value, str):
        # Try ISO datetime with timezone
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                return int(dt.timestamp())
            except ValueError:
                continue
        # Also try fromisoformat which handles more variants
        try: return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError: pass
        raise ValueError(f"Cannot parse date: {value!r}")
    return value  # Pass through other types unchanged


def _convert_date_fields(filter: dict) -> dict:
    """Recursively convert ISO date strings in date_published to Unix timestamps."""
    if not filter: return filter

    result = {}
    for key, value in filter.items():
        if key == "date_published":
            # value is either a direct value or a dict of operators
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
    logger.info(f"Starting Stampy Chat MCP server on port 3002")
    # Run as HTTP server for remote access via Caddy reverse proxy
    mcp.run(transport="http", host="127.0.0.1", port=3002)
