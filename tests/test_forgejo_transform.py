"""Tests for the Forgejo transform.

Run with: python3 tests/test_forgejo_transform.py
"""

import importlib.util
import json
import os
import unittest
from unittest.mock import patch

_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins", "forgejo", "src")
_spec = importlib.util.spec_from_file_location("forgejo_transform", os.path.join(_DIR, "transform.py"))
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
    if "type=pr" in url:
        return _Resp([
            {"title": "Fix bug", "repository": {"full_name": "me/app"}},
            {"title": "Add feature", "repository": {"full_name": "me/lib"}},
        ])
    if "type=issues" in url:
        return _Resp([{"title": "Docs"}, {"title": "Typo"}, {"title": "Enhance"}])
    if "/user/repos" in url:
        return _Resp([{"full_name": "me/app"}])
    if "/actions/runs" in url:
        return _Resp([
            {"status": "running", "conclusion": ""},
            {"status": "success", "conclusion": "success"},
        ])
    return _Resp({})


def _input(url="https://forgejo.example.com", api_key="tok"):
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
        self.assertEqual(out["open_prs"], 2)
        self.assertEqual(out["open_issues"], 3)
        self.assertEqual(out["ci_running"], 1)
        self.assertEqual(out["last_ci"], "success")
        self.assertEqual(len(out["prs"]), 2)

    @patch("urllib.request.urlopen", _fake_urlopen)
    def test_unreachable(self, *_):
        def side(req, timeout=None):
            if "type=pr" in (req.full_url if hasattr(req, "full_url") else str(req)):
                raise OSError("no")
            return _fake_urlopen(req, timeout)
        with patch("urllib.request.urlopen", side_effect=side):
            out = transform.run(_input())
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
