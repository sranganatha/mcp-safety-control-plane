import unittest
from unittest.mock import AsyncMock, patch

from mcp_control_plane.config import load_config
from mcp_control_plane.gateway import (
    ControlPlaneError,
    discover_tools,
    invoke_tool,
)


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


class InvocationAuthorizationTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config("config/demo.json")

    async def assert_denied(
        self, code: str, tool_name: str, arguments: object
    ) -> None:
        with self.assertRaises(ControlPlaneError) as caught:
            await invoke_tool(self.config, "demo-eng-key", tool_name, arguments)
        self.assertEqual(code, caught.exception.code)

    async def test_assigned_site_read_reaches_downstream(self) -> None:
        downstream = AsyncMock(return_value={"status": "alarm"})
        with patch("mcp_control_plane.gateway.call_telemetry_tool", downstream):
            result = await invoke_tool(
                self.config,
                "demo-eng-key",
                "read_equipment_status",
                {"equipment_id": "etch-101"},
            )

        self.assertEqual("alarm", result["status"])
        downstream.assert_awaited_once_with(
            "read_equipment_status", {"equipment_id": "etch-101"}
        )

    async def test_invalid_arguments_stop_before_downstream(self) -> None:
        downstream = AsyncMock()
        with patch("mcp_control_plane.gateway.call_telemetry_tool", downstream):
            await self.assert_denied(
                "ARGUMENTS_INVALID",
                "read_equipment_status",
                {"equipment_id": "etch-101", "site": "site-a"},
            )
        downstream.assert_not_awaited()

    async def test_unknown_equipment_stops_before_downstream(self) -> None:
        downstream = AsyncMock()
        with patch("mcp_control_plane.gateway.call_telemetry_tool", downstream):
            await self.assert_denied(
                "EQUIPMENT_NOT_FOUND",
                "read_equipment_status",
                {"equipment_id": "missing"},
            )
        downstream.assert_not_awaited()

    async def test_cross_site_access_stops_before_downstream(self) -> None:
        downstream = AsyncMock()
        with patch("mcp_control_plane.gateway.call_telemetry_tool", downstream):
            await self.assert_denied(
                "CROSS_SITE_ACCESS",
                "read_equipment_status",
                {"equipment_id": "etch-201"},
            )
        downstream.assert_not_awaited()

    async def test_fabricated_tool_is_not_authorized(self) -> None:
        await self.assert_denied("TOOL_NOT_AUTHORIZED", "delete_equipment", {})

    async def test_supervisor_cannot_invoke_hidden_write(self) -> None:
        with self.assertRaises(ControlPlaneError) as caught:
            await invoke_tool(
                self.config,
                "demo-sup-key",
                "create_maintenance_ticket",
                {
                    "equipment_id": "etch-101",
                    "reason": "Inspect alarm",
                    "idempotency_key": "request-1",
                },
            )
        self.assertEqual("TOOL_NOT_AUTHORIZED", caught.exception.code)

    async def test_engineer_write_requires_approval_without_creating_ticket(self) -> None:
        downstream = AsyncMock()
        with patch("mcp_control_plane.gateway.call_maintenance_tool", downstream):
            await self.assert_denied(
                "APPROVAL_REQUIRED",
                "create_maintenance_ticket",
                {
                    "equipment_id": "etch-101",
                    "reason": "Inspect alarm",
                    "idempotency_key": "request-1",
                },
            )
        downstream.assert_not_awaited()

    async def test_downstream_failure_has_stable_reason(self) -> None:
        downstream = AsyncMock(side_effect=RuntimeError("internal detail"))
        with patch("mcp_control_plane.gateway.call_telemetry_tool", downstream):
            await self.assert_denied(
                "DOWNSTREAM_FAILURE",
                "read_equipment_status",
                {"equipment_id": "etch-101"},
            )
        downstream.assert_awaited_once_with(
            "read_equipment_status", {"equipment_id": "etch-101"}
        )
