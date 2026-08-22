"""Tests for the Paperless-ngx transform.

Run with: python3 tests/test_paperless_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "paperless-ngx", "src")
_spec = importlib.util.spec_from_file_location("paperless_transform", os.path.join(_DIR, "transform.py"))
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


def _input(url="https://paperless.example.com", api_token="test-token"):
    return {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {"url": url, "api_token": api_token}
            }
        }
    }


def _fake_urlopen(req, timeout=None):
    url = getattr(req, 'full_url', str(req))
    if "/api/statistics/" in url:
        return _Resp({"documents_total": 42, "documents_inbox": 5})
    if "/api/documents/" in url:
        return _Resp({
            "results": [
                {"title": "Doc A", "created": "2026-01-15T10:30:00Z"},
                {"title": "Doc B", "created": "2026-01-14T09:00:00Z"},
            ]
        })
    return _Resp({})


class TransformTest(unittest.TestCase):
    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_missing_url(self, *_):
        out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {"url": ""}}}})
        self.assertIn("error", out)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_statistics_reshaped(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["total_documents"], 42)
        self.assertEqual(out["inbox_count"], 5)
        self.assertEqual(len(out["recent"]), 2)
        self.assertEqual(out["recent"][0]["title"], "Doc A")
        self.assertEqual(out["recent"][0]["created"], "2026-01-15")
        self.assertEqual(out["recent"][1]["title"], "Doc B")
        self.assertEqual(out["recent"][1]["created"], "2026-01-14")

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_documents_fetch_failure_degrades(self, *_):
        def side(req, timeout=None):
            url = getattr(req, 'full_url', str(req))
            if "/api/statistics/" in url:
                return _Resp({"documents_total": 10, "documents_inbox": 2})
            if "/api/documents/" in url:
                raise Exception("network error")
            return _Resp({})

        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertEqual(out["total_documents"], 10)
        self.assertEqual(out["inbox_count"], 2)
        self.assertEqual(out["recent"], [])


if __name__ == "__main__":
    unittest.main()
