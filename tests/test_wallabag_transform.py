import importlib.util
import json
import os
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "wallabag_transform",
    os.path.join(HERE, "..", "plugins", "wallabag", "src", "transform.py"),
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


def _fake_urlopen(token_payload, entries_payload):
    def fake(url, data=None, timeout=None):
        u = _url_of(url)
        if "oauth/v2/token" in u:
            return _Resp(token_payload)
        if "entries.json" in u:
            return _Resp(entries_payload)
        return _Resp({})

    return fake


def test_missing_url():
    out = mod.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
    assert "error" in out
    assert "URL" in out["error"]


def test_unread_count():
    inp = {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {
                    "url": "https://wb.example.com",
                    "client_id": "cid",
                    "client_secret": "csec",
                    "username": "user",
                    "password": "pw",
                }
            }
        }
    }
    with mock.patch(
        "urllib.request.urlopen",
        _fake_urlopen({"access_token": "tok"}, {"total": 42, "_embedded": {"items": []}}),
    ):
        out = mod.run(inp)
    assert out["unread"] == 42


def test_auth_failure():
    with mock.patch("urllib.request.urlopen", lambda *a, **k: _Resp({})):
        out = mod.run(
            {
                "trmnl": {
                    "plugin_settings": {
                        "custom_fields_values": {
                            "url": "https://wb.example.com",
                            "client_id": "c",
                            "client_secret": "s",
                            "username": "u",
                            "password": "p",
                        }
                    }
                }
            }
        )
    assert "error" in out
