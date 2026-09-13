#!/usr/bin/env python3
"""Forgejo PRs/issues/CI transform for trmnl-forgejo.

Forgejo requires a token. This transform reads the authenticated user's open
issues (which include pull requests) and splits them by the presence of the
``pull_request`` field, then best-effort fetches the CI (Forgejo Actions) runs
for the user's first repository to surface running workflows and the last run
result.

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


def _as_list(payload, key):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get(key, [])
    return []


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
        return {"error": "Set the url custom field to your Forgejo instance address."}

    base = url.rstrip("/")
    headers = {
        "Authorization": "token " + api_key,
        "Content-Type": "application/json",
    }

    # /user/issues has no PR/issue filter param; PRs carry a pull_request field.
    try:
        items = _as_list(
            _http("GET", base + "/api/v1/user/issues?state=open&limit=50", headers),
            "data",
        ) or []
    except Exception:
        return {"error": "Could not reach Forgejo at " + base + "/api/v1/user/issues"}

    pr_list = []
    open_issues = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("pull_request"):
            repo = (it.get("repository") or {}).get("full_name", "")
            pr_list.append({"title": it.get("title", ""), "repo": repo})
        else:
            open_issues += 1

    ci_running = 0
    last_ci = ""
    try:
        repos = _as_list(_http("GET", base + "/api/v1/user/repos?limit=1", headers), "data") or []
        if repos and isinstance(repos[0], dict):
            full = repos[0].get("full_name", "")
            if full:
                runs = _as_list(
                    _http("GET", base + "/api/v1/repos/" + full + "/actions/runs?limit=10", headers),
                    "workflow_runs",
                ) or []
                ci_running = sum(
                    1 for r in runs if isinstance(r, dict) and r.get("status") == "running"
                )
                done = [r for r in runs if isinstance(r, dict) and r.get("status") != "running"]
                if done:
                    last_ci = done[0].get("conclusion") or done[0].get("status") or ""
    except Exception:
        pass

    return {
        "open_prs": len(pr_list),
        "prs": pr_list[:10],
        "open_issues": open_issues,
        "ci_running": ci_running,
        "last_ci": last_ci,
    }


if __name__ == "__main__":
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(json.dumps(run(payload)))
