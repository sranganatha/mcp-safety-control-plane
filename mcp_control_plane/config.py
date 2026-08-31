"""Load and validate deterministic demo fixtures."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when fixture configuration is invalid."""


@dataclass(frozen=True)
class Principal:
    id: str
    role: str
    assigned_site: str


@dataclass(frozen=True)
class Equipment:
    id: str
    site: str
    temperature_c: float
    alarms: tuple[str, ...]


@dataclass(frozen=True)
class DemoConfig:
    principals: dict[str, Principal]
    equipment: dict[str, Equipment]


def _unique_by_id(items: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item["id"]
        if item_id in indexed:
            raise ConfigError(f"duplicate {kind} id: {item_id}")
        indexed[item_id] = item
    return indexed


def parse_config(raw: dict[str, Any]) -> DemoConfig:
    try:
        principal_rows = _unique_by_id(raw["principals"], "principal")
        equipment_rows = _unique_by_id(raw["equipment"], "equipment")

        principals = {
            item_id: Principal(
                id=item_id,
                role=row["role"],
                assigned_site=row["assigned_site"],
            )
            for item_id, row in principal_rows.items()
        }
        equipment = {
            item_id: Equipment(
                id=item_id,
                site=row["site"],
                temperature_c=float(row["temperature_c"]),
                alarms=tuple(row["alarms"]),
            )
            for item_id, row in equipment_rows.items()
        }
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ConfigError):
            raise
        raise ConfigError(f"invalid fixture configuration: {error}") from error

    invalid_roles = sorted({principal.role for principal in principals.values()} - {"engineer", "supervisor"})
    if invalid_roles:
        raise ConfigError(f"unsupported roles: {', '.join(invalid_roles)}")

    return DemoConfig(principals=principals, equipment=equipment)


def load_config(path: str | Path) -> DemoConfig:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigError(f"invalid fixture configuration: {error}") from error
    return parse_config(raw)


def main() -> None:
    config = load_config(sys.argv[1] if len(sys.argv) > 1 else "config/demo.json")
    print(f"loaded {len(config.principals)} principals and {len(config.equipment)} equipment records")


if __name__ == "__main__":
    main()
