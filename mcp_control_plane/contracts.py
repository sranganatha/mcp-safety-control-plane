"""Structured results shared by gateway and downstream MCP servers."""

from typing import TypedDict


class EquipmentStatus(TypedDict):
    equipment_id: str
    site: str
    temperature_c: float
    status: str


class AlarmList(TypedDict):
    equipment_id: str
    alarms: list[str]


class MaintenanceTicket(TypedDict):
    ticket_id: str
    equipment_id: str
    reason: str
    status: str
