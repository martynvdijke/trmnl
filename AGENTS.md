# AGENTS.md — TRMNL plugins (`github.com/martynvdijke/trmnl`)

Operational notes for AI agents working in this repo.

## Preview / serve
The TRMNL CLI (`trmnlp`) is available as the Docker image `trmnl/trmnlp`
(no local binary needed — `go install` from GitHub and the npm package are
both unavailable, but Docker Hub is reachable). Serve a plugin on port 4567:

```bash
# 1) Serve trmnl on 4568 (keep 4567 free for the proxy below)
docker run -d --name trmnl-preview -p 4568:4567 \
  --volume "$(pwd)/plugins/<name>:/plugin" \
  trmnl/trmnlp serve --bind 0.0.0.0

# 2) Local reverse proxy on 4567 → 127.0.0.1:4568 (strips X-Forwarded-*,
#    forces Host: 127.0.0.1 so Sinatra's Rack::Protection::HostAuthorization
#    accepts the request)
python3 scripts/trmnl-proxy.py
```

- Local: http://localhost:4567 (proxy) → http://localhost:4568 (trmnl). `/` redirects to `/full` (renders 200).
- **On this homelab box the serve is exposed at https://trmnlp.vandijke.xyz/**
  — Nginx Proxy Manager forwards that domain to port 4567 (upstream
  `192.168.3.1:4567`), which is the local `scripts/trmnl-proxy.py` reverse
  proxy. It sits behind **Authelia SSO**, so authenticated sessions pass
  through; unauthenticated requests get `403 Forbidden` (expected — verify the
  upstream with `curl http://192.168.3.1:4567/full` from the `nginx` container,
  which returns 200). Log in to the homelab SSO in a browser to preview.
- **Why the proxy is required:** the trmnl serve container (Sinatra/Rack)
  enforces `Rack::Protection::HostAuthorization`. Through NPM it receives
  `Host`/`X-Forwarded-Host` = the public domain and `X-Forwarded-For` = the
  public client IP, so Rack treats the client as untrusted and rejects the host
  mismatch ("Host not permitted"). The proxy normalizes the request to a trusted
  loopback client (`Host: 127.0.0.1`, no `X-Forwarded-*`) before reaching trmnl.
  Do NOT point NPM directly at the trmnl container — it will 403.
- Switch the served plugin: `docker rm -f trmnl-preview` and re-run step 1 with
  a different `--volume` path (the proxy keeps running).

## Push to TRMNL
`scripts/push-new.sh` is Docker-aware and idempotent. It pushes each new plugin
**without an `id:`** (so TRMNL assigns a fresh ID), captures the returned ID from
the push output, and writes it back into `src/settings.yml` and the README table.

```bash
export TRMNL_API_KEY=...   # the TRMNL API token — no trailing '#'
bash scripts/push-new.sh
```

Re-running skips plugins that already have a real ID. Known push constraints:
descriptions ≤ 35 chars, author-bio `category` must be a TRMNL-approved value
(`entertainment` is used repo-wide).

## Plugin structure
Each plugin = `plugins/<name>/` with:
- `.trmnlp.yml` (watch list + `transform_runtime: enabled`)
- `src/settings.yml` (full `oauth_*` block required — copy an existing plugin)
- `src/transform.py` (stdlib only; reads
  `input['trmnl']['plugin_settings']['custom_fields_values']`; returns
  `{'error': ...}` when the URL is missing)
- 4 liquids: `full` / `half_horizontal` / `half_vertical` / `quadrant`
- `tests/test_<name>_transform.py` (importlib-loads transform.py, monkeypatches
  `urllib.request.urlopen`; the mock must be a context manager and read
  `getattr(url, 'full_url', str(url))` for the request URL)

Reference plugins: `jellyfin-now-playing` (poster + progress bar),
`jellystat` (stats style), `adguard-home` (HTTP Basic), `nginx-proxy-manager`
(login + Bearer), `freshrss` (ClientLogin), `wallabag` (OAuth2).

## Tests
```bash
python3 tests/test_<name>_transform.py
```
(LSP "ModuleSpec | None" errors in test files are a known false positive.)
