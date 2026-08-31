import os
import unittest
from contextlib import closing
from tempfile import TemporaryDirectory
from unittest.mock import patch

from mcp import Client

from mcp_control_plane.maintenance_server import mcp as maintenance_mcp
from mcp_control_plane.storage import connect_database
from mcp_control_plane.telemetry_server import mcp as telemetry_mcp


class TelemetryToolsTest(unittest.IsolatedAsyncioTestCase):
    async def test_tools_are_callable_over_mcp(self):
        async with Client(telemetry_mcp, raise_exceptions=True) as client:
            tools = (await client.list_tools()).tools
            self.assertEqual(
                ["list_active_alarms", "read_equipment_status"],
                sorted(tool.name for tool in tools),
            )

            status = await client.call_tool(
                "read_equipment_status", {"equipment_id": "etch-101"}
            )
            alarms = await client.call_tool(
                "list_active_alarms", {"equipment_id": "etch-101"}
            )

        self.assertFalse(status.is_error)
        self.assertEqual("alarm", status.structured_content["status"])
        self.assertEqual(["TEMP_HIGH"], alarms.structured_content["alarms"])

    async def test_unknown_equipment_is_a_tool_error(self):
        async with Client(telemetry_mcp, raise_exceptions=True) as client:
            result = await client.call_tool(
                "read_equipment_status", {"equipment_id": "missing"}
            )

        self.assertTrue(result.is_error)
        self.assertIn("unknown equipment: missing", result.content[0].text)


class MaintenanceToolsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.environment = patch.dict(
            os.environ,
            {"MCP_DB_PATH": f"{self.temporary_directory.name}/test.db"},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary_directory.cleanup()

    async def test_ticket_creation_is_idempotent_over_mcp(self):
        arguments = {
            "equipment_id": "etch-101",
            "reason": "Inspect high temperature alarm",
            "idempotency_key": "demo-request-1",
        }
        async with Client(maintenance_mcp, raise_exceptions=True) as client:
            tools = (await client.list_tools()).tools
            first = await client.call_tool("create_maintenance_ticket", arguments)
            replay = await client.call_tool("create_maintenance_ticket", arguments)

        self.assertEqual(["create_maintenance_ticket"], [tool.name for tool in tools])
        self.assertEqual("maint-001", first.structured_content["ticket_id"])
        self.assertEqual(first.structured_content, replay.structured_content)
        with closing(connect_database()) as database:
            self.assertEqual(1, database.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])

    async def test_idempotency_key_cannot_change_request(self):
        async with Client(maintenance_mcp, raise_exceptions=True) as client:
            await client.call_tool(
                "create_maintenance_ticket",
                {
                    "equipment_id": "etch-101",
                    "reason": "First reason",
                    "idempotency_key": "same-key",
                },
            )
            result = await client.call_tool(
                "create_maintenance_ticket",
                {
                    "equipment_id": "etch-101",
                    "reason": "Changed reason",
                    "idempotency_key": "same-key",
                },
            )

        self.assertTrue(result.is_error)
        self.assertIn("already used", result.content[0].text)
