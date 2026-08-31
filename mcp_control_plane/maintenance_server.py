"""State-changing MCP tools for simulated equipment maintenance."""

from __future__ import annotations

import os
from typing import TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mcp_control_plane.config import load_config


mcp = MCPServer("equipment-maintenance")


class MaintenanceTicket(TypedDict):
    ticket_id: str
    equipment_id: str
    reason: str
    status: str


_tickets: dict[str, MaintenanceTicket] = {}


@mcp.tool()
def create_maintenance_ticket(
    equipment_id: str,
    reason: str,
    idempotency_key: str,
) -> MaintenanceTicket:
    """Create one maintenance ticket, safely retryable by idempotency key."""
    config = load_config(os.getenv("MCP_DEMO_CONFIG", "config/demo.json"))
    if equipment_id not in config.equipment:
        raise ToolError(f"unknown equipment: {equipment_id}")
    if not reason.strip():
        raise ToolError("reason must not be blank")
    if not idempotency_key.strip():
        raise ToolError("idempotency_key must not be blank")

    existing = _tickets.get(idempotency_key)
    request = {"equipment_id": equipment_id, "reason": reason}
    if existing:
        if request != {key: existing[key] for key in request}:
            raise ToolError("idempotency_key was already used for a different request")
        return existing

    ticket = {
        "ticket_id": f"maint-{len(_tickets) + 1:03d}",
        **request,
        "status": "open",
    }
    _tickets[idempotency_key] = ticket
    return ticket


if __name__ == "__main__":
    mcp.run()
