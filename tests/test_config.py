import unittest

from mcp_control_plane.config import ConfigError, load_config, parse_config


class ConfigTests(unittest.TestCase):
    def test_demo_config_loads(self) -> None:
        config = load_config("config/demo.json")

        self.assertEqual(config.principals["eng-a"].assigned_site, "site-a")
        self.assertEqual(config.equipment["etch-101"].alarms, ("TEMP_HIGH",))

    def test_duplicate_id_is_rejected(self) -> None:
        invalid = {
            "principals": [
                {"id": "eng-a", "role": "engineer", "assigned_site": "site-a"},
                {"id": "eng-a", "role": "supervisor", "assigned_site": "site-a"},
            ],
            "equipment": [],
        }

        with self.assertRaisesRegex(ConfigError, "duplicate principal id"):
            parse_config(invalid)

    def test_unknown_role_is_rejected(self) -> None:
        invalid = {
            "principals": [{"id": "eng-a", "role": "admin", "assigned_site": "site-a"}],
            "equipment": [],
        }

        with self.assertRaisesRegex(ConfigError, "unsupported roles: admin"):
            parse_config(invalid)


if __name__ == "__main__":
    unittest.main()
