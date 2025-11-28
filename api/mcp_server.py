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
def search_alignment_research(query: str, k: int = 20, filter: dict | None = None) -> str:
    """
    Search AI alignment research database for relevant content.

    Returns formatted citation blocks with source information including:
    - Title and authors
    - Publication date
    - URL with text fragment for precise location
    - Relevant text excerpt

    Args:
        query: The search query string
        k: Number of results to return (default: 20, max: 50)
        filter: Optional Pinecone metadata filter dict. Supports operators like $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, $or.
                Example: {"year": {"$gte": 2020}, "genre": {"$eq": "technical"}}

    Returns:
        Formatted XML blocks with search results and citations
    """
    logger.info(f"MCP search request: query='{query}' k={k} filter={filter}")

    # Clamp k to reasonable bounds
    k = max(1, min(50, k))

    try:
        blocks = get_top_k_blocks(query, k, filter)
        formatted = format_blocks(blocks)

        logger.info(f"MCP search returned {len(blocks)} results")
        return formatted
    except Exception as e:
        logger.error(f"MCP search error: {e}", exc_info=True)
        return f"<error>Search failed: {str(e)}</error>"


@mcp.tool
def search_alignment_research_raw(query: str, k: int = 20, filter: dict | None = None) -> list[dict]:
    """
    Search AI alignment research database and return raw block data.

    Returns unformatted block data as JSON for custom processing.

    Args:
        query: The search query string
        k: Number of results to return (default: 20, max: 50)
        filter: Optional Pinecone metadata filter dict. Supports operators like $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $and, $or.
                Example: {"year": {"$gte": 2020}, "genre": {"$eq": "technical"}}

    Returns:
        List of block dictionaries with metadata and text
    """
    logger.info(f"MCP raw search request: query='{query}' k={k} filter={filter}")

    # Clamp k to reasonable bounds
    k = max(1, min(50, k))

    try:
        blocks = get_top_k_blocks(query, k, filter)
        logger.info(f"MCP raw search returned {len(blocks)} results")

        # Convert TypedDict to plain dict for JSON serialization
        return [dict(block) for block in blocks]
    except Exception as e:
        logger.error(f"MCP raw search error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info(f"Starting Stampy Chat MCP server on port 3002")
    # Run as HTTP server for remote access via Caddy reverse proxy
    mcp.run(transport="http", host="127.0.0.1", port=3002)
