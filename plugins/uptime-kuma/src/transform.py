#!/usr/bin/env python3
"""Uptime Kuma status transform for trmnl-uptime-kuma.

Uptime Kuma exposes a public Status Page API at
GET /api/status-page/{slug} that needs no authentication. The poller can fetch
it, but this transform performs the GET itself (stdlib urllib only) so it can
reshape the monitors into up/down counts and a list of down monitors.
"""

import json
import sys
import urllib.request


def _http(url, timeout=10):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(input):
    url = ""
    slug = ""
    try:
        fields = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        url = fields.get("url") or ""
        slug = fields.get("slug") or ""
    except (KeyError, TypeError):
        pass
    if not url:
        return {"error": "Set the url custom field to your Uptime Kuma server address."}
    if not slug:
        return {"error": "Set the slug custom field to your Uptime Kuma status page slug."}

    base = url.rstrip("/")
    try:
        data = _http(base + "/api/status-page/" + slug) or {}
    except Exception:
        return {"error": "Could not fetch the Uptime Kuma status page. Check the url and slug custom fields."}

    monitors = data.get("monitors")
    if not isinstance(monitors, list):
        monitors = []

    total = len(monitors)
    up = 0
    down = 0
    pending = 0
    down_monitors = []
    for m in monitors:
        if not isinstance(m, dict):
            continue
        status = (m.get("status") or "").lower()
        if status == "up" or m.get("online") is True:
            up += 1
        elif status == "down" or m.get("online") is False:
            down += 1
            down_monitors.append(
                {
                    "name": m.get("name") or "",
                    "message": m.get("message") or "",
                }
            )
        else:
            pending += 1

    return {
        "total": total,
        "up": up,
        "down": down,
        "pending": pending,
        "down_monitors": down_monitors,
        "all_up": down == 0,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
