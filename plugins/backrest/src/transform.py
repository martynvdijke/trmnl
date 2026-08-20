#!/usr/bin/env python3
"""Backrest last-backup transform for trmnl-backrest.

Backrest exposes a plain (or basic-auth) REST API. This transform reads the
list of backup plans and the recent operations to determine when the last
backup ran and whether it is stale.

Network is attempted but wrapped in try/except so a missing server or an
offline sandbox degrades to a clear error rather than a crash.
"""

import json
import sys
import time
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


def _as_list(payload, key):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get(key, [])
    return []


def _fmt_ago(ms):
    if not ms:
        return "never"
    age_ms = int(time.time() * 1000) - ms
    if age_ms < 0:
        age_ms = 0
    hours = age_ms / (1000 * 3600)
    if hours < 1:
        return "{} min ago".format(int(hours * 60))
    if hours < 48:
        return "{} hours ago".format(int(hours))
    return "{} days ago".format(int(hours / 24))


def run(input):
    url = ""
    try:
        fields = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        url = fields.get("url") or ""
    except (KeyError, TypeError):
        pass
    if not url:
        return {"error": "Set the url custom field to your Backrest server address."}

    base = url.rstrip("/")
    try:
        plans = _as_list(_http("GET", base + "/api/v1/plans"), "plans")
    except Exception:
        return {"error": "Could not reach Backrest at " + base + "/api/v1/plans"}

    plan_names = []
    for p in plans:
        if isinstance(p, dict):
            plan_names.append(p.get("id") or p.get("name") or "?")

    last_backup_ms = 0
    last_status = ""
    try:
        ops = _as_list(_http("GET", base + "/api/v1/operations?limit=20"), "operations")
    except Exception:
        ops = []

    backups = [o for o in ops if isinstance(o, dict) and o.get("type") == "backup"]

    def _t(o):
        return _num(o.get("unix_start_time_ms") or o.get("start_time") or 0)

    if backups:
        backups.sort(key=_t, reverse=True)
        b = backups[0]
        last_backup_ms = _t(b)
        last_status = b.get("status") or ""

    age_days = 0.0
    if last_backup_ms:
        age_days = (int(time.time() * 1000) - last_backup_ms) / (1000 * 3600 * 24)

    return {
        "plan_count": len(plans),
        "plan_names": plan_names,
        "last_backup_ms": last_backup_ms,
        "last_backup_ago": _fmt_ago(last_backup_ms),
        "last_backup_age_days": round(age_days, 1),
        "last_status": last_status,
        "has_backup": last_backup_ms > 0,
        "stale": age_days > 7,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
