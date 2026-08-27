#!/usr/bin/env python3
"""Punto de entrada del servidor FastMCP para Microsoft Clarity (DataMaq)."""

from typing import Any, cast

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:
    FastMCP = None  # type: ignore

from src.infrastructure.fastmcp.clarity import (
    get_clarity_project_info,
    get_dashboard_insights,
    get_intent_recording_urls,
    get_live_insights,
    get_recording_url,
)

mcp: Any = cast(Any, FastMCP("DataMaq Clarity MCP")) if FastMCP is not None else None

if mcp:
    mcp.tool()(get_clarity_project_info)
    mcp.tool()(get_live_insights)
    mcp.tool()(get_dashboard_insights)
    mcp.tool()(get_intent_recording_urls)
    mcp.tool()(get_recording_url)

if __name__ == "__main__":
    if mcp:
        mcp.run(transport="stdio")
    else:
        print("FastMCP no disponible.")
