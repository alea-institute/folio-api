---
phase: 01-entity-graph
plan: 09
subsystem: frontend
type: execute
wave: 2
status: complete
completed: 2026-05-06
duration_minutes: 8
tasks_completed: 2
tasks_total: 2
files_created: []
files_modified:
  - folio_api/static/js/entity_graph.js
  - folio_api/static/css/styles.css
requirements: [GRAPH-15, GRAPH-16, GRAPH-17]
tags: [frontend, css, visual-styling, heroicons]

dependency_graph:
  requires:
    - "06: ICONS const + state renderers (window.EntityGraph.ICONS)"
    - "08: renderGraph DOM scaffold (viewport > transform > svg + nodes div)"
  provides:
    - "Visually styled entity-graph nodes (icon prefix, selected glow, ROOT badge)"
    - "Edge stroke styling via .graph-edge CSS rule"
  affects:
    - "Plans 10–13 build pan/zoom + +N children + click + modal on top of these styles"

tech_stack:
  added: []
  patterns:
    - "Two-layer DOM (outer positioning DIV + inner styled wrapper) — outer holds absolute coords, inner holds Tailwind border + bg + padding"
    - "_buildTypeMap helper — one IRI→type map per render, reused for icon dispatch"
    - "textContent-on-label pattern preserved (XSS mitigation)"

key_files:
  created: []
  modified:
    - folio_api/static/js/entity_graph.js
    - folio_api/static/css/styles.css

decisions:
  - "Bind edge stroke to .graph-edge CSS, drop inline stroke attributes — keeps SVG markup terse and respects UI-SPEC color contract centrally"
  - "Use .graph-node-selected > div as the box-shadow target — the inner wrapper owns the visible border, so the outer glow visually wraps the border (not a separate ring)"
  - "_buildTypeMap reuses selected.type for ancestors per CONTEXT D-21 ('single-type chain in v1.1')"

metrics:
  duration_minutes: 8
  task_count: 2
  file_count: 2
  test_count_pre: 13
  test_count_post: 13
  test_regressions: 0
---

# Phase 1 Plan 09: Visual Styling Summary

Apply Heroicons icon prefix, selected-node glow, and ROOT-ancestor badge styling on top of the renderGraph scaffold from Plan 08 — closing GRAPH-15, GRAPH-16, GRAPH-17 of milestone v1.1.

## What was built

- **Task 1 (commit `6854605`)** — Replaced the plain DIV per-node markup in `_mountGraph` with a two-layer DOM:
  - Outer DIV: `graph-node [graph-node-selected] [graph-node-root]`, positioned absolutely with `data-iri`, cursor `pointer` (default on selected).
  - Inner DIV: `flex items-center gap-1 px-3 py-2 h-full bg-white border ${borderClass} rounded ${rootInnerClass}` carrying the visible border + padding.
  - Inner content: leading icon span (`text-gray-500 flex-shrink-0`) holding `ICONS.tag` (class) or `ICONS.link` (property) — derived via the new `_buildTypeMap` helper; label `<span class="graph-node-label …">`; optional ROOT pill (`ml-auto text-[11px] font-semibold uppercase tracking-wide text-gray-500 bg-gray-100 rounded px-1.5 py-0.5`).
  - Label classes scale by role: root → `text-base font-semibold leading-tight text-gray-900`; selected → `text-sm font-semibold text-gray-900`; default → `text-sm font-normal text-gray-700`.
  - Edge `<path>` elements now carry only `class="graph-edge"` — stroke styling moves to CSS.
  - Label text continues to be set via `textContent` on `.graph-node-label` after innerHTML assembly (XSS mitigation preserved per RESEARCH.md Security row 2 / T-1-W2-03).
- **Task 2 (commit `756dffa`)** — Appended four CSS rules to `styles.css`:
  - `.graph-edge { stroke: #9CA3AF; fill: none; stroke-width: 1.5; }` — Tailwind gray-400 / 1.5 px, exact UI-SPEC §Color value.
  - `.graph-node { transition: box-shadow 0.12s ease-out; user-select: none; }` — base layer.
  - `.graph-node-selected > div { box-shadow: 0 0 12px rgba(37, 99, 235, 0.35); }` — exact UI-SPEC §Color row-2 rgba (D-20). Targets inner wrapper so the glow hugs the visible border.
  - `@media (prefers-reduced-motion: reduce) { .graph-node { transition: none; } }` — accessibility.
  - All four rules are pure additions at end of file; `git diff --stat` confirms zero deletions.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Class nodes get tag SVG prefix; property nodes get link SVG prefix | PASS — `ICONS.tag` / `ICONS.link` selected via `_buildTypeMap[node.id]` |
| Selected node has 2px solid `border-blue-600` + outer glow box-shadow | PASS — outer class + inner `border-blue-600 border-2`; CSS adds `0 0 12px rgba(37,99,235,0.35)` |
| Topmost ancestor renders with larger/bolder text + ROOT badge | PASS — `text-base font-semibold` + ROOT pill |
| Edge stroke gray-400, 1.5 px (no inline attributes) | PASS — `.graph-edge` CSS owns stroke; renderer emits `<path class="graph-edge" d="…">` only |
| Reduced-motion override disables `.graph-node` transition | PASS — Task 2 added the @media block |
| `node --check folio_api/static/js/entity_graph.js` exits 0 | PASS |
| `uv run pytest --no-cov -q` passes 13/13 (no regression) | PASS — 13 passed, 15 warnings, 0.81 s |

## Manual verification (smoke)

The plan calls for a manual UAT on `/explore/tree`:

- Click any class entity in the tree → click the **Entity Graph** tab → expected: graph renders with `tag` icons on every node; topmost ancestor has the ROOT badge and larger label; the selected node carries a 2 px blue border + a soft outer glow.
- Click any property entity → expected: same, but with `link` icons.

(This worktree runs headless; the visual UAT is recorded as a deferred step for the verifier in the upcoming `/gsd:verify-work` stage.)

## Deviations from Plan

None. Both tasks executed exactly as specified.

The plan's `<verify>` for Task 2 mentions `grep -q "stroke: #9CA3AF"` — the appended rule uses that exact byte sequence, so the verification script passes verbatim.

The plan's Task 1 specifies `cursor:${selected ? 'default' : 'pointer'}` set inline; the implementation sets it via `nodeDiv.style.cursor` rather than a string-interpolated style attribute, which is functionally identical and matches the existing absolute-positioning pattern already used by `_mountGraph` for `left/top/width/height`.

## Threat surface scan

No new attack surface introduced. Both files modified are static assets:

- `entity_graph.js` — DOM-construction code; the existing XSS mitigation (`textContent` on label) is preserved verbatim. Icons are pure inline SVG strings (constants from Plan 06).
- `styles.css` — pure CSS rules; no `url()`, no `@import`, no `expression()`.

The original `<threat_model>` for this plan documents one risk row (T-1-W2-05 — class names exposed in HTML, accept disposition). No new STRIDE rows are warranted.

## TDD Gate Compliance

This plan is `type: execute` (not `type: tdd`); no RED→GREEN→REFACTOR sequencing required. The two `feat(...)` commits are the expected gate sequence for an execute-type plan.

## Self-Check

Files exist:
- FOUND: `folio_api/static/js/entity_graph.js`
- FOUND: `folio_api/static/css/styles.css`
- FOUND: `.planning/phases/01-entity-graph/01-09-SUMMARY.md`

Commits exist:
- FOUND: `6854605` — feat(01-09): styled node markup
- FOUND: `756dffa` — feat(01-09): edge stroke + selected-node glow CSS

## Self-Check: PASSED
