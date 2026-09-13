import importlib.util
import json
import os
import urllib.request as urllib_request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "transform.py")

spec = importlib.util.spec_from_file_location("forgejo_transform", SRC)
transform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transform)


ISSUES = [
    {"title": "Fix thing", "pull_request": {"html_url": "x"}, "repository": {"full_name": "owner/repo"}},
    {"title": "Bug report", "repository": {"full_name": "owner/repo"}},
    {"title": "Another issue"},
]

REPOS = [{"full_name": "owner/repo"}]

RUNS = [
    {"status": "running", "conclusion": ""},
    {"status": "completed", "conclusion": "success"},
]


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
        if "/user/issues" in url:
            return FakeResponse(json.dumps(ISSUES).encode())
        if "/user/repos" in url:
            return FakeResponse(json.dumps(REPOS).encode())
        if "/actions/runs" in url:
            return FakeResponse(json.dumps({"workflow_runs": RUNS}).encode())
        return FakeResponse(b"[]")


def test_split_prs_and_issues():
    original = urllib_request.urlopen
    urllib_request.urlopen = FakeUrlopen()
    try:
        out = transform.run(
            {"trmnl": {"plugin_settings": {"custom_fields_values": {"url": "https://forgejo.example.com", "api_key": "x"}}}}
        )
    finally:
        urllib_request.urlopen = original

    assert "error" not in out, out
    assert out["open_prs"] == 1
    assert out["prs"][0]["title"] == "Fix thing"
    assert out["prs"][0]["repo"] == "owner/repo"
    assert out["open_issues"] == 2
    assert out["ci_running"] == 1
    assert out["last_ci"] == "success"
    print("OK", out)


def test_missing_url_errors():
    out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
    assert "error" in out


if __name__ == "__main__":
    test_split_prs_and_issues()
    test_missing_url_errors()
    print("ALL TESTS PASSED")
