"""Generate compact 64px plugin icons for Liquid templates and marketplace art."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# The glyphs are deliberately simple: they remain legible when Liquid renders
# them at 16–32px, while the color versions add enough identity for listings.
PLUGINS = {
    "adguard-home": ("shield", "#67B279", "AdGuard"),
    "audiobookshelf": ("headphones", "#E58B4B", "Audiobookshelf"),
    "backrest": ("backup", "#6C8FD8", "Backrest"),
    "boardgamegeek": ("dice", "#D28A42", "BoardGameGeek"),
    "booklore": ("book", "#8E6CC6", "Booklore"),
    "coming-soon": ("calendar", "#DB6B76", "Coming Soon"),
    "forgejo": ("forge", "#F07C37", "Forgejo"),
    "freshrss": ("rss", "#F29A38", "FreshRSS"),
    "immich": ("camera", "#A47BE8", "Immich"),
    "immich-stats": ("chart", "#7F62C4", "Immich Stats"),
    "jellyfin-now-playing": ("film", "#61A5D9", "Jellyfin"),
    "jellystat": ("chart", "#4D93C8", "Jellystat"),
    "mealie": ("plate", "#E16A4E", "Mealie"),
    "nginx-proxy-manager": ("proxy", "#35A8A1", "Nginx Proxy Manager"),
    "opencode-limits": ("gauge", "#D06D92", "OpenCode Limits"),
    "opencode-usage": ("terminal", "#7B7FE1", "OpenCode Usage"),
    "scrutiny": ("disk", "#5B9B91", "Scrutiny"),
    "uptime-kuma": ("heartbeat", "#60B88C", "Uptime Kuma"),
    "wallabag": ("bookmark", "#8E9B45", "Wallabag"),
}


def glyph(kind: str, stroke: str) -> str:
    common = f'fill="none" stroke="{stroke}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"'
    shapes = {
        "shield": '<path d="M32 8l18 7v14c0 13-8 22-18 27-10-5-18-14-18-27V15z"/><path d="M22 31l7 7 14-15"/>',
        "headphones": '<path d="M13 34V29a19 19 0 0 1 38 0v5"/><path d="M13 34h8v13h-5a3 3 0 0 1-3-3zM51 34h-8v13h5a3 3 0 0 0 3-3z"/>',
        "backup": '<ellipse cx="32" cy="17" rx="18" ry="7"/><path d="M14 17v15c0 4 8 7 18 7s18-3 18-7V17M14 32v15c0 4 8 7 18 7s18-3 18-7V32"/>',
        "dice": '<rect x="13" y="13" width="38" height="38" rx="7"/><circle cx="24" cy="24" r="2" fill="STROKE" stroke="none"/><circle cx="40" cy="40" r="2" fill="STROKE" stroke="none"/><circle cx="32" cy="32" r="2" fill="STROKE" stroke="none"/><circle cx="40" cy="24" r="2" fill="STROKE" stroke="none"/><circle cx="24" cy="40" r="2" fill="STROKE" stroke="none"/>',
        "book": '<path d="M12 14c7-3 14-2 20 2 6-4 13-5 20-2v35c-7-3-14-2-20 2-6-4-13-5-20-2z"/><path d="M32 16v35"/>',
        "calendar": '<rect x="12" y="14" width="40" height="38" rx="5"/><path d="M20 10v9M44 10v9M12 25h40"/><path d="M22 34h5M34 34h5M22 43h5"/>',
        "forge": '<path d="M18 48l13-13M36 20l8-8 8 8-8 8M31 35l-7-7 8-8"/><path d="M12 52h40"/>',
        "rss": '<path d="M15 45h.01M15 34a16 16 0 0 1 16 16M15 23a27 27 0 0 1 27 27"/><circle cx="15" cy="45" r="4" fill="STROKE" stroke="none"/>',
        "camera": '<path d="M12 22h9l4-6h14l4 6h9v27H12z"/><circle cx="32" cy="35" r="9"/><path d="M44 27h.01"/>',
        "chart": '<path d="M13 48V31M25 48V20M38 48V27M51 48V13"/><path d="M10 52h44"/>',
        "film": '<rect x="12" y="14" width="40" height="36" rx="4"/><circle cx="32" cy="32" r="8"/><path d="M18 14v36M46 14v36"/><path d="M12 22h6M46 22h6M12 42h6M46 42h6"/>',
        "plate": '<circle cx="32" cy="32" r="19"/><circle cx="32" cy="32" r="11"/><path d="M17 15v34M13 15v12M21 15v12M47 15v34"/>',
        "proxy": '<circle cx="20" cy="32" r="8"/><circle cx="44" cy="32" r="8"/><path d="M28 32h16M20 24v-7h24v7M20 40v7h24v-7"/>',
        "gauge": '<path d="M13 43a20 20 0 1 1 38 0"/><path d="M32 32l10-8M18 46h28"/><circle cx="32" cy="32" r="3" fill="STROKE" stroke="none"/>',
        "terminal": '<rect x="10" y="14" width="44" height="36" rx="5"/><path d="M19 26l7 6-7 6M31 39h12"/>',
        "disk": '<ellipse cx="32" cy="18" rx="18" ry="7"/><path d="M14 18v28c0 4 8 7 18 7s18-3 18-7V18"/><ellipse cx="32" cy="32" rx="18" ry="7" opacity=".65"/>',
        "heartbeat": '<path d="M10 34h10l5-15 9 27 6-18 4 6h10"/>',
        "bookmark": '<path d="M18 12h28v40L32 42 18 52z"/>',
    }
    return shapes[kind].replace("STROKE", stroke)


def icon(kind: str, accent: str, label: str, color: bool) -> str:
    bg = accent if color else "#FDFBF5"
    fg = "#FFFFFF" if color else "#0B0B0C"
    border = accent if color else "#0B0B0C"
    subtitle = label.upper()[:18]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-label="{label}">
  <rect x="1" y="1" width="62" height="62" rx="13" fill="{bg}" stroke="{border}" stroke-width="2"/>
  <g>{glyph(kind, fg)}</g>
  <path d="M10 56h44" stroke="{fg}" stroke-width="1" opacity=".25"/>
  <text x="32" y="61" text-anchor="middle" font-family="ui-monospace,monospace" font-size="4.3" font-weight="700" letter-spacing=".55" fill="{fg}">{subtitle}</text>
</svg>
'''


def main() -> None:
    for name, (kind, accent, label) in PLUGINS.items():
        folder = ROOT / "plugins" / name
        (folder / "icon-mono.svg").write_text(icon(kind, accent, label, False))
        (folder / "icon-color.svg").write_text(icon(kind, accent, label, True))


if __name__ == "__main__":
    main()
