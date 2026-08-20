#!/usr/bin/env python3
"""BoardGameGeek transform for trmnl.

Fetches the user's recent plays and their owned collection from the public
BoardGameGeek XML API (v2), enriches plays with cover art via the thing
endpoint, and surfaces one randomly chosen owned game as a "from your
collection" feature. All HTTP is done with urllib (stdlib) and retries the
API's 202 "processing" responses.
"""

import json
import random
import sys
import time
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from xml.etree import ElementTree as ET

BGG_API = "https://boardgamegeek.com/xmlapi2"
USER_AGENT = "trmnl-boardgamegeek/1.0 (+https://github.com/martynvdijke/trmnl)"
PLAY_COUNT = 10


def _http_get(url, retries=5, delay=2.0):
    """GET a URL, retrying while BGG returns its 202 "still processing" reply."""
    last = None
    for attempt in range(retries):
        req = urllib_request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib_request.urlopen(req, timeout=20) as resp:
                status = getattr(resp, "status", getattr(resp, "code", 200))
                body = resp.read()
            if status == 200 and body.strip():
                return body
            last = "HTTP %s" % status
        except (HTTPError, URLError) as e:
            last = str(e)
        if attempt < retries - 1:
            time.sleep(delay)
    raise RuntimeError("BGG did not respond (%s)" % last)


def _parse(body):
    try:
        return ET.fromstring(body)
    except ET.ParseError as e:
        raise RuntimeError("invalid XML from BGG: %s" % e)


def _text(el, default=""):
    if el is None:
        return default
    return (el.text or "").strip() or default


def _parse_plays(body):
    root = _parse(body)
    plays = []
    for play in root.findall("play"):
        item = play.find("item")
        if item is None:
            continue
        oid = item.get("objectid")
        if not oid:
            continue
        name_el = item.find("name")
        name = (name_el.text or "").strip() if name_el is not None else ""
        plays.append({"id": oid, "name": name, "date": play.get("date") or ""})
    return plays


def _fetch_images(ids):
    """Batch the thing endpoint to map game id -> cover/thumbnail/year/rating."""
    meta = {}
    unique = list(dict.fromkeys(ids))
    if not unique:
        return meta
    for i in range(0, len(unique), 20):
        chunk = unique[i : i + 20]
        url = "%s/thing?id=%s&stats=1" % (BGG_API, ",".join(chunk))
        root = _parse(_http_get(url))
        for item in root.findall("item"):
            oid = item.get("id")
            if not oid:
                continue
            img = _text(item.find("image"))
            thumb = _text(item.find("thumbnail")) or img
            year_el = item.find("yearpublished")
            year = year_el.get("value") if year_el is not None else ""
            rating_el = item.find(".//ratings/average")
            rating = rating_el.get("value") if rating_el is not None else ""
            meta[oid] = {
                "image": img,
                "thumbnail": thumb,
                "year": year,
                "rating": rating,
            }
    return meta


def _parse_collection(body):
    root = _parse(body)
    owned = []
    for item in root.findall("item"):
        oid = item.get("objectid")
        if not oid:
            continue
        name_el = item.find("name")
        name = (name_el.text or "").strip() if name_el is not None else ""
        img = _text(item.find("image"))
        thumb = _text(item.find("thumbnail")) or img
        year_el = item.find("yearpublished")
        year = (year_el.text or "").strip() if year_el is not None else ""
        rating_el = item.find(".//rating")
        rating = rating_el.get("value") if rating_el is not None else ""
        owned.append(
            {
                "id": oid,
                "name": name,
                "image": img,
                "thumbnail": thumb,
                "year": year,
                "rating": rating,
            }
        )
    return owned


def run(input):
    username = ""
    try:
        values = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        username = (values.get("username") or "").strip()
    except (KeyError, TypeError, AttributeError):
        pass
    if not username:
        return {"error": "Set the username custom field to your BoardGameGeek username."}

    try:
        plays = _parse_plays(
            _http_get(
                "%s/plays?username=%s&count=%d"
                % (BGG_API, quote(username), PLAY_COUNT)
            )
        )
    except RuntimeError as e:
        return {"error": "Could not load your plays from BoardGameGeek: %s" % e}

    images = _fetch_images([p["id"] for p in plays])
    for p in plays:
        m = images.get(p["id"], {})
        p["image"] = m.get("thumbnail", "")
        p["year"] = m.get("year", "")
        p["rating"] = m.get("rating", "")

    owned = []
    try:
        owned = _parse_collection(
            _http_get(
                "%s/collection?username=%s&own=1&stats=1"
                % (BGG_API, quote(username))
            )
        )
    except RuntimeError:
        owned = []

    featured = None
    if owned:
        pick = random.choice(owned)
        featured = {
            "id": pick["id"],
            "name": pick["name"],
            "image": pick["image"] or pick["thumbnail"],
            "thumbnail": pick["thumbnail"] or pick["image"],
            "year": pick["year"],
            "rating": pick["rating"],
        }

    return {
        "username": username,
        "plays": plays,
        "featured": featured,
        "owned_count": len(owned),
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}
    print(json.dumps(run(payload)))
