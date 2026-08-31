import sqlite3
import unittest
from unittest.mock import Mock, patch

from mcp_control_plane.config import load_config
from mcp_control_plane.gateway import (
    ControlPlaneError,
    approve_request,
    canonical_argument_hash,
    invoke_tool,
)
from mcp_control_plane.storage import initialize_database


class ApprovalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config("config/demo.json")
        self.database = initialize_database(sqlite3.connect(":memory:"))
        self.arguments = {
            "equipment_id": "etch-101",
            "reason": "Inspect alarm",
            "idempotency_key": "request-1",
        }

    def tearDown(self) -> None:
        self.database.close()

    def approve(self) -> str:
        return approve_request(
            self.database,
            self.config,
            "demo-sup-key",
            "eng-a",
            "create_maintenance_ticket",
            self.arguments,
        )

    def invoke(self, approval_id: str, arguments: dict[str, str] | None = None) -> dict:
        return invoke_tool(
            self.config,
            "demo-eng-key",
            "create_maintenance_ticket",
            arguments or self.arguments,
            approval_id,
            self.database,
        )

    def assert_denied(self, code: str, approval_id: str, arguments=None) -> None:
        with self.assertRaises(ControlPlaneError) as caught:
            self.invoke(approval_id, arguments)
        self.assertEqual(code, caught.exception.code)

    def test_exact_approval_creates_ticket_and_is_consumed(self) -> None:
        approval_id = self.approve()

        ticket = self.invoke(approval_id)

        self.assertEqual("maint-001", ticket["ticket_id"])
        used_at = self.database.execute(
            "SELECT used_at FROM approvals WHERE approval_id = ?", (approval_id,)
        ).fetchone()[0]
        self.assertIsNotNone(used_at)
        self.assertEqual(1, self.database.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])

    def test_modified_arguments_do_not_match(self) -> None:
        approval_id = self.approve()
        modified = {**self.arguments, "reason": "Different reason"}

        self.assert_denied("APPROVAL_MISMATCH", approval_id, modified)

        self.assertEqual(0, self.database.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])

    def test_approval_cannot_authorize_other_site(self) -> None:
        approval_id = self.approve()
        other_site = {**self.arguments, "equipment_id": "etch-201"}

        self.assert_denied("CROSS_SITE_ACCESS", approval_id, other_site)

        used_at = self.database.execute(
            "SELECT used_at FROM approvals WHERE approval_id = ?", (approval_id,)
        ).fetchone()[0]
        self.assertIsNone(used_at)

    def test_canonical_hash_ignores_key_order(self) -> None:
        reordered = dict(reversed(list(self.arguments.items())))
        self.assertEqual(
            canonical_argument_hash(self.arguments),
            canonical_argument_hash(reordered),
        )

    def test_expired_approval_is_rejected(self) -> None:
        with patch("mcp_control_plane.gateway.time", return_value=1000):
            approval_id = self.approve()
        with patch("mcp_control_plane.gateway.time", return_value=1300):
            self.assert_denied("APPROVAL_EXPIRED", approval_id)

    def test_consumed_approval_cannot_be_reused(self) -> None:
        approval_id = self.approve()
        self.invoke(approval_id)

        self.assert_denied("APPROVAL_ALREADY_USED", approval_id)

    def test_downstream_failure_leaves_approval_unused(self) -> None:
        approval_id = self.approve()
        downstream = Mock(side_effect=RuntimeError("failure"))

        with patch("mcp_control_plane.gateway.WRITE_TOOL", downstream):
            self.assert_denied("DOWNSTREAM_FAILURE", approval_id)

        used_at = self.database.execute(
            "SELECT used_at FROM approvals WHERE approval_id = ?", (approval_id,)
        ).fetchone()[0]
        self.assertIsNone(used_at)

    def test_unknown_approval_is_a_mismatch(self) -> None:
        self.assert_denied("APPROVAL_MISMATCH", "unknown-approval")

    def test_engineer_cannot_approve(self) -> None:
        with self.assertRaises(ControlPlaneError) as caught:
            approve_request(
                self.database,
                self.config,
                "demo-eng-key",
                "eng-a",
                "create_maintenance_ticket",
                self.arguments,
            )
        self.assertEqual("TOOL_NOT_AUTHORIZED", caught.exception.code)
