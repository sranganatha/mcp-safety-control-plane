import unittest

from mcp_control_plane.config import load_config
from mcp_control_plane.gateway import ControlPlaneError, discover_tools


class FilteredDiscoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config("config/demo.json")

    def test_missing_identity_is_rejected(self) -> None:
        with self.assertRaises(ControlPlaneError) as caught:
            discover_tools(self.config, None)

        self.assertEqual("IDENTITY_REQUIRED", caught.exception.code)

    def test_unknown_identity_is_rejected_without_echoing_key(self) -> None:
        with self.assertRaises(ControlPlaneError) as caught:
            discover_tools(self.config, "secret-unknown-key")

        self.assertEqual("IDENTITY_INVALID", caught.exception.code)
        self.assertNotIn("secret-unknown-key", str(caught.exception))

    def test_engineer_discovers_all_policy_permitted_tools(self) -> None:
        self.assertEqual(
            (
                "create_maintenance_ticket",
                "list_active_alarms",
                "read_equipment_status",
            ),
            discover_tools(self.config, "demo-eng-key"),
        )

    def test_supervisor_does_not_discover_write_tool(self) -> None:
        self.assertEqual(
            ("list_active_alarms", "read_equipment_status"),
            discover_tools(self.config, "demo-sup-key"),
        )

    def test_api_key_is_hidden_from_principal_repr(self) -> None:
        self.assertNotIn("demo-eng-key", repr(self.config.principals["eng-a"]))
