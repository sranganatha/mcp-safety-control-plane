"""Identity resolution and filtered tool discovery."""

from __future__ import annotations

from secrets import compare_digest

from mcp_control_plane.config import DemoConfig, Principal


TOOLS_BY_ROLE = {
    "engineer": (
        "create_maintenance_ticket",
        "list_active_alarms",
        "read_equipment_status",
    ),
    "supervisor": ("list_active_alarms", "read_equipment_status"),
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
