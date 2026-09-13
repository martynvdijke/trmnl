import importlib.util
import json
import os
import time
import urllib.request as urllib_request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "transform.py")

spec = importlib.util.spec_from_file_location("backrest_transform", SRC)
transform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transform)


NOW_MS = int(time.time() * 1000)
RECENT_MS = NOW_MS - 3600 * 1000

CONFIG = {"plans": [{"id": "daily"}, {"id": "weekly"}]}
OPERATIONS = {
    "operations": [
        {"status": "STATUS_SUCCESS", "unix_time_start_ms": RECENT_MS, "operation_backup": {}},
        {"status": "STATUS_SUCCESS", "unix_time_start_ms": NOW_MS - 10 * 24 * 3600 * 1000, "operation_backup": {}},
        {"status": "STATUS_SUCCESS", "unix_time_start_ms": RECENT_MS, "operation_index_snapshot": {}},
    ]
}


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
        if "GetConfig" in url:
            return FakeResponse(json.dumps(CONFIG).encode())
        if "GetOperations" in url:
            return FakeResponse(json.dumps(OPERATIONS).encode())
        return FakeResponse(b"{}")


def test_rpc_and_backup_selection():
    original = urllib_request.urlopen
    urllib_request.urlopen = FakeUrlopen()
    try:
        out = transform.run(
            {"trmnl": {"plugin_settings": {"custom_fields_values": {"url": "http://backrest:9898", "username": "u", "password": "p"}}}}
        )
    finally:
        urllib_request.urlopen = original

    assert "error" not in out, out
    assert out["plan_count"] == 2
    assert out["plan_names"] == ["daily", "weekly"]
    assert out["has_backup"] is True
    assert out["last_status"] == "STATUS_SUCCESS"
    assert out["last_backup_ms"] == RECENT_MS
    assert out["stale"] is False
    print("OK", out)


def test_missing_url_errors():
    out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
    assert "error" in out


if __name__ == "__main__":
    test_rpc_and_backup_selection()
    test_missing_url_errors()
    print("ALL TESTS PASSED")
