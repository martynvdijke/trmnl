## [1.3.1](https://github.com/martynvdijke/trmnl/compare/v1.3.0...v1.3.1) (2026-08-20)


### Bug Fixes

* make opencode-usage general (restore url field) ([8341e8b](https://github.com/martynvdijke/trmnl/commit/8341e8bc86829dad1f37871ca90ac91a169974b6))

# [1.3.0](https://github.com/martynvdijke/trmnl/compare/v1.2.1...v1.3.0) (2026-08-20)


### Bug Fixes

* unblock CI (opencode Usage + TRMNL lint) and add e-ink logo ([40398e9](https://github.com/martynvdijke/trmnl/commit/40398e99c6b382dacecb6a67b425a992d084683f))


### Features

* add BoardGameGeek plugin and fix OpenCode Usage server default ([16f6cd0](https://github.com/martynvdijke/trmnl/commit/16f6cd0a85b51489fa3d15b5c1681c1c3fe45d3f))

## [1.2.1](https://github.com/martynvdijke/trmnl/compare/v1.2.0...v1.2.1) (2026-08-20)


### Bug Fixes

* handle concurrent preview requests ([5128ede](https://github.com/martynvdijke/trmnl/commit/5128ede01d38b1d543ce3fe0069d4a6781933ffb))

# [1.2.0](https://github.com/martynvdijke/trmnl/compare/v1.1.0...v1.2.0) (2026-08-20)


### Features

* add 13 TRMNL plugins with push automation and serve proxy ([86b2e73](https://github.com/martynvdijke/trmnl/commit/86b2e739d339ca4a0c7871abe2a3121f0ab94a26))

# [1.1.0](https://github.com/martynvdijke/trmnl/compare/v1.0.2...v1.1.0) (2026-08-18)


### Features

* add OpenCode usage graph ([5dc37f2](https://github.com/martynvdijke/trmnl/commit/5dc37f2f8cb908c169c4d33051a36521931a9651))

## [1.0.2](https://github.com/martynvdijke/trmnl/compare/v1.0.1...v1.0.2) (2026-08-18)


### Bug Fixes

* improve OpenCode limits layouts ([0667837](https://github.com/martynvdijke/trmnl/commit/066783781685b894191be8b2b165eafc37c9c317))

## [1.0.1](https://github.com/martynvdijke/trmnl/compare/v1.0.0...v1.0.1) (2026-08-18)


### Bug Fixes

* drop docker image publishing from release pipeline ([128c449](https://github.com/martynvdijke/trmnl/commit/128c44920eddd5e0bb2f62fe8a32739790154616))

# 1.0.0 (2026-08-18)


### Features

* consolidate TRMNL plugins into monorepo ([534635d](https://github.com/martynvdijke/trmnl/commit/534635d2cb3c67b90807fff2e20006eaa3433928))

# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- New media/homelab plugins that call their respective APIs directly (IDs are
  assigned on first push via `scripts/push-new.sh`):
  - Media/visual: `jellyfin-now-playing`, `jellystat`, `coming-soon` (Sonarr +
    Radarr), `audiobookshelf` (currently listening), `booklore` (reading +
    library size)
  - Homelab health: `adguard-home`, `uptime-kuma`, `scrutiny` (disk SMART),
    `backrest` (last backup), `nginx-proxy-manager` (cert expiry), `forgejo`
    (PRs/issues + CI), `freshrss` (unread), `wallabag` (unread)
  Each ships with `.trmnlp.yml`, `src/settings.yml`, `transform.py`, four
  Liquid views, and a transform unit test.
- `opencode-usage` now renders a weekly tokens + cost graph (two Highcharts
  spline series) alongside the existing 30-day cost and session views.
- Plugins moved to `plugins/` with per-plugin directories:
  `immich`, `immich-stats`, `mealie`, `opencode-usage`, `opencode-limits`.
- Merged CI/CD: Go tests, Python transform tests, TRMNL plugin lint/push
  loops, semantic-release, gotify notifications, and OpenTelemetry export.
- Dropped Docker image publishing from the release pipeline (middleware runs
  directly via `task run` / `go run`).

### Changed

- `immich-stats` now uses the canonical implementation previously living in
  `trmnl-immich` (hardened transform error handling, `layout--stretch`).
- All plugin settings use `framework_version: latest` and include an
  `author_bio` custom field pointing at this repository.
- All plugin layouts gained responsive `lg:` / `portrait:` classes for the
  TRMNL X display and form-field help texts no longer embed plain-text URLs.
- Go module path changed to `github.com/martynvdijke/trmnl`.

### Removed

- Standalone repositories `trmnl-immich`, `trmnl-mealie`, `trmnl-opencode`,
  and `trmnl-immich-stats` were archived in favor of this monorepo.
