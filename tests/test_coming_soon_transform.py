"""Tests for the Coming Soon transform.

Run with: python3 tests/test_coming_soon_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "coming-soon", "src")
_spec = importlib.util.spec_from_file_location("coming_soon_transform", os.path.join(_DIR, "transform.py"))
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


def _future_iso(days=1):
    import datetime
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fake_urlopen(req, timeout=None):
    return _Resp([
        {
            "id": 1,
            "series": {"id": 1, "title": "My Show"},
            "title": "Pilot",
            "airDateUtc": _future_iso(2),
        },
        {
            "id": 2,
            "title": "Big Movie",
            "year": 2099,
            "airDateUtc": _future_iso(5),
            "releaseDate": _future_iso(5),
        },
    ])


def _input(url="https://sonarr.example.com", api_key="k"):
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
    def test_calendar_reshaped(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["movies"], 1)
        self.assertEqual(out["episodes"], 1)
        self.assertEqual(out["window_days"], 14)
        kinds = {i["kind"] for i in out["items"]}
        self.assertEqual(kinds, {"Movie", "Episode"})
        for it in out["items"]:
            self.assertIn("MediaCover", it["poster"])
        # Sorted by air date: episode (day 2) before movie (day 5)
        self.assertEqual(out["items"][0]["kind"], "Episode")

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_skips_past(self, *_):
        def side(req, timeout=None):
            return _Resp([
                {"id": 9, "title": "Old", "year": 2000, "airDateUtc": "2000-01-01T00:00:00Z"},
                {
                    "id": 2,
                    "title": "Big Movie",
                    "year": 2099,
                    "airDateUtc": _future_iso(5),
                },
            ])

        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["items"][0]["title"], "Big Movie")


if __name__ == "__main__":
    unittest.main()
