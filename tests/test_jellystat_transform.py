"""Tests for the Jellystat transform.

Run with: python3 tests/test_jellystat_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "jellystat", "src")
_spec = importlib.util.spec_from_file_location("jellystat_transform", os.path.join(_DIR, "transform.py"))
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
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if "auth/login" in url or "/api/login" in url:
        return _Resp({"token": "t"})
    if "/api/summary" in url:
        return _Resp({"total_hours": 120, "total_plays": 300, "total_users": 2})
    if "/api/items/watched" in url:
        return _Resp([{"name": "The Expanse", "plays": 40, "hours": 30}])
    return _Resp({})


def _input(url="https://jellystat.example.com", username="u", password="p"):
    return {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {
                    "url": url,
                    "username": username,
                    "password": password,
                }
            }
        }
    }


class TransformTest(unittest.TestCase):
    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_missing_url(self, *_):
        out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {"url": ""}}}})
        self.assertIn("error", out)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_summary_reshaped(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["hours"], 120)
        self.assertEqual(out["plays"], 300)
        self.assertEqual(out["users"], 2)
        self.assertEqual(len(out["top_shows"]), 1)
        self.assertEqual(out["top_show"]["name"], "The Expanse")

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_login_fallback(self, *_):
        # First login endpoint fails, /api/login fallback succeeds.
        calls = {"n": 0}

        def side(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if url.endswith("/api/auth/login"):
                calls["n"] += 1
                raise OSError("no")
            return _fake_urlopen(req, timeout)

        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertEqual(out["hours"], 120)
        self.assertEqual(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
