"""Tests for the Backrest transform.

Run with: python3 tests/test_backrest_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "backrest", "src")
_spec = importlib.util.spec_from_file_location("backrest_transform", os.path.join(_DIR, "transform.py"))
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
    if "GetConfig" in url:
        return _Resp({"plans": [{"id": "plan-main"}, {"id": "plan-media"}]})
    if "GetOperations" in url:
        return _Resp({"operations": [
            {"id": "op1", "plan_id": "plan-main", "operation_backup": {},
             "unix_time_start_ms": 1700000000000, "status": "STATUS_SUCCESS"},
            {"id": "op2", "plan_id": "plan-media", "operation_backup": {},
             "unix_time_start_ms": 1699000000000, "status": "STATUS_SUCCESS"},
        ]})
    return _Resp({})


def _input(url="http://backrest.example.com:9898"):
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
    def test_last_backup(self, *_):
        out = transform.run(_input())
        self.assertEqual(out["plan_count"], 2)
        self.assertTrue(out["has_backup"])
        self.assertEqual(out["last_status"], "STATUS_SUCCESS")
        self.assertIn("ago", out["last_backup_ago"])

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_unreachable(self, *_):
        def side(req, timeout=None):
            raise OSError("no")
        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
