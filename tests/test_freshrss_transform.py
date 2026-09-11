import importlib.util
import json
import os
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "freshrss_transform",
    os.path.join(HERE, "..", "plugins", "freshrss", "src", "transform.py"),
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


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


def _fake_urlopen(login_text, unread_payload):
    def fake(url, data=None, timeout=None):
        u = _url_of(url)
        if "ClientLogin" in u:
            return _Resp(login_text)
        if "unread-count" in u:
            return _Resp(unread_payload)
        return _Resp({})

    return fake


class TransformTest(unittest.TestCase):
    def test_missing_url(self):
        out = mod.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
        self.assertIn("error", out)
        self.assertIn("URL", out["error"])

    def test_unread_count(self):
        inp = {
            "trmnl": {
                "plugin_settings": {
                    "custom_fields_values": {
                        "url": "https://fr.example.com",
                        "username": "user@example.com",
                        "password": "pw",
                    }
                }
            }
        }
        with mock.patch(
            "urllib.request.urlopen",
            _fake_urlopen(
                "SID=abc\nAuth=def\n",
                {"unreadcounts": [{"count": 5}, {"count": 3}]},
            ),
        ):
            out = mod.run(inp)
        self.assertEqual(out["unread"], 8)
        self.assertEqual(out["feeds"], 2)

    def test_login_failure(self):
        with mock.patch("urllib.request.urlopen", lambda *a, **k: _Resp("")):
            out = mod.run(
                {
                    "trmnl": {
                        "plugin_settings": {
                            "custom_fields_values": {
                                "url": "https://fr.example.com",
                                "username": "u",
                                "password": "p",
                            }
                        }
                    }
                }
            )
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
