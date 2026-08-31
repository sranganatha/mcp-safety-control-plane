"""Minimal SQLite storage for approvals and maintenance tickets."""

from __future__ import annotations

import os
import sqlite3


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
"""


def initialize_database(database: sqlite3.Connection) -> sqlite3.Connection:
    database.executescript(SCHEMA)
    return database


def connect_database(path: str | None = None) -> sqlite3.Connection:
    database = sqlite3.connect(path or os.getenv("MCP_DB_PATH", "control-plane.db"))
    return initialize_database(database)
