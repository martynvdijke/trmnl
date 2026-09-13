import importlib.util
import json
import os
import urllib.request as urllib_request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "transform.py")

spec = importlib.util.spec_from_file_location("jellystat_transform", SRC)
transform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transform)


class FakeResponse:
    def __init__(self, body, status=200):
        self._body = body
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeUrlopen:
    def __call__(self, request, *args, **kwargs):
        url = getattr(request, "full_url", str(request))
        if "/auth/login" in url:
            return FakeResponse(json.dumps({"token": "tok"}).encode())
        if "getViewsOverTime" in url:
            return FakeResponse(
                json.dumps(
                    {"libraries": [], "stats": [{"Key": "Sep 01", "Movies": {"count": 3, "duration": 120}}]}
                ).encode()
            )
        if "getAllUserActivity" in url:
            return FakeResponse(
                json.dumps([{"UserName": "alice"}, {"UserName": "bob"}, {"UserName": "alice"}]).encode()
            )
        if "getMostViewedByType" in url:
            return FakeResponse(
                json.dumps([{"Plays": 5, "total_playback_duration": 7200, "Name": "Some Show", "Id": "1"}]).encode()
            )
        return FakeResponse(b"{}")


def test_stats_endpoints():
    original = urllib_request.urlopen
    urllib_request.urlopen = FakeUrlopen()
    try:
        out = transform.run(
            {"trmnl": {"plugin_settings": {"custom_fields_values": {"url": "https://jellystat.example.com", "username": "u", "password": "p"}}}}
        )
    finally:
        urllib_request.urlopen = original

    assert "error" not in out, out
    assert out["plays"] == 3
    assert out["hours"] == 2.0  # 120 minutes
    assert out["users"] == 2
    assert out["top_shows"][0]["name"] == "Some Show"
    assert out["top_shows"][0]["plays"] == 5
    assert out["top_shows"][0]["hours"] == 2.0  # 7200 seconds
    assert out["top_show"]["name"] == "Some Show"
    print("OK", out)


def test_login_failure_errors():
    class Deny(FakeUrlopen):
        def __call__(self, request, *args, **kwargs):
            return FakeResponse(b"{}")

    original = urllib_request.urlopen
    urllib_request.urlopen = Deny()
    try:
        out = transform.run(
            {"trmnl": {"plugin_settings": {"custom_fields_values": {"url": "https://jellystat.example.com", "username": "u", "password": "p"}}}}
        )
    finally:
        urllib_request.urlopen = original
    assert "error" in out


def test_missing_url_errors():
    out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
    assert "error" in out


if __name__ == "__main__":
    test_stats_endpoints()
    test_login_failure_errors()
    test_missing_url_errors()
    print("ALL TESTS PASSED")
