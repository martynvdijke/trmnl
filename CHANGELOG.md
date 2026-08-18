# 1.0.0 (2026-08-18)


### Features

* consolidate TRMNL plugins into monorepo ([534635d](https://github.com/martynvdijke/trmnl/commit/534635d2cb3c67b90807fff2e20006eaa3433928))

# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- Monorepo consolidating the standalone `trmnl-immich`, `trmnl-mealie`,
  `trmnl-opencode`, and `trmnl-immich-stats` repositories.
- Plugins moved to `plugins/` with per-plugin directories:
  `immich`, `immich-stats`, `mealie`, `opencode-usage`, `opencode-limits`.
- Merged CI/CD: Go tests, Python transform tests, TRMNL plugin lint/push
  loops, semantic-release with Docker + GHCR publishing, gotify
  notifications, and OpenTelemetry export.

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
