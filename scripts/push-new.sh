#!/usr/bin/env bash
#
# Bootstrap new TRMNL plugins: push WITHOUT an id so TRMNL creates a fresh
# plugin, capture the returned plugin ID from the push output, and write it
# back into src/settings.yml. Idempotent: plugins that already have a real
# id are skipped, so re-running never creates duplicates.
#
# Prerequisites:
#   - `trmnlp` CLI on PATH (go install github.com/TRMNL-Studio/trmnlp@latest)
#     OR Docker (the trmnl/trmnlp container is used automatically)
#   - TRMNL_API_KEY exported (your TRMNL developer token)
#
# Usage:
#   export TRMNL_API_KEY=your_token
#   bash scripts/push-new.sh
#
set -uo pipefail

if command -v trmnlp >/dev/null 2>&1; then
  TRMNL_BIN=trmnlp
elif command -v docker >/dev/null 2>&1; then
  TRMNL_BIN=docker
else
  echo "ERROR: neither 'trmnlp' nor 'docker' is available." >&2
  echo "  Install trmnlp: go install github.com/TRMNL-Studio/trmnlp@latest" >&2
  echo "  or install Docker and use the trmnl/trmnlp container." >&2
  exit 1
fi

if [ -z "${TRMNL_API_KEY:-}" ]; then
  echo "ERROR: TRMNL_API_KEY is not set. Export it first:" >&2
  echo "  export TRMNL_API_KEY=your_token" >&2
  exit 1
fi

# New plugins to bootstrap (no real id yet). Existing plugins (immich, mealie,
# opencode-*, etc.) already have ids and are skipped automatically.
PLUGINS=(
  jellyfin-now-playing
  jellystat
  adguard-home
  uptime-kuma
  coming-soon
  scrutiny
  backrest
  audiobookshelf
  forgejo
  nginx-proxy-manager
  freshrss
  wallabag
  booklore
)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

push_plugin() {
  # Push a plugin dir, returning the command output on stdout. Never fails the
  # script (we inspect the output to decide success).
  local dir="$1"
  if [ "$TRMNL_BIN" = "docker" ]; then
    docker run --rm --volume "$dir:/plugin" -e "TRMNL_API_KEY=$TRMNL_API_KEY" \
      trmnl/trmnlp push --force --dir /plugin 2>&1 || true
  else
    trmnlp push --force --dir "$dir" 2>&1 || true
  fi
}

current_id() {
  # Print the top-level `id:` value, or empty if absent.
  grep -E '^[[:space:]]*id:' "$1" 2>/dev/null | head -1 | sed -E 's/.*:[[:space:]]*//' | tr -d '"'"'"' '
}

update_readme() {
  # Replace the ID cell in README.md for the plugin's table row.
  local name="$1" new_id="$2"
  local readme="$ROOT/README.md"
  [ -f "$readme" ] || return 0
  python3 - "$readme" "$name" "$new_id" <<'PY'
import sys, re
path, name, new_id = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f:
    lines = f.readlines()
pat = re.compile(r'^(.*\| \[' + re.escape(name) + r'\]\(plugins/' + re.escape(name) + r'\) \|)[^|]*(\|.*)$')
out = []
changed = False
for ln in lines:
    m = pat.match(ln.rstrip("\n"))
    if m:
        ln = m.group(1) + " " + new_id + " " + m.group(2) + "\n"
        changed = True
    out.append(ln)
with open(path, "w") as f:
    f.writelines(out)
if changed:
    print("      updated README row for %s -> %s" % (name, new_id))
PY
}

for name in "${PLUGINS[@]}"; do
  dir="$ROOT/plugins/$name"
  file="$dir/src/settings.yml"

  if [ ! -f "$file" ]; then
    echo "SKIP  $name: $file not found" >&2
    continue
  fi

  id="$(current_id "$file")"
  if [ -n "$id" ]; then
    echo "SKIP  $name: already has id $id"
    continue
  fi

  # Ensure no id line is present (strip it if somehow still there).
  grep -vE '^[[:space:]]*id:' "$file" > "$file.tmp" && mv "$file.tmp" "$file"

  echo "==> Pushing $name (without id) via $TRMNL_BIN..."
  output="$(push_plugin "$dir")"
  echo "$output"

  new_id="$(printf '%s\n' "$output" | grep -oE '/plugin_settings/[0-9]+/edit' | grep -oE '[0-9]+' | tail -1)"

  if [ -z "$new_id" ]; then
    echo "ERROR: could not extract a new plugin ID for '$name' from the push output." >&2
    echo "       Check the TRMNL dashboard; the plugin may have been created." >&2
    echo "       Skipping '$name' and continuing with the rest." >&2
    continue
  fi

  # Write the captured id back as the first line of settings.yml.
  printf 'id: %s\n' "$new_id" | cat - "$file" > "$file.tmp" && mv "$file.tmp" "$file"

  update_readme "$name" "$new_id"

  echo "OK    $name -> id $new_id"
done

echo
echo "All new plugins pushed and their IDs written back into src/settings.yml."
echo "Commit the changes so future 'trmnlp push' calls update these plugins."
