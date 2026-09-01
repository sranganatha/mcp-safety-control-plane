"""Deterministic end-to-end security demo."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing

from mcp_control_plane.config import load_config
from mcp_control_plane.gateway import (
    ControlPlaneError,
    approve_request,
    discover_tools,
    invoke_tool,
)
from mcp_control_plane.storage import initialize_database, verify_audit_chain


def _pass(label: str, condition: bool) -> None:
    if not condition:
        raise RuntimeError(f"demo check failed: {label}")
    print(f"PASS {label}")


def _denied(label: str, code: str, action: Callable[[], object]) -> None:
    try:
        action()
    except ControlPlaneError as error:
        _pass(label, error.code == code)
        return
    raise RuntimeError(f"demo check failed: {label}")


def run_demo() -> None:
    config = load_config("config/demo.json")
    with closing(initialize_database(sqlite3.connect(":memory:"))) as database:
        tools = discover_tools(config, "demo-eng-key", database)
        _pass(
            "engineer sees only permitted tools",
            tools
            == (
                "create_maintenance_ticket",
                "list_active_alarms",
                "read_equipment_status",
            ),
        )

        status = invoke_tool(
            config,
            "demo-eng-key",
            "read_equipment_status",
            {"equipment_id": "etch-101"},
            database=database,
        )
        _pass("assigned-site read succeeds", status["equipment_id"] == "etch-101")

        _denied(
            "cross-site read is denied",
            "CROSS_SITE_ACCESS",
            lambda: invoke_tool(
                config,
                "demo-eng-key",
                "read_equipment_status",
                {"equipment_id": "etch-201"},
                database=database,
            ),
        )

        arguments = {
            "equipment_id": "etch-101",
            "idempotency_key": "demo-ticket-1",
            "reason": "Inspect elevated temperature",
        }
        _denied(
            "write without approval is denied",
            "APPROVAL_REQUIRED",
            lambda: invoke_tool(
                config,
                "demo-eng-key",
                "create_maintenance_ticket",
                arguments,
                database=database,
            ),
        )

        approval_id = approve_request(
            database,
            config,
            "demo-sup-key",
            "eng-a",
            "create_maintenance_ticket",
            arguments,
        )
        ticket = invoke_tool(
            config,
            "demo-eng-key",
            "create_maintenance_ticket",
            arguments,
            approval_id,
            database,
        )
        _pass("exact approved write succeeds", ticket["ticket_id"] == "maint-001")

        _denied(
            "consumed approval cannot be replayed",
            "APPROVAL_ALREADY_USED",
            lambda: invoke_tool(
                config,
                "demo-eng-key",
                "create_maintenance_ticket",
                arguments,
                approval_id,
                database,
            ),
        )
        _pass("audit hash chain verifies", verify_audit_chain(database))


if __name__ == "__main__":
    run_demo()
