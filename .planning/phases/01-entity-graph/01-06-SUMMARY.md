---
phase: 01-entity-graph
plan: 06
subsystem: frontend
tags: [frontend, ui-states, skeleton, empty-state, error-state, heroicons, accessibility]
requirements: [GRAPH-18, GRAPH-19, GRAPH-20]
dependency-graph:
  requires:
    - "01-03 (entity_graph.js IIFE skeleton + window.EntityGraph export)"
    - "01-05 (creates #entity-graph-pane host element — used by these renderers)"
  provides:
    - "EntityGraph.showEmpty() — renders centered hint into #entity-graph-pane"
    - "EntityGraph.showSkeleton() — renders 4 stacked animate-pulse rectangles, sets aria-busy"
    - "EntityGraph.showError(label, onRetry) — renders red-tint alert with wired Retry button"
    - "EntityGraph.clearStates() — empties pane, removes aria-busy"
    - "EntityGraph.ICONS — { tag, link, arrowsPointingOut, xMark, arrowPath, share } verbatim Heroicons v2 outline SVG strings"
    - "@media (prefers-reduced-motion: reduce) skeleton override"
  affects:
    - "01-09 (will reuse ICONS.tag and ICONS.link for node icons)"
    - "01-12 (will call showSkeleton → fetch → showError on failure)"
    - "01-13 (will reuse ICONS.arrowsPointingOut + ICONS.xMark for fullscreen toggle/close)"
tech-stack:
  added: []
  patterns:
    - "Inline Heroicons v2 outline SVG (no asset fetch, CSP-friendly per D-19)"
    - "Tailwind utility classes for layout + colors (project convention)"
    - "Tailwind animate-pulse for skeleton motion; CSS @media override for accessibility"
    - "textContent (not innerHTML) for user-derived strings (XSS mitigation)"
key-files:
  created: []
  modified:
    - "folio_api/static/js/entity_graph.js (+115 lines: ICONS const, showEmpty, showSkeleton, showError, clearStates, export updates)"
    - "folio_api/static/css/styles.css (+21 lines: .entity-graph-skeleton class + prefers-reduced-motion override)"
decisions:
  - "Inlined Heroicons SVG markup as JS string constants rather than separate assets — follows D-19 / UI-SPEC §Iconography (zero CSP img-src complications, zero extra HTTP)"
  - "Used Tailwind animate-pulse instead of custom @keyframes — Tailwind already ships the keyframe; project uses Tailwind utilities throughout (consistency with unified_tree.js)"
  - "Used textContent for the entity label inside showError per RESEARCH.md Security Domain row 2 / threat T-1-W1-04 mitigation"
  - "Used ES5-style string concatenation (no template literals) to match existing entity_graph.js / unified_tree.js conventions"
  - "Used Unicode right-single-quote (U+2019) in copy strings (\"Couldn't load graph\") per UI-SPEC §Copywriting — avoids HTML-escape concerns inside JS literals"
metrics:
  duration: "~7 minutes"
  completed: "2026-05-06"
  tasks_completed: 2
  files_modified: 2
  lines_added: 136
---

# Phase 1 Plan 6: UI State Renderers + Heroicons Summary

State renderers (empty / skeleton / error) and verbatim Heroicons v2 outline SVG constants are now exposed on `window.EntityGraph`, ready for Plan 12 to drive the fetch lifecycle.

## What Was Built

### entity_graph.js (commit 63cabcb)

Added inside the existing IIFE, before the lazy-ELK loader:

- **`ICONS` constant** — six Heroicons v2 outline SVG strings, verbatim from `tailwindlabs/heroicons` (verified 2026-05-05):
  - `tag` (w-4 h-4) — `M9.568 3H5.25A2.25 2.25 0 0 0 3 …`
  - `link` (w-4 h-4) — `M13.19 8.688a4.5 4.5 0 0 1 1.242 …`
  - `arrowsPointingOut` (w-5 h-5) — `M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 …`
  - `xMark` (w-5 h-5) — `M6 18 L18 6M6 6l12 12`
  - `arrowPath` (w-4 h-4) — `M16.023 9.348h4.992v-.001M2.985 19.644…`
  - `share` (w-16 h-16) — `M7.217 10.907a2.25 2.25 0 1 0 0 2.186…`
- **`_svg(sizeClass, pathsHtml)` / `_path(d)`** — internal helpers that emit the SVG wrapper (xmlns, viewBox, stroke, aria-hidden) and `<path stroke-linecap="round" …>` markup.
- **`showEmpty()`** — renders centered share icon + heading "No entity selected" + body "Select an entity in the tree to see its graph." (UI-SPEC Copywriting Contract verbatim).
- **`showSkeleton()`** — sets `aria-busy="true"` on the pane and renders four stacked `bg-gray-100 rounded h-8` rectangles (widths w-48, w-56, w-48, w-44) each carrying Tailwind `animate-pulse`. Includes `<span class="sr-only">Loading entity graph…</span>` and `role="status" aria-live="polite"` for the screen-reader contract.
- **`showError(entityLabel, onRetry)`** — renders `bg-red-50 border border-red-200 rounded-lg` alert box with heading "Couldn't load graph" (Unicode right-single-quote), body "Couldn't load graph for {label}. The server returned an error." (set via `textContent` for XSS), and a Retry button (`bg-blue-50 …`) carrying the `arrowPath` icon. `onRetry` is wired to the click event when callable.
- **`clearStates()`** — empties pane innerHTML and removes `aria-busy`.

The `window.EntityGraph` export now also exposes `showEmpty`, `showSkeleton`, `showError`, `clearStates`, `ICONS` (alongside the existing `init`, `loadELK`, `refreshFor`, `expand`, `close`, `toggleFullscreen`, `state`).

### styles.css (commit f6ee8cb)

Appended at the end of the file:

- `.entity-graph-skeleton` marker class (no properties — only a hook for the media query).
- `@media (prefers-reduced-motion: reduce)` rule overriding `.entity-graph-skeleton .animate-pulse` to `animation: none !important; opacity: 0.7;` — Tailwind's animate-pulse is fully suppressed and rectangles remain visible but static, matching UI-SPEC §Motion contract.

No existing rules were modified; the diff shows additions only.

## Verification

```
node --check folio_api/static/js/entity_graph.js          → exit 0
grep -c "function show" entity_graph.js                   → 3 (showEmpty, showSkeleton, showError)
grep -c "M13.19 8.688" entity_graph.js                    → 1
grep -c "animate-pulse" entity_graph.js                   → 4 (one per skeleton rect)
grep -c "entity-graph-skeleton" styles.css                → 2 (class def + media-query selector)
grep -c "prefers-reduced-motion: reduce" styles.css       → 1
```

All acceptance criteria for both tasks pass.

### Manual UAT (planned — not executed in this worktree)

A live `/explore/tree` is not available inside the parallel worktree (Plan 05 has not yet wired `#entity-graph-pane` to the tab UI; that lands in this same wave). Manual UAT for Plan 6 will be done in the merged main once Plan 5 lands:

1. Open `/explore/tree`, devtools console.
2. `EntityGraph.showEmpty()` → centered share icon + "No entity selected" hint.
3. `EntityGraph.showSkeleton()` → 4 pulsing grey rectangles; pane has `aria-busy="true"`.
4. `EntityGraph.showError('Court', () => alert('retry'))` → red-tint alert with body referencing "Court"; clicking Retry fires the alert.
5. `EntityGraph.clearStates()` → pane is empty, `aria-busy` removed.
6. In OS settings, enable "Reduce motion"; reload; call `showSkeleton()` → rectangles visible at opacity 0.7, no pulse.

## Deviations from Plan

None — plan executed exactly as written. Both tasks landed verbatim against the plan's `<action>` block.

## Compliance Notes

- **GRAPH-18 (empty hint):** Verbatim copy + 64×64 share icon, `gap-6` centered flex column. Matches UI-SPEC State Inventory and Copywriting Contract.
- **GRAPH-19 (skeleton):** 4 rectangles, Tailwind `animate-pulse` (1500 ms), `aria-busy="true"`, `role="status"` + `aria-live="polite"` + sr-only label. Matches UI-SPEC accessibility contract.
- **GRAPH-20 (error + retry):** `role="alert"`, red-tinted box with verbatim copy, focusable Retry button with focus-visible ring. `onRetry` callback wired via `addEventListener`.
- **D-19 (no asset fetch):** All Heroicons inlined as JS string constants; zero new HTTP requests, no CSP `img-src` impact.
- **D-27/D-28/D-29 (state UX):** Empty / loading / error all implemented per CONTEXT decisions.
- **Threat T-1-W1-04 (XSS via entity label):** Mitigated — label set via `textContent` on a pre-built `<p>` element. The plan's threat register entry is honored.
- **Threat T-1-W1-05 (info disclosure via console.error):** Accepted — labels are public ontology identifiers.
- **Threat T-1-W1-06 (SVG path tampering):** Mitigated — paths are static module constants.

## Known Stubs

None. All three render methods emit complete UI from supplied parameters; nothing is hardcoded to empty/null/placeholder values that flow to user-visible output.

## Self-Check: PASSED

- File: `folio_api/static/js/entity_graph.js` — present, parses with `node --check`.
- File: `folio_api/static/css/styles.css` — present, appended block visible at tail.
- Commit `63cabcb` — present in `git log` (Task 1: ICONS + state renderers).
- Commit `f6ee8cb` — present in `git log` (Task 2: CSS state styles + reduced-motion).
