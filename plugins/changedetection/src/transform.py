#!/usr/bin/env python3
"""Changedetection.io transform for trmnl-changedetection.

Changedetection.io exposes a watch API at GET /api/v1/watch.
"""

import json
import sys
import urllib.request


def _http(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(input):
    url = ""
    api_key = ""
    try:
        fields = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        url = fields.get("url") or ""
        api_key = fields.get("api_key") or ""
    except (KeyError, TypeError):
        pass
    if not url:
        return {"error": "Set the url custom field to your changedetection.io server address."}

    base = url.rstrip("/")
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        data = _http(base + "/api/v1/watch", headers=headers) or {}
    except Exception:
        return {"error": "Could not fetch changedetection.io watches. Check the url and api_key custom fields."}

    if not isinstance(data, dict):
        data = {}

    total = len(data)
    unviewed = sum(1 for v in data.values() if isinstance(v, dict) and v.get("viewed") is False)
    paused = sum(1 for v in data.values() if isinstance(v, dict) and v.get("paused") is True)
    errored = sum(1 for v in data.values() if isinstance(v, dict) and v.get("last_error"))

    candidates = []
    for v in data.values():
        if not isinstance(v, dict):
            continue
        title = v.get("title") or v.get("url") or ""
        last_changed = v.get("last_changed")
        candidates.append({"title": title, "last_changed": last_changed})

    def sort_key(x):
        val = x["last_changed"]
        if val is None:
            return ""
        return str(val)

    candidates.sort(key=sort_key, reverse=True)
    recent = candidates[:5]

    return {
        "total": total,
        "unviewed": unviewed,
        "paused": paused,
        "errored": errored,
        "recent": recent,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
