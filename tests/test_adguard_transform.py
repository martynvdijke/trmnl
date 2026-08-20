"""Tests for the AdGuard Home transform.

Run with: python3 tests/test_adguard_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "adguard-home", "src")
_spec = importlib.util.spec_from_file_location("adguard_transform", os.path.join(_DIR, "transform.py"))
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
    if url.endswith("/control/stats"):
        return _Resp({"num_queries": 10000, "num_blocked_filtering": 1500})
    if url.endswith("/control/top_blocked_domains"):
        return _Resp([
            ["ads.example.com", 500],
            ["tracker.net", 300],
            ["spam.com", 100],
        ])
    return _Resp({})


def _input(url="https://adguard.example.com", username="u", password="p"):
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
    def test_stats_reshaped(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["queries"], 10000)
        self.assertEqual(out["blocked"], 1500)
        self.assertEqual(out["blocked_pct"], 15)
        self.assertEqual(len(out["top_blocked"]), 3)
        self.assertEqual(out["top_blocked_domain"], "ads.example.com")
        self.assertEqual(out["top_blocked"][1]["domain"], "tracker.net")

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_dict_blocked_entries(self, *_):
        def side(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if url.endswith("/control/top_blocked_domains"):
                return _Resp([{"domain": "x.com", "count": 9}])
            return _fake_urlopen(req, timeout)

        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertEqual(out["top_blocked"][0]["domain"], "x.com")
        self.assertEqual(out["top_blocked"][0]["count"], 9)


if __name__ == "__main__":
    unittest.main()
