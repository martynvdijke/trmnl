#!/usr/bin/env python3
"""Jellystat watch stats transform for trmnl-jellystat.

Jellystat requires a login (POST /auth/login, outside the /api prefix) to
obtain a bearer token, then authenticated GETs/POSTs under /stats. The poller
cannot perform this two-step flow, so this transform performs the network calls
itself (stdlib urllib only) and reshapes the result for the Liquid templates.

Network is attempted but wrapped in try/except so a missing server or an
offline sandbox degrades to a clear error rather than a crash.
"""

import json
import sys
import urllib.request

DAYS = 30


def _http(method, url, headers=None, data=None, timeout=10):
    req = urllib.request.Request(
        url, data=data, headers=headers or {}, method=method
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_token(payload):
    if not isinstance(payload, dict):
        return ""
    if payload.get("token"):
        return payload["token"]
    data = payload.get("data")
    if isinstance(data, dict) and data.get("token"):
        return data["token"]
    return ""


def _login(base, username, password):
    body = json.dumps({"username": username, "password": password}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    return _extract_token(_http("POST", base + "/auth/login", headers, body))


def _num(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0


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
        return {"error": "Set the url custom field to your Jellystat server address."}

    base = url.rstrip("/")
    try:
        token = _login(base, username, password)
    except Exception:
        token = ""
    if not token:
        return {"error": "Could not log in to Jellystat. Check the url, username and password custom fields."}

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }

    # getViewsOverTime rows are grouped by day and library; "duration" is in
    # minutes and "count" is the number of plays.
    hours = 0.0
    plays = 0
    try:
        views = _http("GET", base + "/stats/getViewsOverTime?days=%d" % DAYS, headers) or {}
        for day in (views.get("stats") or []) if isinstance(views, dict) else []:
            if not isinstance(day, dict):
                continue
            for key, val in day.items():
                if key == "Key" or not isinstance(val, dict):
                    continue
                plays += _num(val.get("count"))
                hours += _num(val.get("duration")) / 60.0
    except Exception:
        pass

    users = 0
    try:
        activity = _http("GET", base + "/stats/getAllUserActivity", headers) or []
        if isinstance(activity, list):
            users = len(
                {a.get("UserName") for a in activity if isinstance(a, dict) and a.get("UserName")}
            )
    except Exception:
        pass

    top_shows = []
    try:
        body = json.dumps({"days": DAYS, "type": "Series"}).encode("utf-8")
        rows = _http("POST", base + "/stats/getMostViewedByType", headers, body) or []
        for r in rows if isinstance(rows, list) else []:
            if not isinstance(r, dict):
                continue
            top_shows.append(
                {
                    "name": r.get("Name") or "",
                    "plays": _num(r.get("Plays")),
                    "hours": round(_num(r.get("total_playback_duration")) / 3600.0, 1),
                }
            )
    except Exception:
        top_shows = []

    return {
        "hours": round(hours, 1),
        "plays": plays,
        "users": users,
        "top_shows": top_shows,
        "top_show": top_shows[0] if top_shows else {},
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
