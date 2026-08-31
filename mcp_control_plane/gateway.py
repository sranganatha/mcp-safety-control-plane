"""Identity resolution and filtered tool discovery."""

from __future__ import annotations

from secrets import compare_digest
from typing import Callable

from mcp_control_plane.config import DemoConfig, Principal
from mcp_control_plane.telemetry_server import (
    list_active_alarms,
    read_equipment_status,
)


TOOLS_BY_ROLE = {
    "engineer": (
        "create_maintenance_ticket",
        "list_active_alarms",
        "read_equipment_status",
    ),
    "supervisor": ("list_active_alarms", "read_equipment_status"),
}
ARGUMENTS_BY_TOOL = {
    "create_maintenance_ticket": {"equipment_id", "idempotency_key", "reason"},
    "list_active_alarms": {"equipment_id"},
    "read_equipment_status": {"equipment_id"},
}
READ_TOOLS: dict[str, Callable[..., dict]] = {
    "list_active_alarms": list_active_alarms,
    "read_equipment_status": read_equipment_status,
}


class ControlPlaneError(ValueError):
    """A rejected control-plane request with a stable reason code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def resolve_principal(config: DemoConfig, api_key: str | None) -> Principal:
    if not api_key:
        raise ControlPlaneError("IDENTITY_REQUIRED")
    for principal in config.principals.values():
        if compare_digest(principal.api_key.encode(), api_key.encode()):
            return principal
    raise ControlPlaneError("IDENTITY_INVALID")


def discover_tools(config: DemoConfig, api_key: str | None) -> tuple[str, ...]:
    principal = resolve_principal(config, api_key)
    return TOOLS_BY_ROLE[principal.role]


def _validate_arguments(tool_name: str, arguments: object) -> dict[str, str]:
    if not isinstance(arguments, dict) or set(arguments) != ARGUMENTS_BY_TOOL[tool_name]:
        raise ControlPlaneError("ARGUMENTS_INVALID")
    if any(not isinstance(value, str) or not value.strip() for value in arguments.values()):
        raise ControlPlaneError("ARGUMENTS_INVALID")
    return arguments


def invoke_tool(
    config: DemoConfig,
    api_key: str | None,
    tool_name: str,
    arguments: object,
) -> dict:
    principal = resolve_principal(config, api_key)
    if not isinstance(tool_name, str) or tool_name not in TOOLS_BY_ROLE[principal.role]:
        raise ControlPlaneError("TOOL_NOT_AUTHORIZED")

    validated = _validate_arguments(tool_name, arguments)
    equipment = config.equipment.get(validated["equipment_id"])
    if equipment is None:
        raise ControlPlaneError("EQUIPMENT_NOT_FOUND")
    if equipment.site != principal.assigned_site:
        raise ControlPlaneError("CROSS_SITE_ACCESS")
    if tool_name == "create_maintenance_ticket":
        raise ControlPlaneError("APPROVAL_REQUIRED")

    try:
        return READ_TOOLS[tool_name](**validated)
    except Exception as error:
        raise ControlPlaneError("DOWNSTREAM_FAILURE") from error
