"""Tests for the Audiobookshelf transform.

Run with: python3 tests/test_audiobookshelf_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "audiobookshelf", "src")
_spec = importlib.util.spec_from_file_location("audiobookshelf_transform", os.path.join(_DIR, "transform.py"))
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
        "sessions": [
            {
                "id": "s1",
                "displayTitle": "The Hobbit",
                "isActive": True,
                "progress": 0.42,
                "currentTime": 252,
                "duration": 600,
                "libraryItemId": "li-123",
                "mediaMetadata": {"title": "The Hobbit", "author": "Tolkien"},
            }
        ]
    })


def _input(url="http://abs.example.com:13378", api_key="tok"):
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
    def test_current_session(self, *_):
        out = transform.run(_input())
        self.assertTrue(out["has_session"])
        self.assertEqual(out["title"], "The Hobbit")
        self.assertEqual(out["author"], "Tolkien")
        self.assertEqual(out["progress"], 42)
        self.assertIn("/api/items/li-123/cover", out["cover"])

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_no_session(self, *_):
        def side(req, timeout=None):
            return _Resp({"sessions": []})
        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertFalse(out["has_session"])


if __name__ == "__main__":
    unittest.main()
