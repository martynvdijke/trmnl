import json
import sys
from datetime import datetime, timezone
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError


def _get(values, key, default=""):
    v = values.get(key)
    return v if isinstance(v, str) else default


def _http_json(url, headers=None, data=None, method="GET"):
    req = urllib_request.Request(url, data=data, method=method)
    if headers:
        for k, val in headers.items():
            req.add_header(k, val)
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except (URLError, HTTPError) as e:
        raise RuntimeError("request failed: %s" % e)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError("invalid JSON response")


def _login(url, username, password):
    body = json.dumps({"identity": username, "secret": password}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    data = _http_json(url.rstrip("/") + "/api/tokens", headers=headers, data=body, method="POST")
    token = data.get("token") or (data.get("data") or {}).get("token")
    if not token:
        raise RuntimeError("login failed: no token returned")
    return token


def _days_left(expires_on):
    if not expires_on:
        return None
    s = expires_on.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0, int((dt - now).total_seconds() // 86400))


def run(input):
    values = input.get("trmnl", {}).get("plugin_settings", {}).get("custom_fields_values", {})
    url = _get(values, "url")
    username = _get(values, "username")
    password = _get(values, "password")

    if not url:
        return {"error": "Missing URL. Set the URL custom field to your Nginx Proxy Manager instance."}

    try:
        token = _login(url, username, password)
    except RuntimeError as e:
        return {"error": str(e)}

    try:
        certs_raw = _http_json(
            url.rstrip("/") + "/api/nginx/certificates",
            headers={"Authorization": "Bearer " + token},
        )
    except RuntimeError as e:
        return {"error": str(e)}

    if isinstance(certs_raw, dict):
        certs_raw = certs_raw.get("data", certs_raw.get("certs", []))

    certs = []
    expiring_soon_count = 0
    for c in certs_raw:
        domains = c.get("domain_names") or []
        domain = domains[0] if domains else (c.get("domain") or "unknown")
        days = _days_left(c.get("expiresOn") or c.get("notAfter"))
        expiring_soon = bool(days is not None and days <= 30)
        if expiring_soon:
            expiring_soon_count += 1
        certs.append({
            "domain": domain,
            "days_left": days if days is not None else "?",
            "expiring_soon": expiring_soon,
        })

    certs.sort(key=lambda x: (x["days_left"] == "?", 9999 if x["days_left"] == "?" else x["days_left"]))

    return {
        "certs": certs,
        "count": len(certs),
        "expiring_soon_count": expiring_soon_count,
    }


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload)))
