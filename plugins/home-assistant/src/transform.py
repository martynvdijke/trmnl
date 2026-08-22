#!/usr/bin/env python3
"""Home Assistant entity states transform for trmnl-home-assistant.

Home Assistant exposes entity states at GET /api/states authenticated with
a Bearer long-lived access token. This transform fetches that list and either
returns a filtered ordered list of requested entities or a domain summary.
"""

import json
import sys
import urllib.request


def _http(url, token, timeout=10):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(input):
    url = ""
    token = ""
    entities = ""
    try:
        fields = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        url = fields.get("url") or ""
        token = fields.get("token") or ""
        entities = fields.get("entities") or ""
    except (KeyError, TypeError):
        pass
    if not url:
        return {"error": "Set the url custom field to your Home Assistant server address."}

    base = url.rstrip("/")
    try:
        data = _http(base + "/api/states", token) or []
    except Exception:
        return {"error": "Could not fetch Home Assistant states. Check the url and token custom fields."}

    if not isinstance(data, list):
        data = []

    # Entities mode: non-empty comma-separated entity IDs
    if entities and entities.strip():
        wanted = [e.strip() for e in entities.split(",") if e.strip()]
        by_id = {}
        for entry in data:
            if not isinstance(entry, dict):
                continue
            eid = entry.get("entity_id") or ""
            by_id[eid] = entry
        items = []
        for eid in wanted:
            entry = by_id.get(eid)
            if entry is None:
                continue
            attrs = entry.get("attributes") if isinstance(entry.get("attributes"), dict) else {}
            name = attrs.get("friendly_name") or eid
            state = entry.get("state") or ""
            unit = attrs.get("unit_of_measurement") or ""
            items.append({"name": name, "state": state, "unit": unit})
        return {"mode": "entities", "total": len(data), "items": items}

    # Summary mode
    total = len(data)
    domains = ["light", "switch", "binary_sensor", "sensor", "climate", "media_player"]
    counts = {d: 0 for d in domains}
    lights_on = 0
    for entry in data:
        if not isinstance(entry, dict):
            continue
        eid = entry.get("entity_id") or ""
        domain = eid.split(".", 1)[0] if "." in eid else ""
        if domain in counts:
            counts[domain] += 1
        if domain == "light" and entry.get("state") == "on":
            lights_on += 1

    return {
        "mode": "summary",
        "total": total,
        "counts": counts,
        "lights_on": lights_on,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
