#!/usr/bin/env python3
"""Audiobookshelf currently-listening transform for trmnl-audiobookshelf.

Audiobookshelf requires a bearer token. This transform fetches the recent
listening sessions and picks the one currently in progress (active first,
otherwise the most recently updated in-progress session), then reshapes it
into a cover + progress summary for the Liquid templates.

Network is attempted but wrapped in try/except so a missing server or an
offline sandbox degrades to a clear error rather than a crash.
"""

import json
import sys
import urllib.request


def _http(method, url, headers=None, data=None, timeout=10):
    req = urllib.request.Request(
        url, data=data, headers=headers or {}, method=method
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _num(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


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
        return {"error": "Set the url custom field to your Audiobookshelf server address."}

    base = url.rstrip("/")
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }

    try:
        data = _http(
            "GET",
            base + "/api/sessions?sort=updatedAt&collapsed=true&itemsPerPage=20",
            headers,
        ) or {}
    except Exception:
        return {"error": "Could not reach Audiobookshelf at " + base + "/api/sessions"}

    sessions = data.get("sessions", data) if isinstance(data, dict) else data
    if not isinstance(sessions, list):
        sessions = []

    current = None
    for s in sessions:
        if isinstance(s, dict) and s.get("isActive"):
            current = s
            break
    if current is None:
        candidates = [
            s
            for s in sessions
            if isinstance(s, dict) and _float(s.get("progress") or 0) < 1
        ]
        if candidates:
            candidates.sort(key=lambda s: _num(s.get("updatedAt") or 0), reverse=True)
            current = candidates[0]

    if current is None:
        return {
            "has_session": False,
            "title": "",
            "author": "",
            "progress": 0,
            "current_time": 0,
            "duration": 0,
            "cover": "",
            "is_active": False,
        }

    meta = current.get("mediaMetadata", {}) or {}
    title = current.get("displayTitle") or meta.get("title") or ""
    author = meta.get("author") or ""
    progress = round(_float(current.get("progress") or 0) * 100)
    library_item_id = current.get("libraryItemId") or ""
    cover = (base + "/api/items/" + library_item_id + "/cover") if library_item_id else ""

    return {
        "has_session": True,
        "title": title,
        "author": author,
        "progress": progress,
        "current_time": _num(current.get("currentTime") or 0),
        "duration": _num(current.get("duration") or 0),
        "cover": cover,
        "is_active": bool(current.get("isActive")),
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
