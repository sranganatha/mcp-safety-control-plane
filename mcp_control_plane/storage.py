"""Minimal SQLite storage for approvals, tickets, and audit events."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from time import time


GENESIS_HASH = "0" * 64


SCHEMA = """
CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    argument_hash TEXT NOT NULL,
    equipment_site TEXT NOT NULL,
    approver_role TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT UNIQUE NOT NULL,
    equipment_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    principal_id TEXT,
    tool_name TEXT,
    decision TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL
);
"""


def initialize_database(database: sqlite3.Connection) -> sqlite3.Connection:
    database.executescript(SCHEMA)
    return database


def connect_database(path: str | None = None) -> sqlite3.Connection:
    database = sqlite3.connect(path or os.getenv("MCP_DB_PATH", "control-plane.db"))
    return initialize_database(database)


def _event_hash(event: dict[str, int | str | None], previous_hash: str) -> str:
    canonical = json.dumps(
        event, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(f"{previous_hash}\n{canonical}".encode()).hexdigest()


def record_audit(
    database: sqlite3.Connection,
    event_type: str,
    principal_id: str | None,
    tool_name: str | None,
    decision: str,
    reason_code: str,
) -> None:
    previous = database.execute(
        "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
    ).fetchone()
    previous_hash = previous[0] if previous else GENESIS_HASH
    event: dict[str, int | str | None] = {
        "created_at": int(time()),
        "event_type": event_type,
        "principal_id": principal_id,
        "tool_name": tool_name,
        "decision": decision,
        "reason_code": reason_code,
    }
    with database:
        database.execute(
            """INSERT INTO audit_events
               (created_at, event_type, principal_id, tool_name, decision,
                reason_code, previous_hash, event_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (*event.values(), previous_hash, _event_hash(event, previous_hash)),
        )


def verify_audit_chain(database: sqlite3.Connection) -> bool:
    previous_hash = GENESIS_HASH
    rows = database.execute(
        """SELECT created_at, event_type, principal_id, tool_name, decision,
                  reason_code, previous_hash, event_hash
           FROM audit_events ORDER BY id"""
    )
    for row in rows:
        (
            created_at,
            event_type,
            principal_id,
            tool_name,
            decision,
            reason_code,
            saved_previous,
            saved_hash,
        ) = row
        event: dict[str, int | str | None] = {
            "created_at": created_at,
            "event_type": event_type,
            "principal_id": principal_id,
            "tool_name": tool_name,
            "decision": decision,
            "reason_code": reason_code,
        }
        if saved_previous != previous_hash or saved_hash != _event_hash(
            event, previous_hash
        ):
            return False
        previous_hash = saved_hash
    return True
