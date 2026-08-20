import json
import sys
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode


def _get(values, key, default=""):
    v = values.get(key)
    return v if isinstance(v, str) else default


def _http(url, headers=None, data=None, method="GET"):
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


def _token(url, client_id, client_secret, username, password):
    body = urlencode({
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
    }).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = _http(
        url.rstrip("/") + "/oauth/v2/token",
        headers=headers,
        data=body,
        method="POST",
    )
    tok = data.get("access_token")
    if not tok:
        raise RuntimeError("auth failed: no access token returned")
    return tok


def run(input):
    values = input.get("trmnl", {}).get("plugin_settings", {}).get("custom_fields_values", {})
    url = _get(values, "url")
    client_id = _get(values, "client_id")
    client_secret = _get(values, "client_secret")
    username = _get(values, "username")
    password = _get(values, "password")

    if not url:
        return {"error": "Missing URL. Set the URL custom field to your Wallabag instance."}

    try:
        tok = _token(url, client_id, client_secret, username, password)
    except RuntimeError as e:
        return {"error": str(e)}

    try:
        entries = _http(
            url.rstrip("/") + "/api/entries.json?archive=0&limit=1",
            headers={"Authorization": "Bearer " + tok},
        )
    except RuntimeError as e:
        return {"error": str(e)}

    unread = int(entries.get("total", 0))
    return {"unread": unread}


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload)))
