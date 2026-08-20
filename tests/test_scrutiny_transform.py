"""Tests for the Scrutiny transform.

Run with: python3 tests/test_scrutiny_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "scrutiny", "src")
_spec = importlib.util.spec_from_file_location("scrutiny_transform", os.path.join(_DIR, "transform.py"))
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


def _fake_urlopen(req, timeout=None):
    return _Resp([
        {
            "device": {
                "name": "sda",
                "model": "WD Red",
                "status": "PASS",
                "temp": 38,
                "power_on_hours": 12000,
            }
        },
        {
            "device": {
                "name": "sdb",
                "model": "Seagate",
                "status": "WARN",
                "temp": 55,
                "power_on_hours": 30000,
            }
        },
        {
            "device": {
                "name": "sdc",
                "model": "Toshiba",
                "status": "FAIL",
                "temp": 60,
                "power_on_hours": 40000,
            }
        },
    ])


def _input(url="http://scrutiny.example.com:8080"):
    return {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {"url": url}
            }
        }
    }


class TransformTest(unittest.TestCase):
    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_missing_url(self, *_):
        out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {"url": ""}}}})
        self.assertIn("error", out)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_health_summary(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["total"], 3)
        self.assertEqual(out["failed_count"], 1)
        self.assertEqual(out["warned_count"], 1)
        self.assertEqual(out["healthy_count"], 1)
        self.assertFalse(out["all_good"])
        self.assertEqual(out["failed"][0], "sdc")
        self.assertEqual(len(out["devices"]), 3)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_unreachable(self, *_):
        def side(req, timeout=None):
            raise OSError("no")
        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
