import importlib.util
import json
import os
import urllib.request as urllib_request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "transform.py")

spec = importlib.util.spec_from_file_location("booklore_transform", SRC)
transform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transform)


BOOKS = [
    {
        "title": "Book A",
        "lastReadTime": "2024-03-02T10:00:00Z",
        "metadata": {"authors": ["Alice", "Bob"]},
        "epubProgress": {"percentage": 42.6},
    },
    {
        "title": "Book B",
        "lastReadTime": "2024-03-03T10:00:00Z",
        "metadata": {"authors": ["Carol"]},
        "pdfProgress": {"percentage": 10},
    },
    {
        "title": "Book C",
        "lastReadTime": "2024-01-01T10:00:00Z",
        "metadata": {"authors": []},
    },
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
        if "/api/v1/books" in url:
            return FakeResponse(json.dumps(BOOKS).encode())
        return FakeResponse(b"[]")


def test_list_shape():
    original = urllib_request.urlopen
    urllib_request.urlopen = FakeUrlopen()
    try:
        out = transform.run(
            {"trmnl": {"plugin_settings": {"custom_fields_values": {"url": "https://booklore.example.com", "api_key": "x"}}}}
        )
    finally:
        urllib_request.urlopen = original

    assert "error" not in out, out
    assert out["total_books"] == 3
    assert out["reading_count"] == 2
    # Most recently read book with progress comes first.
    assert out["reading"][0]["title"] == "Book B"
    assert out["reading"][0]["author"] == "Carol"
    assert out["reading"][0]["progress_pct"] == 10
    assert out["reading"][1]["title"] == "Book A"
    assert out["reading"][1]["author"] == "Alice, Bob"
    assert out["reading"][1]["progress_pct"] == 43
    print("OK", out)


def test_missing_url_errors():
    out = transform.run({"trmnl": {"plugin_settings": {"custom_fields_values": {}}}})
    assert "error" in out


if __name__ == "__main__":
    test_list_shape()
    test_missing_url_errors()
    print("ALL TESTS PASSED")
