<p align="center">
  <img src="assets/logo.svg" width="220" alt="TRMNL monorepo logo — e-ink device with plugin grid"/>
</p>

# trmnl

Custom TRMNL plugins and the Immich photo proxy middleware, consolidated into a single monorepo.

## Plugins

| Plugin | TRMNL ID | Description |
| --- | --- | --- |
| [immich](plugins/immich) | 444098 | Photo of the Day — a random photo from your Immich library |
| [immich-stats](plugins/immich-stats) | 443892 | Immich storage and server statistics |
| [mealie](plugins/mealie) | 443871 | Recipe of the Day — a random recipe from your Mealie instance |
| [opencode-usage](plugins/opencode-usage) | 444114 | OpenCode usage and token spend from an OpenCode server |
| [opencode-limits](plugins/opencode-limits) | 444197 | OpenCode Go usage limits |
| [jellyfin-now-playing](plugins/jellyfin-now-playing) | 450296 | What is currently streaming on your Jellyfin, with poster art |
| [jellystat](plugins/jellystat) | 450299 | Jellyfin watch time and top shows from Jellystat |
| [adguard-home](plugins/adguard-home) | 450311 | AdGuard Home query and blocking statistics |
| [uptime-kuma](plugins/uptime-kuma) | 450312 | Uptime Kuma monitor status from a public status page |
| [coming-soon](plugins/coming-soon) | 450302 | Upcoming Sonarr and Radarr releases with poster art |
| [scrutiny](plugins/scrutiny) | 450313 | Disk health and SMART status from Scrutiny |
| [backrest](plugins/backrest) | 450314 | Last restic backup time and status from Backrest |
| [audiobookshelf](plugins/audiobookshelf) | 450305 | Currently listening progress from Audiobookshelf |
| [boardgamegeek](plugins/boardgamegeek) |  | Latest plays & a game you own |
| [forgejo](plugins/forgejo) | 450315 | Open PRs, issues, and CI status from Forgejo |
| [nginx-proxy-manager](plugins/nginx-proxy-manager) | 450316 | TLS certificate expiry from Nginx Proxy Manager |
| [freshrss](plugins/freshrss) | 450308 | Unread article count from FreshRSS |
| [wallabag](plugins/wallabag) | 450309 | Unread article count from Wallabag |
| [booklore](plugins/booklore) | 450310 | Reading progress and library size from Booklore |
| [home-assistant](plugins/home-assistant) |  | Home Assistant entity summary |
| [paperless-ngx](plugins/paperless-ngx) |  | Paperless inbox and library |
| [changedetection](plugins/changedetection) |  | Website change monitoring |

Each plugin lives in `plugins/<name>/` with its own `.trmnlp.yml` and `src/`
(`settings.yml`, `transform.py`, and one `.liquid` view per display size).
The TRMNL plugin ID is pinned in `src/settings.yml`, so pushes update the
existing plugin instead of creating new ones. New plugins start without an ID;
run `bash scripts/push-new.sh` (with `TRMNL_API_KEY` exported) to push them
for the first time, capture the assigned IDs, and write them back into both
`src/settings.yml` and this table.

## Immich photo proxy middleware

`main.go` is a small Go service that proxies Immich thumbnails to TRMNL
devices:

- `GET /healthz` — health check
- `GET /api/trmnl/photo/{id}` — proxies `{IMMICH_URL}/api/assets/{id}/thumbnail?size=preview`
  with the configured API key, caches for 24h

Configure via env vars: `IMMICH_URL`, `IMMICH_API_KEY`, `PORT` (default `8080`).

```bash
task setup     # go mod download
task dev       # run with air (auto-reload)
task build     # go build
task run       # go run .
task test      # go test ./...
```

No Docker images are published — run the middleware directly (e.g. as a
systemd service or your scheduler of choice).

## Development

- Lint the plugins: `trmnlp lint --dir plugins/<name>` for each plugin
  (or `for d in plugins/*/; do trmnlp lint --dir "$d"; done`)
- Push a plugin to TRMNL: `TRMNL_API_KEY=... trmnlp push --force --dir plugins/<name>`
- Bootstrap new plugins (first push without IDs, then capture + write back):
  `export TRMNL_API_KEY=... && bash scripts/push-new.sh`
- Preview a plugin locally: `trml --serve --dir plugins/<name>`
  (or, with no local install, via the official container). On this homelab box
  the serve is exposed at **https://trmnlp.vandijke.xyz/** through Nginx Proxy
  Manager → a local reverse proxy (`scripts/trmnl-proxy.py`) → the trmnl
  container. The proxy is required because trmnl's Sinatra/Rack
  `HostAuthorization` rejects NPM's public-domain `Host`/`X-Forwarded-For`.
  Serve with:
  ```bash
  docker run -d --name trmnl-preview -p 4568:4567 \
    --volume "$(pwd)/plugins/<name>:/plugin" \
    trmnl/trmnlp serve --bind 0.0.0.0
  python3 scripts/trmnl-proxy.py   # listens on :4567, forwards to 127.0.0.1:4568
  ```
  It sits behind **Authelia SSO**, so authenticated sessions pass through and
  unauthenticated requests get `403 Forbidden` (expected). Log in to the homelab
  SSO in your browser to preview at https://trmnlp.vandijke.xyz/.
- Push via Docker (instead of installing the binary):
  ```bash
  docker run --rm --volume "$(pwd)/plugins/<name>:/plugin" \
    -e TRMNL_API_KEY=... trmnl/trmnlp push --force --dir /plugin
  ```
  `scripts/push-new.sh` auto-detects Docker and uses the container when the
  `trmnlp` binary is not on your PATH.
- Python transforms: `python3 tests/test_transform.py && python3 tests/test_limits_transform.py`

## CI/CD

- `ci.yaml` — Go vet/test + Python transform tests on PRs and non-main pushes
- `trml.yaml` — lints all plugins on PRs; pushes all plugins on main
- `release.yaml` — semantic-release, TRMNL plugin push, gotify notifications, OpenTelemetry export
- `stale-branches.yml` — daily stale branch cleanup
- Renovate keeps actions, Go, and dependencies up to date
