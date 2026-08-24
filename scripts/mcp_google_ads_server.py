#!/usr/bin/env python3
"""Punto de entrada del servidor FastMCP para Google Ads (DataMaq)."""

from typing import Any, cast

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    FastMCP = None  # type: ignore

from src.infrastructure.fastmcp.google_ads import (
    get_campaign_performance,
    get_daily_budget_pacing,
    get_google_ads_status,
    get_search_terms_report,
)

mcp: Any = cast(Any, FastMCP("DataMaq Google Ads MCP")) if FastMCP is not None else None

if mcp:
    mcp.tool()(get_google_ads_status)
    mcp.tool()(get_campaign_performance)
    mcp.tool()(get_search_terms_report)
    mcp.tool()(get_daily_budget_pacing)

if __name__ == "__main__":
    if mcp:
        mcp.run(transport="stdio")
    else:
        print("FastMCP no disponible.")
