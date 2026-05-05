---
slug: tree-vertical-fill
status: complete
date: 2026-05-05
---

# Tree pages — content fills vertical gap

## Problem

After compacting the header to `py-2` and removing the navbar block, the `.tree-explorer-container`'s inline `min-height: calc(85vh - 110px)` no longer matched the actual layout. Result: a large gray gap between the bottom of the white tree/detail panels and the page footer.

Two contributing causes:
1. The `85vh - 110px` calc was calibrated for the *old* taller header (`py-6` + `text-3xl` + a navbar bar). With the new layout, that value undershoots significantly.
2. `<main>`'s `py-4` (from base.html) added 16px above and below — the top half was already overridden via `padding-top: 0 !important`; bottom half was not.

## Fix

- Replaced `calc(85vh - 110px)` → `calc(100vh - 124px)` (and the no-space `85vh-110px` → `100vh-124px`) across all three tree templates. The 124px = header (58px) + footer (65px) + 1px slack.
- Extended the `main` padding override to also kill `padding-bottom`:
  ```css
  main { padding-top: 0 !important; padding-bottom: 0 !important; }
  ```

## Verification

JS-measured gap between `.tree-explorer-container` bottom and `<footer>` top: **1px** (sub-pixel rounding, visually flush). Confirmed via chrome-devtools screenshot.

## Files touched

- `folio_api/templates/jinja2/explore/tree.html`
- `folio_api/templates/jinja2/properties/tree.html`
- `folio_api/templates/jinja2/taxonomy/tree.html`
