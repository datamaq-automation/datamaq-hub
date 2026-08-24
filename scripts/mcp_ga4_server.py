#!/usr/bin/env python3
"""Punto de entrada del servidor FastMCP para Google Analytics 4 (DataMaq)."""

from typing import Any, cast

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    FastMCP = None  # type: ignore

from src.infrastructure.fastmcp.ga4 import (
    get_ga4_conversions,
    get_ga4_geo_traffic,
    get_ga4_status,
    get_ga4_top_pages,
    get_ga4_traffic_sources,
)

mcp: Any = (
    cast(Any, FastMCP("DataMaq GA4 Analytics MCP")) if FastMCP is not None else None
)

if mcp:
    mcp.tool()(get_ga4_status)
    mcp.tool()(get_ga4_top_pages)
    mcp.tool()(get_ga4_traffic_sources)
    mcp.tool()(get_ga4_geo_traffic)
    mcp.tool()(get_ga4_conversions)

if __name__ == "__main__":
    if mcp:
        mcp.run(transport="stdio")
    else:
        print("FastMCP no disponible.")
