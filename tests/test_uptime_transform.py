"""Tests for the Uptime Kuma transform.

Run with: python3 tests/test_uptime_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "uptime-kuma", "src")
_spec = importlib.util.spec_from_file_location("uptime_transform", os.path.join(_DIR, "transform.py"))
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
    return _Resp({
        "monitors": [
            {"name": "Website", "status": "up", "online": True},
            {"name": "API", "status": "down", "online": False, "message": "502"},
        ]
    })


def _input(url="https://uptime.example.com", slug="my-page"):
    return {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {"url": url, "slug": slug}
            }
        }
    }


class TransformTest(unittest.TestCase):
    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_missing_url(self, *_):
        out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {"url": ""}}}})
        self.assertIn("error", out)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_status_reshaped(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["total"], 2)
        self.assertEqual(out["up"], 1)
        self.assertEqual(out["down"], 1)
        self.assertEqual(out["pending"], 0)
        self.assertEqual(len(out["down_monitors"]), 1)
        self.assertEqual(out["down_monitors"][0]["name"], "API")
        self.assertEqual(out["down_monitors"][0]["message"], "502")
        self.assertFalse(out["all_up"])

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_all_up(self, *_):
        def side(req, timeout=None):
            return _Resp({"monitors": [{"name": "Website", "status": "up", "online": True}]})

        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertEqual(out["down"], 0)
        self.assertTrue(out["all_up"])


if __name__ == "__main__":
    unittest.main()
