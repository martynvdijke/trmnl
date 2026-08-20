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


def _progress_pct(progress):
    try:
        p = float(progress)
    except (TypeError, ValueError):
        return 0
    if p <= 1 and p > 0:
        p = p * 100
    return max(0, min(100, int(p)))


def run(input):
    values = input.get("trmnl", {}).get("plugin_settings", {}).get("custom_fields_values", {})
    url = _get(values, "url")
    api_key = _get(values, "api_key")

    if not url:
        return {"error": "Missing URL. Set the URL custom field to your Booklore instance."}

    headers = {"Authorization": "Bearer " + api_key} if api_key else {}
    base = url.rstrip("/") + "/api/books"

    try:
        size_resp = _http_json(base + "?page=0&size=1", headers=headers)
        list_resp = _http_json(base + "?page=0&size=5", headers=headers)
    except RuntimeError as e:
        return {"error": str(e)}

    total_books = int(size_resp.get("totalElements", size_resp.get("total", 0)))

    content = list_resp.get("content", list_resp.get("data", []))
    reading = []
    for b in content:
        authors = b.get("authors") or []
        names = []
        if isinstance(authors, list):
            for a in authors:
                if isinstance(a, dict):
                    names.append(str(a.get("name", "")))
                else:
                    names.append(str(a))
        else:
            names.append(str(authors))
        author = ", ".join(n for n in names if n)
        pct = _progress_pct(b.get("progress", 0))
        reading.append({
            "title": b.get("title", "Unknown"),
            "author": author,
            "progress_pct": pct,
        })

    return {
        "total_books": total_books,
        "reading": reading,
        "reading_count": len(reading),
    }


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload)))
