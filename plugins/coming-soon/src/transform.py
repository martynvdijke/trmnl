#!/usr/bin/env python3
"""Coming Soon transform for trmnl-coming-soon.

Works for both Sonarr and Radarr. The calendar endpoint returns episodes
(when an item has a "series" key) and movies (otherwise). This transform
fetches the next two weeks of releases, keeps only those still in the future,
sorts them, and builds a poster URL for each so the TRMNL device can fetch the
art directly.
"""

import datetime
import json
import sys
import urllib.request


def _http(url, timeout=10):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse(dt):
    if not dt:
        return None
    s = str(dt).replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None


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
        return {"error": "Set the url custom field to your Sonarr/Radarr server address."}

    base = url.rstrip("/")
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.strftime("%Y-%m-%d")
    end = (now + datetime.timedelta(days=14)).strftime("%Y-%m-%d")
    cal_url = (
        base + "/api/v3/calendar?start=" + start + "&end=" + end + "&apikey=" + api_key
    )

    try:
        items = _http(cal_url) or []
    except Exception:
        return {"error": "Could not fetch the Sonarr/Radarr calendar. Check the url and api_key custom fields."}
    if not isinstance(items, list):
        items = []

    collected = []
    for it in items:
        if not isinstance(it, dict):
            continue
        air = _parse(it.get("airDateUtc"))
        if air is None or air < now:
            continue

        series = it.get("series")
        if isinstance(series, dict):
            kind = "Episode"
            series_title = series.get("title") or ""
            poster_id = series.get("id")
            title = it.get("title") or ""
            subtitle = series_title
        else:
            kind = "Movie"
            series_title = ""
            poster_id = it.get("id")
            title = it.get("title") or ""
            subtitle = str(it.get("year") or "")

        if not poster_id:
            continue

        poster = (
            base + "/api/v3/MediaCover/" + str(poster_id) + "/poster.jpg?apikey=" + api_key
        )
        collected.append(
            {
                "title": title,
                "series": series_title,
                "kind": kind,
                "subtitle": subtitle,
                "poster": poster,
                "_dt": air,
            }
        )

    collected.sort(key=lambda x: x["_dt"])
    out = []
    for c in collected:
        dt = c.pop("_dt")
        c["air"] = dt.strftime("%b %d %H:%M")
        out.append(c)

    movies = sum(1 for c in out if c["kind"] == "Movie")
    episodes = sum(1 for c in out if c["kind"] == "Episode")

    return {
        "count": len(out),
        "movies": movies,
        "episodes": episodes,
        "window_days": 14,
        "items": out,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
