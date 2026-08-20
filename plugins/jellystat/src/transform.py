#!/usr/bin/env python3
"""Jellystat watch stats transform for trmnl-jellystat.

Jellystat requires a login (POST /api/auth/login) to obtain a bearer token,
then authenticated GETs for the summary and the most-watched shows. The poller
cannot perform this two-step flow, so this transform performs the network
calls itself (stdlib urllib only) and reshapes the result for the Liquid
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


def _extract_token(payload):
    if not isinstance(payload, dict):
        return ""
    if payload.get("token"):
        return payload["token"]
    data = payload.get("data")
    if isinstance(data, dict) and data.get("token"):
        return data["token"]
    session = payload.get("session")
    if isinstance(session, dict) and session.get("token"):
        return session["token"]
    return ""


def _login(url, username, password):
    body = json.dumps({"username": username, "password": password}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    base = url.rstrip("/")
    try:
        payload = _http("POST", base + "/api/auth/login", headers, body)
    except Exception:
        payload = _http("POST", base + "/api/login", headers, body)
    return _extract_token(payload)


def _num(value):
    try:
        return int(value or 0)
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
    token = _login(base, username, password)
    if not token:
        return {"error": "Could not log in to Jellystat. Check the url, username and password custom fields."}

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }

    try:
        summary = _http("GET", base + "/api/summary", headers) or {}
    except Exception:
        return {"error": "Could not fetch the Jellystat summary. Is the server reachable?"}

    try:
        watched = _http("GET", base + "/api/items/watched?type=show&limit=5", headers) or []
    except Exception:
        watched = []

    if not isinstance(watched, list):
        watched = []

    hours = summary.get("total_hours")
    if hours is None:
        hours = _num(summary.get("show_hours")) + _num(summary.get("movie_hours"))

    top_shows = []
    for w in watched:
        if not isinstance(w, dict):
            continue
        top_shows.append(
            {
                "name": w.get("name") or "",
                "plays": _num(w.get("plays")),
                "hours": _num(w.get("hours")),
            }
        )

    return {
        "hours": _num(hours),
        "plays": _num(summary.get("total_plays")),
        "users": _num(summary.get("total_users")),
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
