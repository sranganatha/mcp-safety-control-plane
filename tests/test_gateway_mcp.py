import unittest
from unittest.mock import AsyncMock, patch

from mcp import Client

from mcp_control_plane.gateway_server import API_KEY_META, mcp


class GovernedGatewayDiscoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_tool_discovery_is_filtered_per_mcp_request(self) -> None:
        async with Client(mcp, cache=None) as client:
            engineer = await client.list_tools(
                meta={API_KEY_META: "demo-eng-key"}
            )
        async with Client(mcp, cache=None) as client:
            supervisor = await client.list_tools(
                meta={API_KEY_META: "demo-sup-key"}
            )

        self.assertEqual(
            [
                "create_maintenance_ticket",
                "list_active_alarms",
                "read_equipment_status",
            ],
            sorted(tool.name for tool in engineer.tools),
        )
        self.assertEqual(
            ["list_active_alarms", "read_equipment_status"],
            sorted(tool.name for tool in supervisor.tools),
        )

    async def test_denied_mcp_call_does_not_cross_downstream_boundary(self) -> None:
        downstream = AsyncMock(
            return_value={
                "equipment_id": "etch-101",
                "site": "site-a",
                "temperature_c": 84.5,
                "status": "alarm",
            }
        )
        with patch("mcp_control_plane.gateway.call_telemetry_tool", downstream):
            async with Client(mcp, cache=None) as client:
                await client.list_tools(meta={API_KEY_META: "demo-eng-key"})
                allowed = await client.call_tool(
                    "read_equipment_status",
                    {"equipment_id": "etch-101"},
                    meta={API_KEY_META: "demo-eng-key"},
                )
                downstream.assert_awaited_once()
                downstream.reset_mock()

                denial = await client.call_tool(
                    "read_equipment_status",
                    {"equipment_id": "etch-201"},
                    meta={API_KEY_META: "demo-eng-key"},
                )

        self.assertFalse(allowed.is_error)
        self.assertTrue(denial.is_error)
        self.assertIn("CROSS_SITE_ACCESS", denial.content[0].text)
        downstream.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
