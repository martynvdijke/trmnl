#!/usr/bin/env python3
"""AdGuard Home stats transform for trmnl-adguard-home.

AdGuard Home exposes unauthenticated-by-default control endpoints that require
HTTP Basic auth. The poller cannot attach Basic credentials to the control
routes, so this transform performs the GETs itself (stdlib urllib only) and
reshapes the result for the Liquid templates.
"""

import base64
import json
import sys
import urllib.request


def _http(url, headers, timeout=10):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _num(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_blocked(entry):
    if isinstance(entry, dict):
        return {
            "domain": entry.get("domain") or "",
            "count": _num(entry.get("count")),
        }
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        return {"domain": str(entry[0]), "count": _num(entry[1])}
    return {"domain": "", "count": 0}


def _hourly_series(stats):
    """Per-hour [{ts, y}] points for DNS queries and blocked requests.

    /control/stats returns parallel arrays of hourly values, oldest first,
    covering roughly the last 24 hours (the newest bucket is the current
    partial hour). Timestamps are reconstructed backwards from the current
    hour so the chart's x axis lines up with wall-clock time even though
    AdGuard does not send them.
    """
    def arr(key):
        v = stats.get(key)
        return v if isinstance(v, list) else []

    query_counts = arr("num_dns_queries")
    n = len(query_counts)
    if n == 0:
        return [], []

    import datetime

    hour_start = datetime.datetime.now(datetime.timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )

    def stamps():
        base = int(hour_start.timestamp())
        return [base - (n - 1 - i) * 3600 for i in range(n)]

    blocked_per_hour = []
    raw_blocked = [
        arr("num_blocked_filtering"),
        arr("num_replaced_safebrowsing"),
        arr("num_replaced_parental"),
        arr("num_replaced_safesearch"),
    ]
    for i in range(n):
        total = 0
        for source in raw_blocked:
            if len(source) == n:
                total += _num(source[i])
        blocked_per_hour.append(total)

    ts = stamps()
    queries_series = [{"ts": ts[i], "y": _num(query_counts[i])} for i in range(n)]
    blocked_series = [{"ts": ts[i], "y": blocked_per_hour[i]} for i in range(n)]
    return queries_series, blocked_series


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
        return {"error": "Set the url custom field to your AdGuard Home server address."}

    base = url.rstrip("/")
    raw = "%s:%s" % (username, password)
    token = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    headers = {"Authorization": "Basic " + token}

    try:
        stats = _http(base + "/control/stats", headers) or {}
    except Exception:
        return {"error": "Could not fetch AdGuard stats. Check the url, username and password custom fields."}

    try:
        top_raw = _http(base + "/control/top_blocked_domains", headers) or []
    except Exception:
        top_raw = []
    if not isinstance(top_raw, list):
        top_raw = []

    blocked = (
        _num(stats.get("num_blocked_filtering"))
        + _num(stats.get("num_replaced_safebrowsing"))
        + _num(stats.get("num_replaced_parental"))
        + _num(stats.get("num_replaced_safesearch"))
    )
    queries = _num(stats.get("num_queries"))
    blocked_pct = round(blocked / queries * 100) if queries else 0

    top_blocked = [_normalize_blocked(e) for e in top_raw[:3]]
    top_blocked_domain = top_blocked[0]["domain"] if top_blocked else ""

    queries_series, blocked_series = _hourly_series(stats)

    return {
        "queries": queries,
        "blocked": blocked,
        "blocked_pct": blocked_pct,
        "top_blocked": top_blocked,
        "top_blocked_domain": top_blocked_domain,
        "queries_series": queries_series,
        "blocked_series": blocked_series,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
