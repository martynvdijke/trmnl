import importlib.util
import json
import os
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "npm_transform",
    os.path.join(HERE, "..", "plugins", "nginx-proxy-manager", "src", "transform.py"),
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
        return json.dumps(self._o).encode()


def _url_of(url):
    return getattr(url, "full_url", str(url))


def _fake_urlopen(login_payload, certs_payload):
    def fake(url, data=None, timeout=None):
        u = _url_of(url)
        if "tokens" in u:
            return _Resp(login_payload)
        if "certificates" in u:
            return _Resp(certs_payload)
        return _Resp({})

    return fake


def test_missing_url():
    out = mod.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
    assert "error" in out
    assert "URL" in out["error"]


def test_certs_and_expiry():
    inp = {
        "trmnl": {
            "plugin_settings": {
                "custom_fields_values": {
                    "url": "https://npm.example.com",
                    "username": "admin@example.com",
                    "password": "pw",
                }
            }
        }
    }
    certs = [
        {"domain_names": ["far.example.com"], "expiresOn": "2099-01-01T00:00:00.000Z"},
        {"domain_names": ["soon.example.com"], "expiresOn": "2026-08-25T00:00:00.000Z"},
    ]
    with mock.patch(
        "urllib.request.urlopen",
        _fake_urlopen({"token": "abc"}, certs),
    ):
        out = mod.run(inp)
    assert out["count"] == 2
    assert out["expiring_soon_count"] == 1
    # sorted soonest first
    assert out["certs"][0]["domain"] == "soon.example.com"
    assert isinstance(out["certs"][0]["days_left"], int)
    assert out["certs"][0]["days_left"] <= 30
    assert isinstance(out["certs"][1]["days_left"], int)


def test_login_failure():
    with mock.patch("urllib.request.urlopen", lambda *a, **k: _Resp({})):
        out = mod.run(
            {
                "trmnl": {
                    "plugin_settings": {
                        "custom_fields_values": {
                            "url": "https://npm.example.com",
                            "username": "a",
                            "password": "b",
                        }
                    }
                }
            }
        )
    assert "error" in out
