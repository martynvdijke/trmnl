"""Tests for the Home Assistant transform.

Run with: python3 tests/test_home_assistant_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "home-assistant", "src")
_spec = importlib.util.spec_from_file_location("ha_transform", os.path.join(_DIR, "transform.py"))
transform = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transform)


class _Resp:
    def __init__(self, payload):
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._data


_FIXTURE = [
    {"entity_id": "light.living_room", "state": "on", "attributes": {"friendly_name": "Living Room", "unit_of_measurement": ""}},
    {"entity_id": "light.bedroom", "state": "off", "attributes": {"friendly_name": "Bedroom"}},
    {"entity_id": "switch.kitchen", "state": "on", "attributes": {"friendly_name": "Kitchen Switch"}},
    {"entity_id": "sensor.temperature", "state": "22.5", "attributes": {"friendly_name": "Temperature", "unit_of_measurement": "°C"}},
    {"entity_id": "binary_sensor.motion", "state": "off", "attributes": {"friendly_name": "Motion"}},
    {"entity_id": "climate.thermostat", "state": "heat", "attributes": {"friendly_name": "Thermostat"}},
    {"entity_id": "media_player.tv", "state": "playing", "attributes": {"friendly_name": "TV"}},
]


def _fake_urlopen(req, timeout=None):
    return _Resp(_FIXTURE)


def _input(url="https://ha.example.com", token="tok", entities=""):
    return {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {"url": url, "token": token, "entities": entities}
            }
        }
    }


class TransformTest(unittest.TestCase):
    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_missing_url(self, *_):
        out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {"url": ""}}}})
        self.assertIn("error", out)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_entities_mode_filters_orders(self, *_):
        out = transform.run(_input(entities="sensor.temperature, light.living_room, not.found"))
        self.assertEqual(out["mode"], "entities")
        self.assertEqual(len(out["items"]), 2)
        # preserve requested order
        self.assertEqual(out["items"][0]["name"], "Temperature")
        self.assertEqual(out["items"][0]["state"], "22.5")
        self.assertEqual(out["items"][0]["unit"], "°C")
        self.assertEqual(out["items"][1]["name"], "Living Room")
        self.assertEqual(out["items"][1]["state"], "on")

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_summary_mode_counts(self, *_):
        out = transform.run(_input(entities=""))
        self.assertEqual(out["mode"], "summary")
        self.assertEqual(out["total"], 7)
        self.assertEqual(out["counts"]["light"], 2)
        self.assertEqual(out["counts"]["switch"], 1)
        self.assertEqual(out["counts"]["binary_sensor"], 1)
        self.assertEqual(out["counts"]["sensor"], 1)
        self.assertEqual(out["counts"]["climate"], 1)
        self.assertEqual(out["counts"]["media_player"], 1)
        self.assertEqual(out["lights_on"], 1)


if __name__ == "__main__":
    unittest.main()
