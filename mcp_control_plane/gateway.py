"""Identity resolution and filtered tool discovery."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from secrets import compare_digest, token_hex
from time import time

from mcp_control_plane.config import DemoConfig, Principal
from mcp_control_plane.downstream import call_maintenance_tool, call_telemetry_tool
from mcp_control_plane.storage import connect_database, record_audit


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


def discover_tools(
    config: DemoConfig,
    api_key: str | None,
    database: sqlite3.Connection | None = None,
) -> tuple[str, ...]:
    if database is None:
        with closing(connect_database()) as opened:
            return discover_tools(config, api_key, opened)

    principal = None
    try:
        principal = resolve_principal(config, api_key)
        tools = TOOLS_BY_ROLE[principal.role]
    except ControlPlaneError as error:
        record_audit(database, "discovery", None, None, "deny", error.code)
        raise
    record_audit(database, "discovery", principal.id, None, "allow", "AUTHORIZED")
    return tools


def _validate_arguments(tool_name: str, arguments: object) -> dict[str, str]:
    if not isinstance(arguments, dict) or set(arguments) != ARGUMENTS_BY_TOOL[tool_name]:
        raise ControlPlaneError("ARGUMENTS_INVALID")
    if any(not isinstance(value, str) or not value.strip() for value in arguments.values()):
        raise ControlPlaneError("ARGUMENTS_INVALID")
    return arguments


def _authorize_request(
    config: DemoConfig,
    principal: Principal,
    tool_name: str,
    arguments: object,
):
    if not isinstance(tool_name, str) or tool_name not in TOOLS_BY_ROLE[principal.role]:
        raise ControlPlaneError("TOOL_NOT_AUTHORIZED")
    validated = _validate_arguments(tool_name, arguments)
    equipment = config.equipment.get(validated["equipment_id"])
    if equipment is None:
        raise ControlPlaneError("EQUIPMENT_NOT_FOUND")
    if equipment.site != principal.assigned_site:
        raise ControlPlaneError("CROSS_SITE_ACCESS")
    return validated, equipment


def canonical_argument_hash(arguments: dict[str, str]) -> str:
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def approve_request(
    database: sqlite3.Connection,
    config: DemoConfig,
    supervisor_api_key: str | None,
    principal_id: str,
    tool_name: str,
    arguments: object,
    expires_in_seconds: int = 300,
) -> str:
    approver = resolve_principal(config, supervisor_api_key)
    if approver.role != "supervisor" or tool_name != "create_maintenance_ticket":
        raise ControlPlaneError("TOOL_NOT_AUTHORIZED")
    requester = config.principals.get(principal_id)
    if requester is None:
        raise ControlPlaneError("IDENTITY_INVALID")
    validated, equipment = _authorize_request(config, requester, tool_name, arguments)
    if equipment.site != approver.assigned_site:
        raise ControlPlaneError("CROSS_SITE_ACCESS")

    approval_id = token_hex(16)
    with database:
        database.execute(
            """INSERT INTO approvals
               (approval_id, principal_id, tool_name, argument_hash, equipment_site,
                approver_role, expires_at, used_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL)""",
            (
                approval_id,
                requester.id,
                tool_name,
                canonical_argument_hash(validated),
                equipment.site,
                approver.role,
                int(time()) + expires_in_seconds,
            ),
        )
    return approval_id


async def _invoke_approved_write(
    database: sqlite3.Connection,
    principal: Principal,
    tool_name: str,
    arguments: dict[str, str],
    equipment_site: str,
    approval_id: str,
) -> dict:
    approval = database.execute(
        """SELECT principal_id, tool_name, argument_hash, equipment_site,
                  approver_role, expires_at, used_at
           FROM approvals WHERE approval_id = ?""",
        (approval_id,),
    ).fetchone()
    if approval is None:
        raise ControlPlaneError("APPROVAL_MISMATCH")

    saved_principal, saved_tool, saved_hash, saved_site, role, expires_at, used_at = approval
    if used_at is not None:
        raise ControlPlaneError("APPROVAL_ALREADY_USED")
    if int(time()) >= expires_at:
        raise ControlPlaneError("APPROVAL_EXPIRED")
    if (
        saved_principal != principal.id
        or saved_tool != tool_name
        or saved_site != equipment_site
        or role != "supervisor"
        or not compare_digest(saved_hash, canonical_argument_hash(arguments))
    ):
        raise ControlPlaneError("APPROVAL_MISMATCH")

    try:
        ticket = await call_maintenance_tool(tool_name, arguments)
    except Exception as error:
        raise ControlPlaneError("DOWNSTREAM_FAILURE") from error
    with database:
        consumed = database.execute(
            "UPDATE approvals SET used_at = ? WHERE approval_id = ? AND used_at IS NULL",
            (int(time()), approval_id),
        )
        if consumed.rowcount != 1:
            raise ControlPlaneError("APPROVAL_ALREADY_USED")
    return ticket


async def invoke_tool(
    config: DemoConfig,
    api_key: str | None,
    tool_name: str,
    arguments: object,
    approval_id: str | None = None,
    database: sqlite3.Connection | None = None,
) -> dict:
    if database is None:
        with closing(connect_database()) as opened:
            return await invoke_tool(
                config, api_key, tool_name, arguments, approval_id, opened
            )

    principal = None
    audit_tool = tool_name if isinstance(tool_name, str) else None
    try:
        principal = resolve_principal(config, api_key)
        validated, equipment = _authorize_request(config, principal, tool_name, arguments)
        if tool_name == "create_maintenance_ticket":
            if not approval_id:
                raise ControlPlaneError("APPROVAL_REQUIRED")
            if not isinstance(approval_id, str):
                raise ControlPlaneError("APPROVAL_MISMATCH")
            result = await _invoke_approved_write(
                database, principal, tool_name, validated, equipment.site, approval_id
            )
        else:
            try:
                result = await call_telemetry_tool(tool_name, validated)
            except Exception as error:
                raise ControlPlaneError("DOWNSTREAM_FAILURE") from error
    except ControlPlaneError as error:
        principal_id = principal.id if principal else None
        record_audit(database, "invocation", principal_id, audit_tool, "deny", error.code)
        raise
    record_audit(database, "invocation", principal.id, audit_tool, "allow", "AUTHORIZED")
    return result
