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
            "principals": [
                {
                    "id": "eng-a",
                    "api_key": "demo-eng-key",
                    "role": "admin",
                    "assigned_site": "site-a",
                }
            ],
            "equipment": [],
        }

        with self.assertRaisesRegex(ConfigError, "unsupported roles: admin"):
            parse_config(invalid)

    def test_duplicate_api_key_is_rejected_without_echoing_key(self) -> None:
        invalid = {
            "principals": [
                {
                    "id": "eng-a",
                    "api_key": "shared-secret",
                    "role": "engineer",
                    "assigned_site": "site-a",
                },
                {
                    "id": "sup-a",
                    "api_key": "shared-secret",
                    "role": "supervisor",
                    "assigned_site": "site-a",
                },
            ],
            "equipment": [],
        }

        with self.assertRaises(ConfigError) as caught:
            parse_config(invalid)

        self.assertEqual("duplicate principal api_key", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
