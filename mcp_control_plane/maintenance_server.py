"""State-changing MCP tools for simulated equipment maintenance."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from typing import TypedDict

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mcp_control_plane.config import load_config
from mcp_control_plane.storage import connect_database


mcp = MCPServer("equipment-maintenance")


class MaintenanceTicket(TypedDict):
    ticket_id: str
    equipment_id: str
    reason: str
    status: str


def create_ticket(
    database: sqlite3.Connection,
    equipment_id: str,
    reason: str,
    idempotency_key: str,
) -> MaintenanceTicket:
    existing = database.execute(
        "SELECT id, equipment_id, reason, status FROM tickets WHERE idempotency_key = ?",
        (idempotency_key,),
    ).fetchone()
    if existing:
        ticket_id, saved_equipment, saved_reason, status = existing
        if (equipment_id, reason) != (saved_equipment, saved_reason):
            raise ToolError("idempotency_key was already used for a different request")
        return {
            "ticket_id": f"maint-{ticket_id:03d}",
            "equipment_id": saved_equipment,
            "reason": saved_reason,
            "status": status,
        }

    cursor = database.execute(
        "INSERT INTO tickets (idempotency_key, equipment_id, reason, status) VALUES (?, ?, ?, 'open')",
        (idempotency_key, equipment_id, reason),
    )
    return {
        "ticket_id": f"maint-{cursor.lastrowid:03d}",
        "equipment_id": equipment_id,
        "reason": reason,
        "status": "open",
    }


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

    with closing(connect_database()) as database, database:
        return create_ticket(database, equipment_id, reason, idempotency_key)


if __name__ == "__main__":
    mcp.run()
