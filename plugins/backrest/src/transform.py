#!/usr/bin/env python3
"""Backrest last-backup transform for trmnl-backrest.

Backrest does not expose a REST API: it speaks ConnectRPC over HTTP under
POST /v1.Backrest/* (JSON bodies). This transform calls GetConfig for the plan
list and GetOperations for recent operations, then determines when the last
backup ran and whether it is stale. Optional HTTP Basic auth is applied when a
username/password is configured.

Network is attempted but wrapped in try/except so a missing server or an
offline sandbox degrades to a clear error rather than a crash.
"""

import base64
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


def _auth_header(username, password):
    if not username and not password:
        return {}
    raw = (username + ":" + password).encode("utf-8")
    return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}


def _rpc(base, method, payload, headers):
    body = json.dumps(payload).encode("utf-8")
    return _http("POST", base + "/v1.Backrest/" + method, headers, body)


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
    username = ""
    password = ""
    try:
        fields = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        url = fields.get("url") or ""
        username = fields.get("username") or ""
        password = fields.get("password") or ""
    except (KeyError, TypeError):
        pass
    if not url:
        return {"error": "Set the url custom field to your Backrest server address."}

    base = url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    headers.update(_auth_header(username, password))

    try:
        config = _rpc(base, "GetConfig", {}, headers) or {}
    except Exception:
        return {"error": "Could not reach Backrest at " + base + "/v1.Backrest/GetConfig"}

    plans = config.get("plans") if isinstance(config, dict) else []
    if not isinstance(plans, list):
        plans = []

    plan_names = []
    for p in plans:
        if isinstance(p, dict):
            plan_names.append(p.get("id") or p.get("repo") or "?")

    try:
        ops_resp = _rpc(base, "GetOperations", {"selector": {}, "last_n": 20}, headers) or {}
    except Exception:
        ops_resp = {}
    ops = ops_resp.get("operations") if isinstance(ops_resp, dict) else []
    if not isinstance(ops, list):
        ops = []

    # A backup operation carries the oneof field "operation_backup".
    backups = [
        o for o in ops if isinstance(o, dict) and o.get("operation_backup") is not None
    ]

    def _t(o):
        return _num(o.get("unix_time_start_ms"))

    last_backup_ms = 0
    last_status = ""
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
