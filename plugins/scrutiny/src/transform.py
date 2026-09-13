#!/usr/bin/env python3
"""Scrutiny disk-health transform for trmnl-scrutiny.

Scrutiny exposes device health at GET /api/summary, which returns
{"success": true, "data": {"summary": {<uuid>: {"device": {...}, "smart": {...}}}}}.
This transform reshapes that map into a compact health summary for the Liquid
templates.

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


def _bucket(status):
    """Map Scrutiny's status strings (passed/failed/warning) to FAIL/WARN/OK."""
    s = str(status or "").lower()
    if "fail" in s:
        return "FAIL"
    if "warn" in s:
        return "WARN"
    return "OK"


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
        data = _http("GET", base + "/api/summary") or {}
    except Exception:
        return {"error": "Could not reach Scrutiny at " + base + "/api/summary"}

    summary = {}
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, dict):
            summary = inner.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}
        if not summary:
            # Fallback for older/alternative deployments returning a flat map.
            summary = data.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}

    total = len(summary)
    failed = []
    warned = []
    devices = []
    for entry in summary.values():
        if not isinstance(entry, dict):
            continue
        dev = entry.get("device") or {}
        smart = entry.get("smart") or {}
        if not isinstance(smart, dict):
            smart = {}
        status = _bucket(
            dev.get("device_status") or entry.get("device_status") or "unknown"
        )
        model = dev.get("model_name") or dev.get("model") or "Unknown"
        name = (
            dev.get("device_label")
            or dev.get("label")
            or dev.get("device_name")
            or dev.get("name")
            or model
        )
        temp = _num(smart.get("temp")) or _num(dev.get("temp"))
        hours = _num(smart.get("power_on_hours")) or _num(dev.get("power_on_hours"))
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
