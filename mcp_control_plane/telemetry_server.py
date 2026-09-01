"""Read-only MCP tools backed by deterministic equipment fixtures."""

from __future__ import annotations

import os

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mcp_control_plane.config import load_config
from mcp_control_plane.contracts import AlarmList, EquipmentStatus


mcp = MCPServer("equipment-telemetry")


def _equipment(equipment_id: str):
    config = load_config(os.getenv("MCP_DEMO_CONFIG", "config/demo.json"))
    try:
        return config.equipment[equipment_id]
    except KeyError as error:
        raise ToolError(f"unknown equipment: {equipment_id}") from error


@mcp.tool()
def read_equipment_status(equipment_id: str) -> EquipmentStatus:
    """Return the current deterministic status for one equipment unit."""
    equipment = _equipment(equipment_id)
    return {
        "equipment_id": equipment.id,
        "site": equipment.site,
        "temperature_c": equipment.temperature_c,
        "status": "alarm" if equipment.alarms else "normal",
    }


@mcp.tool()
def list_active_alarms(equipment_id: str) -> AlarmList:
    """Return active alarms for one equipment unit."""
    equipment = _equipment(equipment_id)
    return {"equipment_id": equipment.id, "alarms": list(equipment.alarms)}


if __name__ == "__main__":
    mcp.run()
