#!/usr/bin/env python3
"""Paperless-ngx inbox and library transform for trmnl-paperless-ngx.

Fetches document statistics and recent documents from a Paperless-ngx
instance via its REST API using Token authentication.
"""

import json
import sys
import urllib.request


def _http(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(input):
    url = ""
    api_token = ""
    try:
        fields = input["trmnl"]["plugin_settings"]["custom_fields_values"]
        url = fields.get("url") or ""
        api_token = fields.get("api_token") or ""
    except (KeyError, TypeError):
        pass
    if not url:
        return {"error": "Set the url custom field to your Paperless-ngx server address."}

    base = url.rstrip("/")
    headers = {}
    if api_token:
        headers["Authorization"] = f"Token {api_token}"

    try:
        data = _http(base + "/api/statistics/", headers=headers) or {}
    except Exception:
        return {"error": "Could not fetch Paperless-ngx statistics. Check the url and api_token custom fields."}

    total = data.get("documents_total")
    inbox = data.get("documents_inbox")
    if total is None:
        total = 0
    if inbox is None:
        inbox = 0
    try:
        total = int(total)
    except (ValueError, TypeError):
        total = 0
    try:
        inbox = int(inbox)
    except (ValueError, TypeError):
        inbox = 0

    recent = []
    try:
        doc_data = _http(base + "/api/documents/?page_size=5&ordering=-created", headers=headers) or {}
        results = doc_data.get("results")
        if not isinstance(results, list):
            results = []
        for doc in results:
            if not isinstance(doc, dict):
                continue
            title = doc.get("title") or ""
            created = doc.get("created") or ""
            if created and "T" in created:
                created = created.split("T")[0]
            recent.append({"title": title, "created": created})
    except Exception:
        recent = []

    return {
        "total_documents": total,
        "inbox_count": inbox,
        "recent": recent,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
