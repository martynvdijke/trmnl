#!/usr/bin/env python3
"""Reshapes the Immich random-search response for the TRMNL Liquid templates.

The plugin polls POST /api/search/random with an x-api-key header. Immich
returns an array of assets, which the poller wraps as {"data": [...]}. On a
failed request (e.g. a 422 from an invalid filter) the poller hands this
script an empty object.

run(input) returns a single-photo payload:

    { id, title, date, make, model, lens_model, focal_length, iso,
      exposure_time, f_number, width, height, file_size, city, state,
      country, image: "/api/trmnl/photo/<id>" }

or an error card when nothing could be fetched.
"""

import json
import sys


def _exif(asset):
    return asset.get("exifInfo") or {}


def _num(d, key):
    try:
        return int(d.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def run(input):
    data = input.get("data") if isinstance(input, dict) else input
    if not isinstance(data, list) or not data:
        return {
            "error": "No photos found. Check that album_id and person_id are valid JSON arrays of UUIDs, and that the url and api_key are correct."
        }

    asset = data[0]
    exif = _exif(asset)
    title = exif.get("description") or asset.get("originalFileName") or ""

    return {
        "id": asset.get("id") or "",
        "title": title,
        "date": asset.get("fileCreatedAt") or "",
        "make": exif.get("make") or "",
        "model": exif.get("model") or "",
        "lens_model": exif.get("lensModel") or "",
        "focal_length": exif.get("focalLength") or 0,
        "iso": _num(exif, "iso"),
        "exposure_time": exif.get("exposureTime") or "",
        "f_number": exif.get("fNumber") or 0,
        "width": _num(asset, "width"),
        "height": _num(asset, "height"),
        "file_size": _num(exif, "fileSizeInByte"),
        "city": exif.get("city") or "",
        "state": exif.get("state") or "",
        "country": exif.get("country") or "",
        "image": "/api/trmnl/photo/" + (asset.get("id") or ""),
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
