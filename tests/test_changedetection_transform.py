"""Tests for the Changedetection transform.

Run with: python3 tests/test_changedetection_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "changedetection", "src")
_spec = importlib.util.spec_from_file_location("changedetection_transform", os.path.join(_DIR, "transform.py"))
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


_WATCHES = {
    "uuid-1": {
        "title": "Example Page",
        "url": "https://example.com",
        "last_changed": 1700000003,
        "last_checked": 1700000003,
        "last_error": False,
        "paused": False,
        "viewed": False,
    },
    "uuid-2": {
        "title": "",
        "url": "https://example.org",
        "last_changed": 1700000001,
        "last_checked": 1700000002,
        "last_error": "404",
        "paused": True,
        "viewed": True,
    },
    "uuid-3": {
        "title": "Third Page",
        "url": "https://example.net",
        "last_changed": 1700000002,
        "last_checked": 1700000003,
        "last_error": "",
        "paused": False,
        "viewed": False,
    },
}


def _fake_urlopen(req, timeout=None):
    return _Resp(_WATCHES)


def _input(url="https://changedetection.example.com", api_key="test-key"):
    return {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {"url": url, "api_key": api_key}
            }
        }
    }


class TransformTest(unittest.TestCase):
    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_missing_url(self, *_):
        out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {"url": ""}}}})
        self.assertIn("error", out)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_counts(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["total"], 3)
        self.assertEqual(out["unviewed"], 2)
        self.assertEqual(out["paused"], 1)
        self.assertEqual(out["errored"], 1)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_recent_sorted(self, *_):
        out = transform.run(_input())
        recent = out["recent"]
        self.assertEqual(len(recent), 3)
        # Sorted descending by last_changed: uuid-1 (3), uuid-3 (2), uuid-2 (1)
        self.assertEqual(recent[0]["title"], "Example Page")
        self.assertEqual(recent[0]["last_changed"], 1700000003)
        self.assertEqual(recent[1]["title"], "Third Page")
        self.assertEqual(recent[2]["title"], "https://example.org")  # fallback to url when title empty
        self.assertEqual(recent[2]["last_changed"], 1700000001)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_recent_max_five(self, *_):
        watches = {}
        for i in range(7):
            watches[f"uuid-{i}"] = {
                "title": f"Page {i}",
                "url": f"https://example.com/{i}",
                "last_changed": 1700000000 + i,
                "last_error": False,
                "paused": False,
                "viewed": False,
            }

        def side(req, timeout=None):
            return _Resp(watches)

        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertEqual(len(out["recent"]), 5)
        # Most recent first
        self.assertEqual(out["recent"][0]["title"], "Page 6")


if __name__ == "__main__":
    unittest.main()
