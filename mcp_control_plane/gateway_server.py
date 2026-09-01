"""Governed MCP gateway for equipment tools."""

from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.shared.exceptions import MCPError
from mcp_types import INVALID_REQUEST

from mcp_control_plane.config import load_config
from mcp_control_plane.contracts import AlarmList, EquipmentStatus, MaintenanceTicket
from mcp_control_plane.gateway import ControlPlaneError, discover_tools, invoke_tool


API_KEY_META = "io.github.sranganatha.mcp-safety-control-plane/api-key"
config = load_config(os.getenv("MCP_DEMO_CONFIG", "config/demo.json"))


def _api_key(meta: dict[str, Any] | None) -> str | None:
    api_key = (meta or {}).get(API_KEY_META)
    return api_key if isinstance(api_key, str) else None


async def _filter_tool_discovery(
    request: ServerRequestContext[Any, Any], call_next: CallNext
) -> HandlerResult:
    if request.method != "tools/list":
        return await call_next(request)
    try:
        permitted = discover_tools(config, _api_key(request.meta))
    except ControlPlaneError as error:
        raise MCPError(INVALID_REQUEST, error.code) from error
    response = await call_next(request)
    if not isinstance(response, dict) or not isinstance(response.get("tools"), list):
        return response
    return {
        **response,
        "tools": [tool for tool in response["tools"] if tool.get("name") in permitted],
    }


mcp = MCPServer("mcp-safety-control-plane", middleware=[_filter_tool_discovery])


async def _invoke(
    context: Context,
    tool_name: str,
    arguments: dict[str, str],
    approval_id: str | None = None,
) -> dict:
    try:
        return await invoke_tool(
            config,
            _api_key(context.request_context.meta),
            tool_name,
            arguments,
            approval_id,
        )
    except ControlPlaneError as error:
        raise ToolError(error.code) from error


@mcp.tool()
async def read_equipment_status(
    equipment_id: str, context: Context
) -> EquipmentStatus:
    """Return status when gateway policy permits this equipment read."""
    return await _invoke(
        context, "read_equipment_status", {"equipment_id": equipment_id}
    )


@mcp.tool()
async def list_active_alarms(equipment_id: str, context: Context) -> AlarmList:
    """Return alarms when gateway policy permits this equipment read."""
    return await _invoke(context, "list_active_alarms", {"equipment_id": equipment_id})


@mcp.tool()
async def create_maintenance_ticket(
    equipment_id: str,
    reason: str,
    idempotency_key: str,
    context: Context,
    approval_id: str | None = None,
) -> MaintenanceTicket:
    """Create a ticket when gateway policy and exact approval permit it."""
    return await _invoke(
        context,
        "create_maintenance_ticket",
        {
            "equipment_id": equipment_id,
            "reason": reason,
            "idempotency_key": idempotency_key,
        },
        approval_id,
    )


if __name__ == "__main__":
    mcp.run()
