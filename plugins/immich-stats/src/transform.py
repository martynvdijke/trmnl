#!/usr/bin/env python3
"""Merges the four Immich server endpoints into a single TRMNL payload.

The poller requests four URLs (newline-separated in settings.yml) and hands
this script:

    {
      "IDX_0": <GET /api/server/statistics>,
      "IDX_1": <GET /api/server/version>,
      "IDX_2": <GET /api/server/about>,
      "IDX_3": <GET /api/server/license>,
      "trmnl": { "plugin_settings": { "custom_fields_values": {...} } }
    }

A failed endpoint is an empty object {}. run(input) returns the merged,
formatted payload that the Liquid templates render.
"""

import json
import sys


def format_bytes(n):
    """Render a byte count with two significant figures (e.g. 1.4 GB)."""
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        n = 0
    if n < 1024:
        return "%d B" % n
    value = float(n)
    units = ["KB", "MB", "GB", "TB", "PB", "EB"]
    for unit in units:
        value /= 1024.0
        if value < 1024 or unit == units[-1]:
            return "%.1f %s" % (value, unit)
    return "%d B" % n


def _num(d, key):
    try:
        return int(d.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def run(input):
    idx = input.get("IDX_0")
    ver = input.get("IDX_1")
    about = input.get("IDX_2")
    license_data = input.get("IDX_3")

    if not idx:
        return {"error": "Could not fetch Immich statistics. Check the url and api_key custom fields."}

    users = []
    for u in idx.get("usageByUser") or []:
        usage = _num(u, "usage")
        quota = _num(u, "quotaSizeInBytes")
        users.append(
            {
                "user_name": u.get("userName") or "",
                "photos": _num(u, "photos"),
                "videos": _num(u, "videos"),
                "usage": usage,
                "usage_human": format_bytes(usage),
                "quota": quota,
                "quota_human": format_bytes(quota),
            }
        )

    photos = _num(idx, "photos")
    videos = _num(idx, "videos")
    usage = _num(idx, "usage")

    version_full = ""
    if ver:
        version_full = "%d.%d.%d" % (
            int(ver.get("major") or 0),
            int(ver.get("minor") or 0),
            int(ver.get("patch") or 0),
        )
        if ver.get("prerelease"):
            version_full += "-" + ver["prerelease"]

    server = {}
    if about:
        server = {
            "version": about.get("version") or "",
            "build": about.get("build") or "",
            "licensed": bool(about.get("licensed")),
            "nodejs": about.get("nodejs") or "",
            "ffmpeg": about.get("ffmpeg") or "",
            "exiftool": about.get("exiftool") or "",
            "imagemagick": about.get("imagemagick") or "",
            "libvips": about.get("libvips") or "",
            "source_commit": about.get("sourceCommit") or "",
            "source_url": about.get("sourceUrl") or "",
            "repository_url": about.get("repositoryUrl") or "",
        }

    return {
        "photos": photos,
        "videos": videos,
        "total_assets": photos + videos,
        "usage": usage,
        "usage_human": format_bytes(usage),
        "usage_by_user": users,
        "version_full": version_full,
        "version": ver or {},
        "server": server,
        "license": license_data,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
