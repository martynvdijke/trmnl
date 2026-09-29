# Immich Stats and Mealie Display Design

## Goal

Make Immich Stats and Mealie readable and useful on every TRMNL display size. The supplied screenshots show Mealie's ingredient and instruction text crowded into narrow regions and Immich's server metadata colliding with the bottom title area.

## Scope

Update the Liquid templates for `full`, `half_horizontal`, `half_vertical`, and `quadrant` in `plugins/immich-stats/src/` and `plugins/mealie/src/`. Keep the changes focused on layout and content density; preserve current transforms, settings, and data contracts unless template-safe formatting requires a small adjustment.

## Design

### Immich Stats

- Present photos, videos, storage, and Immich version in an aligned, balanced metric grid with values and labels that remain legible at each size.
- Keep per-user storage where the display has room, in clearly separated rows.
- Remove the crowded stack of individual server-library versions from display templates; retain a compact licensed indicator where applicable.
- Keep error states and the existing title bars readable.

### Mealie

- Make the full view a recipe card: clearly separated recipe name and key metadata, followed by readable ingredient and instruction sections.
- Bound the amount of detail shown on the full screen so long recipes cannot crowd or run into the title bar. Show a clear indication when the displayed list is shortened.
- On half-size views, prioritize the recipe name and preparation metadata; show only a small, readable subset of ingredients/details.
- On quadrant, prioritize recipe name and the most useful brief metadata; avoid dense lists.
- Preserve optional image, description, error handling, and title bar without letting them collapse the text area.

## Constraints and data flow

Use the existing TRMNL Liquid/CSS utility classes and existing transform payloads. No new API calls, custom fields, or external dependencies are needed. Templates must tolerate missing optional values and empty ingredient/instruction arrays.

## Verification

- Run `python3 tests/test_immich_stats_transform.py` and `python3 tests/test_mealie_transform.py` to ensure the unchanged data transforms still pass.
- Inspect all eight templates for consistent structure, proper error branches, and bounded content in small layouts.
- Use the local TRMNL preview when available to check that lists, metric values, and title bars do not overlap at the supported display sizes.
