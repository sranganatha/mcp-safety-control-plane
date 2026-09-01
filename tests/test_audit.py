import sqlite3
import unittest

from mcp_control_plane.config import load_config
from mcp_control_plane.gateway import ControlPlaneError, discover_tools, invoke_tool
from mcp_control_plane.storage import initialize_database, verify_audit_chain


class AuditChainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config("config/demo.json")

    def setUp(self) -> None:
        self.database = initialize_database(sqlite3.connect(":memory:"))

    def tearDown(self) -> None:
        self.database.close()

    def test_invocation_attempts_record_decision_and_reason(self) -> None:
        invoke_tool(
            self.config,
            "demo-eng-key",
            "read_equipment_status",
            {"equipment_id": "etch-101"},
            database=self.database,
        )
        with self.assertRaises(ControlPlaneError):
            invoke_tool(
                self.config,
                "demo-eng-key",
                "read_equipment_status",
                {"equipment_id": "etch-201"},
                database=self.database,
            )

        decisions = self.database.execute(
            "SELECT decision, reason_code FROM audit_events ORDER BY id"
        ).fetchall()
        self.assertEqual(
            [("allow", "AUTHORIZED"), ("deny", "CROSS_SITE_ACCESS")], decisions
        )

    def test_discovery_attempts_are_audited_without_api_keys(self) -> None:
        discover_tools(self.config, "demo-eng-key", self.database)
        with self.assertRaises(ControlPlaneError):
            discover_tools(self.config, "secret-unknown-key", self.database)

        rows = self.database.execute("SELECT * FROM audit_events ORDER BY id").fetchall()
        self.assertEqual(2, len(rows))
        self.assertNotIn("demo-eng-key", repr(rows))
        self.assertNotIn("secret-unknown-key", repr(rows))

    def test_intact_chain_verifies(self) -> None:
        discover_tools(self.config, "demo-eng-key", self.database)

        self.assertTrue(verify_audit_chain(self.database))

    def test_changed_event_fails_verification(self) -> None:
        discover_tools(self.config, "demo-eng-key", self.database)
        self.database.execute(
            "UPDATE audit_events SET reason_code = 'TAMPERED' WHERE id = 1"
        )

        self.assertFalse(verify_audit_chain(self.database))


if __name__ == "__main__":
    unittest.main()
