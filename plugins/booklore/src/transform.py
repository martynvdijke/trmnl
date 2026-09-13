import json
import sys
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError


def _get(values, key, default=""):
    v = values.get(key)
    return v if isinstance(v, str) else default


def _http_json(url, headers=None):
    req = urllib_request.Request(url, method="GET")
    if headers:
        for k, val in headers.items():
            req.add_header(k, val)
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except (URLError, HTTPError) as e:
        raise RuntimeError("request failed: %s" % e)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("invalid JSON response")


def _progress_pct(book):
    # Booklore stores per-format progress as {percentage: 0-100}.
    for key in (
        "epubProgress",
        "pdfProgress",
        "koreaderProgress",
        "audiobookProgress",
        "koboProgress",
        "cbxProgress",
    ):
        p = book.get(key)
        if isinstance(p, dict) and p.get("percentage") is not None:
            try:
                return max(0, min(100, int(round(float(p["percentage"])))))
            except (TypeError, ValueError):
                continue
    return 0


def _authors(book):
    meta = book.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    authors = meta.get("authors") or book.get("authors") or []
    names = []
    if isinstance(authors, list):
        for a in authors:
            names.append(str(a.get("name", "")) if isinstance(a, dict) else str(a))
    elif authors:
        names.append(str(authors))
    return ", ".join(n for n in names if n)


def run(input):
    values = input.get("trmnl", {}).get("plugin_settings", {}).get("custom_fields_values", {})
    url = _get(values, "url")
    api_key = _get(values, "api_key")

    if not url:
        return {"error": "Missing URL. Set the URL custom field to your Booklore instance."}

    headers = {"Authorization": "Bearer " + api_key} if api_key else {}
    base = url.rstrip("/") + "/api/v1/books"

    try:
        books = _http_json(base, headers=headers)
    except RuntimeError as e:
        return {"error": str(e)}

    if isinstance(books, dict):
        # Defensive: tolerate a wrapped/paginated shape if Booklore changes.
        books = books.get("content", books.get("data", []))
    if not isinstance(books, list):
        books = []
    books = [b for b in books if isinstance(b, dict)]

    with_progress = [b for b in books if _progress_pct(b) > 0]
    with_progress.sort(key=lambda b: str(b.get("lastReadTime") or ""), reverse=True)

    reading = []
    for b in with_progress[:5]:
        meta = b.get("metadata")
        if not isinstance(meta, dict):
            meta = {}
        title = b.get("title") or meta.get("title") or "Unknown"
        reading.append({
            "title": title,
            "author": _authors(b),
            "progress_pct": _progress_pct(b),
        })

    return {
        "total_books": len(books),
        "reading": reading,
        "reading_count": len(reading),
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
