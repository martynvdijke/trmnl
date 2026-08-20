"""Tests for the Jellyfin Now Playing transform.

Run with: python3 tests/test_jellyfin_transform.py
"""

import importlib.util
import json
import os
import unittest

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "jellyfin-now-playing", "src")
_spec = importlib.util.spec_from_file_location("jellyfin_transform", os.path.join(_DIR, "transform.py"))
transform = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(transform)


def _input(sessions, url="https://jellyfin.example.com", api_key="key"):
    return {
        "data": sessions,
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {"url": url, "api_key": api_key}
            }
        },
    }


SESSION_PLAYING = {
    "UserName": "Martyn",
    "Client": "Jellyfin Web",
    "DeviceName": "Living Room TV",
    "NowPlayingItem": {
        "Id": "ep-1",
        "Name": "The Storm",
        "SeriesName": "The Expanse",
        "Type": "Episode",
        "ParentIndexNumber": 1,
        "IndexNumber": 4,
        "ProductionYear": 2015,
        "SeriesId": "series-1",
        "RunTimeTicks": 27_000_000_000,  # 45 min
    },
    "PlayState": {"PositionTicks": 9_000_000_000, "IsPaused": False},
    "TranscodingInfo": {"VideoCodec": "h264"},
}

SESSION_IDLE = {
    "UserName": "Martyn",
    "Client": "Jellyfin Web",
    "DeviceName": "Phone",
    "NowPlayingItem": None,
}


class TransformTest(unittest.TestCase):
    def test_missing_url(self):
        out = transform.run({"data": [], "trmnl": {"plugin_settings": {"custom_fields_values": {"url": "", "api_key": ""}}}})
        self.assertIn("error", out)

    def test_nothing_playing(self):
        out = transform.run(_input([SESSION_IDLE]))
        self.assertEqual(out["count"], 0)
        self.assertEqual(out["playing"], [])

    def test_playing_reshaped(self):
        out = transform.run(_input([SESSION_PLAYING]))
        self.assertEqual(out["count"], 1)
        p = out["playing"][0]
        self.assertEqual(p["title"], "The Storm")
        self.assertEqual(p["subtitle"], "The Expanse · S01E04")
        self.assertEqual(p["user"], "Martyn")
        self.assertEqual(p["device"], "Living Room TV")
        self.assertTrue(p["transcoding"])
        self.assertEqual(p["runtime_min"], 45)
        self.assertEqual(p["position_min"], 15)
        self.assertEqual(p["progress"], 33)
        self.assertIn("api_key=key", p["poster"])
        self.assertIn("/Items/series-1/Images/Primary", p["poster"])

    def test_skips_idle_sessions(self):
        out = transform.run(_input([SESSION_IDLE, SESSION_PLAYING]))
        self.assertEqual(out["count"], 1)


if __name__ == "__main__":
    unittest.main()
