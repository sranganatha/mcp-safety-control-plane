"""MCP client boundary for the two downstream servers."""

from __future__ import annotations

import os
import sys

from mcp import Client, StdioServerParameters


async def _call_server(module: str, tool_name: str, arguments: dict[str, str]) -> dict:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        env=os.environ.copy(),
    )
    async with Client(server, raise_exceptions=True, cache=None) as client:
        response = await client.call_tool(tool_name, arguments)
    if response.is_error or not isinstance(response.structured_content, dict):
        raise RuntimeError("downstream MCP call failed")
    return response.structured_content


async def call_telemetry_tool(tool_name: str, arguments: dict[str, str]) -> dict:
    return await _call_server(
        "mcp_control_plane.telemetry_server", tool_name, arguments
    )


async def call_maintenance_tool(tool_name: str, arguments: dict[str, str]) -> dict:
    return await _call_server(
        "mcp_control_plane.maintenance_server", tool_name, arguments
    )
