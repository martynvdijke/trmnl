#!/usr/bin/env python3
"""Scrutiny disk-health transform for trmnl-scrutiny.

Scrutiny exposes a public (or basic-auth) health endpoint at
/api/health that returns a list of monitored devices with their SMART
status. This transform reshapes that list into a compact health summary
for the Liquid templates.

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


def run(input):
    url = ""
    try:
        fields = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        url = fields.get("url") or ""
    except (KeyError, TypeError):
        pass
    if not url:
        return {"error": "Set the url custom field to your Scrutiny server address."}

    base = url.rstrip("/")
    try:
        data = _http("GET", base + "/api/health") or []
    except Exception:
        return {"error": "Could not reach Scrutiny at " + base + "/api/health"}

    if not isinstance(data, list):
        data = data.get("devices", []) if isinstance(data, dict) else []

    total = len(data)
    failed = []
    warned = []
    devices = []
    for d in data:
        if not isinstance(d, dict):
            continue
        dev = d.get("device", d)
        status = (dev.get("status") or d.get("status") or "UNKNOWN").upper()
        model = dev.get("model") or d.get("model") or "Unknown"
        name = dev.get("name") or model
        temp = _num(dev.get("temp") or d.get("temp"))
        hours = _num(dev.get("power_on_hours") or d.get("power_on_hours"))
        devices.append(
            {"name": name, "model": model, "status": status, "temp": temp, "hours": hours}
        )
        if status == "FAIL":
            failed.append(name)
        elif status == "WARN":
            warned.append(name)

    return {
        "total": total,
        "failed": failed,
        "warned": warned,
        "failed_count": len(failed),
        "warned_count": len(warned),
        "healthy_count": total - len(failed) - len(warned),
        "devices": devices,
        "all_good": len(failed) == 0 and len(warned) == 0,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
