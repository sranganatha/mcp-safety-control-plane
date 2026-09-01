import os
import unittest
from contextlib import closing
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from mcp import Client

from mcp_control_plane.config import load_config
from mcp_control_plane.gateway import approve_request
from mcp_control_plane.gateway_server import API_KEY_META, mcp
from mcp_control_plane.storage import connect_database


class GovernedGatewayDiscoveryTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_and_invalid_identity_cannot_discover_tools(self) -> None:
        identities = (
            (None, "IDENTITY_REQUIRED"),
            ({API_KEY_META: "invalid"}, "IDENTITY_INVALID"),
        )
        for meta, code in identities:
            with self.subTest(code=code), self.assertRaises(ExceptionGroup) as caught:
                async with Client(mcp, cache=None) as client:
                    await client.list_tools(meta=meta)
            nested_errors = caught.exception.subgroup(lambda error: code in str(error))
            self.assertIsNotNone(nested_errors)

    async def test_missing_and_invalid_identity_cannot_invoke_tools(self) -> None:
        identities = (
            (None, "IDENTITY_REQUIRED"),
            ({API_KEY_META: "invalid"}, "IDENTITY_INVALID"),
        )
        downstream = AsyncMock()
        with patch("mcp_control_plane.gateway.call_telemetry_tool", downstream):
            for meta, code in identities:
                with self.subTest(code=code):
                    async with Client(mcp, cache=None) as client:
                        denial = await client.call_tool(
                            "read_equipment_status",
                            {"equipment_id": "etch-101"},
                            meta=meta,
                        )
                    self.assertTrue(denial.is_error)
                    self.assertIn(code, denial.content[0].text)
        downstream.assert_not_awaited()

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

    async def test_supervisor_cannot_directly_invoke_hidden_write(self) -> None:
        downstream = AsyncMock()
        with patch("mcp_control_plane.gateway.call_maintenance_tool", downstream):
            async with Client(mcp, cache=None) as client:
                denial = await client.call_tool(
                    "create_maintenance_ticket",
                    {
                        "equipment_id": "etch-101",
                        "reason": "Inspect alarm",
                        "idempotency_key": "supervisor-request",
                    },
                    meta={API_KEY_META: "demo-sup-key"},
                )

        self.assertTrue(denial.is_error)
        self.assertIn("TOOL_NOT_AUTHORIZED", denial.content[0].text)
        downstream.assert_not_awaited()

    async def test_modified_arguments_cannot_use_existing_approval(self) -> None:
        config = load_config("config/demo.json")
        arguments = {
            "equipment_id": "etch-101",
            "reason": "Inspect alarm",
            "idempotency_key": "modified-request",
        }
        with TemporaryDirectory() as temporary_directory:
            database_path = f"{temporary_directory}/gateway.db"
            with closing(connect_database(database_path)) as database:
                approval_id = approve_request(
                    database,
                    config,
                    "demo-sup-key",
                    "eng-a",
                    "create_maintenance_ticket",
                    arguments,
                )
            with patch.dict(os.environ, {"MCP_DB_PATH": database_path}):
                async with Client(mcp, cache=None) as client:
                    denial = await client.call_tool(
                        "create_maintenance_ticket",
                        {
                            **arguments,
                            "reason": "Different reason",
                            "approval_id": approval_id,
                        },
                        meta={API_KEY_META: "demo-eng-key"},
                    )

            with closing(connect_database(database_path)) as database:
                used_at = database.execute(
                    "SELECT used_at FROM approvals WHERE approval_id = ?",
                    (approval_id,),
                ).fetchone()[0]
                ticket_count = database.execute(
                    "SELECT COUNT(*) FROM tickets"
                ).fetchone()[0]

        self.assertTrue(denial.is_error)
        self.assertIn("APPROVAL_MISMATCH", denial.content[0].text)
        self.assertIsNone(used_at)
        self.assertEqual(0, ticket_count)

    async def test_approved_write_succeeds_once_through_gateway(self) -> None:
        config = load_config("config/demo.json")
        arguments = {
            "equipment_id": "etch-101",
            "reason": "Inspect alarm",
            "idempotency_key": "approved-request",
        }
        with TemporaryDirectory() as temporary_directory:
            database_path = f"{temporary_directory}/gateway.db"
            with closing(connect_database(database_path)) as database:
                approval_id = approve_request(
                    database,
                    config,
                    "demo-sup-key",
                    "eng-a",
                    "create_maintenance_ticket",
                    arguments,
                )
            request = {**arguments, "approval_id": approval_id}
            with patch.dict(os.environ, {"MCP_DB_PATH": database_path}):
                async with Client(mcp, cache=None) as client:
                    await client.list_tools(meta={API_KEY_META: "demo-eng-key"})
                    success = await client.call_tool(
                        "create_maintenance_ticket",
                        request,
                        meta={API_KEY_META: "demo-eng-key"},
                    )
                    replay = await client.call_tool(
                        "create_maintenance_ticket",
                        request,
                        meta={API_KEY_META: "demo-eng-key"},
                    )

        self.assertFalse(success.is_error)
        self.assertEqual("maint-001", success.structured_content["ticket_id"])
        self.assertTrue(replay.is_error)
        self.assertIn("APPROVAL_ALREADY_USED", replay.content[0].text)


if __name__ == "__main__":
    unittest.main()
