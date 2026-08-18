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

Each plugin lives in `plugins/<name>/` with its own `.trmnlp.yml` and `src/`
(`settings.yml`, `transform.py`, and one `.liquid` view per display size).
The TRMNL plugin ID is pinned in `src/settings.yml`, so pushes update the
existing plugin instead of creating new ones.

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

Docker: `docker compose up -d` (image `martynvandijke/trmnl-immich`).

## Development

- Lint the plugins: `trmnlp lint --dir plugins/<name>` for each plugin
  (or `for d in plugins/*/; do trmnlp lint --dir "$d"; done`)
- Push a plugin to TRMNL: `TRMNL_API_KEY=... trmnlp push --force --dir plugins/<name>`
- Python transforms: `python3 tests/test_transform.py && python3 tests/test_limits_transform.py`

## CI/CD

- `ci.yaml` — Go vet/test + Python transform tests on PRs and non-main pushes
- `trml.yaml` — lints all plugins on PRs; pushes all plugins on main
- `release.yaml` — semantic-release, Docker image build/push, TRMNL plugin
  push, gotify notifications, OpenTelemetry export
- `stale-branches.yml` — daily stale branch cleanup
- Renovate keeps actions, Go, and dependencies up to date
