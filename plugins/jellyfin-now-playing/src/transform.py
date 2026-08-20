#!/usr/bin/env python3
"""Jellyfin Now Playing transform for trmnl-jellyfin.

The plugin polls GET /Sessions (wrapped by the poller as {"data": [...]}).
This transform keeps only sessions that are actively playing media and
reshapes each into a compact card with a poster-art URL, progress and a
subtitle line. Poster URLs embed the API key so the TRMNL device can fetch
them directly from the Jellyfin server.
"""

import json
import sys


def _ticks_to_minutes(ticks):
    try:
        ticks = int(ticks or 0)
    except (TypeError, ValueError):
        ticks = 0
    if ticks <= 0:
        return 0
    return int(round(ticks / 10_000_000 / 60))


def _progress(position_ticks, runtime_ticks):
    try:
        pos = int(position_ticks or 0)
        run = int(runtime_ticks or 0)
    except (TypeError, ValueError):
        return 0
    if run <= 0:
        return 0
    pct = int(round(pos / run * 100))
    return max(0, min(100, pct))


def _poster(url, api_key, item):
    # For episodes the series poster is more recognizable than the episode still.
    poster_id = item.get("SeriesId") or item.get("Id")
    if not poster_id:
        return ""
    return (
        url.rstrip("/")
        + "/Items/"
        + str(poster_id)
        + "/Images/Primary?maxWidth=400&quality=80&api_key="
        + api_key
    )


def _subtitle(item):
    kind = (item.get("Type") or "").lower()
    if kind == "episode":
        series = item.get("SeriesName") or ""
        season = item.get("ParentIndexNumber")
        episode = item.get("IndexNumber")
        if season and episode:
            try:
                return "%s · S%02dE%02d" % (series, int(season), int(episode))
            except (TypeError, ValueError):
                return series
        return series
    year = item.get("ProductionYear")
    if year:
        return str(year)
    return ""


def _session(s, url, api_key):
    item = s.get("NowPlayingItem") or {}
    play_state = s.get("PlayState") or {}
    runtime = item.get("RunTimeTicks")
    position = play_state.get("PositionTicks")
    return {
        "user": s.get("UserName") or "",
        "client": s.get("Client") or "",
        "device": s.get("DeviceName") or "",
        "title": item.get("Name") or "",
        "series": item.get("SeriesName") or "",
        "type": item.get("Type") or "",
        "year": item.get("ProductionYear") or "",
        "subtitle": _subtitle(item),
        "runtime_min": _ticks_to_minutes(runtime),
        "position_min": _ticks_to_minutes(position),
        "progress": _progress(position, runtime),
        "paused": bool(play_state.get("IsPaused")),
        "transcoding": bool(s.get("TranscodingInfo")),
        "poster": _poster(url, api_key, item),
    }


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
        return {"error": "Set the url custom field to your Jellyfin server address."}

    data = input.get("data") if isinstance(input, dict) else input
    if not isinstance(data, list):
        data = input if isinstance(input, list) else []

    playing = []
    for s in data:
        if not isinstance(s, dict) or not s.get("NowPlayingItem"):
            continue
        playing.append(_session(s, url, api_key))

    return {"count": len(playing), "playing": playing}


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
