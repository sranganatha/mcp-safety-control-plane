"""Deterministic end-to-end security demo."""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import closing
from tempfile import TemporaryDirectory

from mcp import Client, StdioServerParameters
from mcp_types import CallToolResult

from mcp_control_plane.config import load_config
from mcp_control_plane.gateway import approve_request
from mcp_control_plane.gateway_server import API_KEY_META
from mcp_control_plane.storage import connect_database, verify_audit_chain


def _pass(label: str, condition: bool) -> None:
    if not condition:
        raise RuntimeError(f"demo check failed: {label}")
    print(f"PASS {label}")


def _denied(label: str, code: str, response: CallToolResult) -> None:
    messages = [part.text for part in response.content if hasattr(part, "text")]
    _pass(label, response.is_error and any(code in message for message in messages))


async def run_demo() -> None:
    config = load_config("config/demo.json")
    identity = {API_KEY_META: "demo-eng-key"}
    with TemporaryDirectory() as temporary_directory:
        database_path = f"{temporary_directory}/demo.db"
        server_environment = {**os.environ, "MCP_DB_PATH": database_path}
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_control_plane.gateway_server"],
            env=server_environment,
        )
        with closing(connect_database(database_path)) as database:
            async with Client(server, raise_exceptions=True, cache=None) as client:
                tools = await client.list_tools(meta=identity)
                _pass(
                    "engineer sees only permitted tools",
                    sorted(tool.name for tool in tools.tools)
                    == [
                        "create_maintenance_ticket",
                        "list_active_alarms",
                        "read_equipment_status",
                    ],
                )

                status = await client.call_tool(
                    "read_equipment_status",
                    {"equipment_id": "etch-101"},
                    meta=identity,
                )
                status_data = status.structured_content or {}
                _pass(
                    "assigned-site read succeeds",
                    not status.is_error
                    and status_data.get("equipment_id") == "etch-101",
                )

                cross_site = await client.call_tool(
                    "read_equipment_status",
                    {"equipment_id": "etch-201"},
                    meta=identity,
                )
                _denied("cross-site read is denied", "CROSS_SITE_ACCESS", cross_site)

                arguments = {
                    "equipment_id": "etch-101",
                    "idempotency_key": "demo-ticket-1",
                    "reason": "Inspect elevated temperature",
                }
                unapproved = await client.call_tool(
                    "create_maintenance_ticket", arguments, meta=identity
                )
                _denied(
                    "write without approval is denied",
                    "APPROVAL_REQUIRED",
                    unapproved,
                )

                approval_id = approve_request(
                    database,
                    config,
                    "demo-sup-key",
                    "eng-a",
                    "create_maintenance_ticket",
                    arguments,
                )
                ticket = await client.call_tool(
                    "create_maintenance_ticket",
                    {**arguments, "approval_id": approval_id},
                    meta=identity,
                )
                ticket_data = ticket.structured_content or {}
                _pass(
                    "exact approved write succeeds",
                    not ticket.is_error
                    and ticket_data.get("ticket_id") == "maint-001",
                )

                replay = await client.call_tool(
                    "create_maintenance_ticket",
                    {**arguments, "approval_id": approval_id},
                    meta=identity,
                )
                _denied(
                    "consumed approval cannot be replayed",
                    "APPROVAL_ALREADY_USED",
                    replay,
                )
            _pass("audit hash chain verifies", verify_audit_chain(database))


if __name__ == "__main__":
    asyncio.run(run_demo())
