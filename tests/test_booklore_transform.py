import importlib.util
import json
import os
import urllib.request
from unittest import mock
import unittest

SPEC = importlib.util.spec_from_file_location(
    "booklore_transform",
    os.path.join(os.path.dirname(__file__), "..", "plugins", "booklore", "src", "transform.py"),
)
transform = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transform)


class _Resp:
    def __init__(self, obj):
        self._o = obj

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        if isinstance(self._o, (dict, list)):
            return json.dumps(self._o).encode()
        return self._o.encode()


def _url_of(url):
    return getattr(url, "full_url", str(url))


def _fake(mapping):
    def _open(url, *a, **k):
        u = _url_of(url)
        for frag, payload in mapping.items():
            if frag in u:
                return _Resp(payload)
        raise AssertionError("unexpected url: %s" % u)
    return _open


def _input(**fields):
    return {"trmnl": {"plugin_settings": {"custom_fields_values": fields}}}


class TransformTest(unittest.TestCase):
    def test_missing_url_returns_error(self):
        out = transform.run(_input())
        self.assertIn("error", out)

    def test_happy_path_counts_and_progress(self):
        size = {"totalElements": 42, "content": []}
        listing = {
            "content": [
                {"title": "Dune", "authors": [{"name": "Frank Herbert"}], "progress": 0.5},
                {"title": "Hyperion", "authors": [{"name": "Dan Simmons"}], "progress": 80},
            ]
        }
        fake = _fake({"size=1": size, "size=5": listing})
        with mock.patch.object(urllib.request, "urlopen", fake):
            out = transform.run(_input(url="https://booklore.local", api_key="tok"))
        self.assertNotIn("error", out)
        self.assertEqual(out["total_books"], 42)
        self.assertEqual(out["reading_count"], 2)
        self.assertEqual(out["reading"][0]["title"], "Dune")
        self.assertEqual(out["reading"][0]["author"], "Frank Herbert")
        self.assertEqual(out["reading"][0]["progress_pct"], 50)
        self.assertEqual(out["reading"][1]["progress_pct"], 80)

    def test_string_authors_and_zero_progress(self):
        listing = {
            "content": [
                {"title": "The Name of the Wind", "authors": "Patrick Rothfuss", "progress": 0},
            ]
        }
        fake = _fake({"size=1": {"totalElements": 7}, "size=5": listing})
        with mock.patch.object(urllib.request, "urlopen", fake):
            out = transform.run(_input(url="https://booklore.local", api_key="tok"))
        self.assertEqual(out["total_books"], 7)
        self.assertEqual(out["reading"][0]["author"], "Patrick Rothfuss")
        self.assertEqual(out["reading"][0]["progress_pct"], 0)


if __name__ == "__main__":
    unittest.main()
