import json
import sys
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError
from urllib.parse import quote


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
            return resp.read().decode("utf-8")
    except (URLError, HTTPError) as e:
        raise RuntimeError("request failed: %s" % e)


def _login(url, username, password):
    body = (
        "email=%s&password=%s" % (quote(username), quote(password))
    ).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    text = _http(
        url.rstrip("/") + "/api/greader.php/accounts/ClientLogin",
        headers=headers,
        data=body,
        method="POST",
    )
    token = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Auth="):
            token = line[len("Auth="):]
            break
        if line.startswith("SID="):
            token = line[len("SID="):]
    if not token:
        raise RuntimeError("login failed: no auth token returned")
    return token


def run(input):
    values = input.get("trmnl", {}).get("plugin_settings", {}).get("custom_fields_values", {})
    url = _get(values, "url")
    username = _get(values, "username")
    password = _get(values, "password")

    if not url:
        return {"error": "Missing URL. Set the URL custom field to your FreshRSS instance."}

    try:
        token = _login(url, username, password)
    except RuntimeError as e:
        return {"error": str(e)}

    try:
        raw = _http(
            url.rstrip("/") + "/api/greader.php/reader/api/0/unread-count",
            headers={"Authorization": "GoogleLogin auth=" + token},
        )
    except RuntimeError as e:
        return {"error": str(e)}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "invalid response from FreshRSS"}

    counts = data.get("unreadcounts", [])
    unread = sum(int(c.get("count", 0)) for c in counts)
    return {"unread": unread, "feeds": len(counts)}


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload)))
