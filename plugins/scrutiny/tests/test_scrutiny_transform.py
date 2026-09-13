import importlib.util
import json
import os
import urllib.request as urllib_request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "transform.py")

spec = importlib.util.spec_from_file_location("scrutiny_transform", SRC)
transform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transform)


SUMMARY = {
    "success": True,
    "data": {
        "summary": {
            "uuid-ok": {
                "device": {"device_name": "sda", "model_name": "Samsung SSD", "device_status": "passed"},
                "smart": {"temp": 34, "power_on_hours": 1200},
            },
            "uuid-bad": {
                "device": {"device_name": "sdb", "model_name": "WD Red", "device_status": "failed"},
                "smart": {"temp": 41, "power_on_hours": 900},
            },
            "uuid-warn": {
                "device": {"device_name": "sdc", "model_name": "Crucial", "device_status": "warning"},
                "smart": {"temp": 38, "power_on_hours": 500},
            },
        }
    },
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
        if "/api/summary" in url:
            return FakeResponse(json.dumps(SUMMARY).encode())
        return FakeResponse(b"{}")


def test_summary_map():
    original = urllib_request.urlopen
    urllib_request.urlopen = FakeUrlopen()
    try:
        out = transform.run(
            {"trmnl": {"plugin_settings": {"custom_fields_values": {"url": "http://scrutiny:8080"}}}}
        )
    finally:
        urllib_request.urlopen = original

    assert "error" not in out, out
    assert out["total"] == 3
    assert out["failed_count"] == 1
    assert out["warned_count"] == 1
    assert out["healthy_count"] == 1
    assert out["all_good"] is False
    assert {d["temp"] for d in out["devices"]} == {34, 41, 38}
    assert any(d["name"] == "sdb" and d["status"] == "FAIL" for d in out["devices"])
    print("OK", out)


def test_missing_url_errors():
    out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
    assert "error" in out


if __name__ == "__main__":
    test_summary_map()
    test_missing_url_errors()
    print("ALL TESTS PASSED")
