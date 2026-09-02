#!/usr/bin/env python3
"""Punto de entrada del servidor FastMCP para Google Business Profile (DataMaq)."""

from typing import Any, cast

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    FastMCP = None  # type: ignore

from src.infrastructure.fastmcp.gbp import (
    create_gbp_post,
    get_gbp_location_info,
    get_gbp_performance,
    get_gbp_reviews,
    get_gbp_search_keywords,
    get_gbp_status,
    reply_to_gbp_review,
)

mcp: Any = (
    cast(Any, FastMCP("DataMaq Google Business Profile MCP"))
    if FastMCP is not None
    else None
)

if mcp:
    mcp.tool()(get_gbp_status)
    mcp.tool()(get_gbp_location_info)
    mcp.tool()(get_gbp_performance)
    mcp.tool()(get_gbp_search_keywords)
    mcp.tool()(get_gbp_reviews)
    mcp.tool()(create_gbp_post)
    mcp.tool()(reply_to_gbp_review)

if __name__ == "__main__":
    if mcp:
        mcp.run(transport="stdio")
    else:
        print("FastMCP no disponible.")
