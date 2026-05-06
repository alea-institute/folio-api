---
phase: 01-entity-graph
plan: 03
subsystem: frontend-js
tags: [scaffold, javascript, module-skeleton, entity-graph]
requires: []
provides:
  - "window.EntityGraph public API surface"
  - "Lazy ELK loader (loadELK)"
  - "entity:selected event listener"
affects:
  - "folio_api/static/js/entity_graph.js"
  - "folio_api/templates/jinja2/explore/tree.html"
tech-stack:
  added: []
  patterns:
    - "IIFE module wrapper with 'use strict'"
    - "Lazy script-injection loader with cached promise"
    - "Custom DOM event channel (entity:selected) for cross-module messaging"
key-files:
  created:
    - "folio_api/static/js/entity_graph.js"
  modified:
    - "folio_api/templates/jinja2/explore/tree.html"
decisions:
  - "Stub methods (refreshFor/expand/toggleFullscreen) reject/throw with target plan numbers — accidental early calls are loud"
  - "loadELK caches the promise on success and clears it on error so a network blip allows retry"
  - "entity_graph.js loads on tree.html only (not base.html) per D-05; ELK bundle stays lazy via dynamic <script>"
  - "_onEntitySelected dedupes by (iri, type) per RESEARCH.md Pitfall 7 to prevent re-fetch loops"
metrics:
  duration: "~10 min"
  completed: "2026-05-06"
---

# Phase 01 Plan 03: Entity Graph Module Skeleton Summary

JS module skeleton for the entity graph renderer: `window.EntityGraph` public API, lazy elk.bundled.js loader, and `entity:selected` listener — landing the contract before downstream plans (04, 07, 08, 09, 10, 11, 12, 13) implement against it.

## What Was Built

### Task 1 — `folio_api/static/js/entity_graph.js` (commit `efbf46c`)

Self-contained 135-line IIFE module exposing `window.EntityGraph` with these methods:

| Method                | Status in this plan                | Filled in by |
| --------------------- | ---------------------------------- | ------------ |
| `init()`              | **Real** — registers `entity:selected` listener; auto-runs on DOMContentLoaded | — |
| `loadELK()`           | **Real** — lazy script injection of `/static/js/vendor/elk.bundled.js`; caches load promise; clears cache on error to allow retry | — |
| `refreshFor(iri, type)` | Stub — returns rejected Promise with "not yet implemented (Plan 07)" | Plan 07/08 |
| `expand(iri)`         | Stub — returns rejected Promise with "not yet implemented (Plan 11)" | Plan 11 |
| `close()`             | No-op | Plan 13 |
| `toggleFullscreen()`  | Stub — throws Error with "not yet implemented (Plan 13)" | Plan 13 |
| `state` (getter)      | **Real** — returns the live internal state object (read for external code, mutated by closure-bound implementers) | All later plans |

Also includes `_onEntitySelected(ev)` (private) — guards on `state.activeTab === 'graph'` (D-10 lazy fetch) and dedupes on `(iri, type)` (RESEARCH.md Pitfall 7). For now logs `console.debug`; Plan 12 replaces the body with a real `refreshFor()` call.

Internal `state` shape (locked for downstream plans):

```js
{
  activeTab: 'details',          // 'details' | 'graph'
  currentIri: null,
  currentType: null,             // 'class' | 'property'
  graphData: null,
  transform: { x: 0, y: 0, scale: 1 },  // pan/zoom
  expandedIris: new Set(),
  isFullscreen: false,
}
```

### Task 2 — `folio_api/templates/jinja2/explore/tree.html` (commit `3f36d14`)

Single line added at **line 235**, immediately after `<script src="/static/js/unified_tree.js"></script>` (line 234):

```html
<script src="/static/js/entity_graph.js"></script>
```

`base.html` not touched. No `elk.bundled.js` reference in tree.html — the heavy bundle is loaded dynamically via `loadELK()` only on first call.

## Verification (all green)

- `node --check folio_api/static/js/entity_graph.js` → exit 0 (PARSE_OK)
- All 6 public-API method names export-bound: `init`, `loadELK`, `refreshFor`, `expand`, `close`, `toggleFullscreen`
- 124 non-blank lines (≥ 80 required)
- Contains `window.EntityGraph =` exactly once
- Contains `'/static/js/vendor/elk.bundled.js'` exactly once
- Contains `addEventListener('entity:selected'` exactly once
- No external CDN URLs (`grep -E "https?://(unpkg|cdnjs|jsdelivr)"` empty)
- `grep -c '<script src="/static/js/entity_graph.js"></script>' folio_api/templates/jinja2/explore/tree.html` → `1`
- `git diff --exit-code folio_api/templates/jinja2/layouts/base.html` → exit 0 (untouched)
- Script tag ordering: split_pane.js (233) → unified_tree.js (234) → entity_graph.js (235) ✓

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None. The trust-boundary surface introduced (one new same-origin `<script>` injection point in `loadELK`, plus a `window.EntityGraph` global) is fully covered by the plan's threat register entries T-1-W0-07/08/09 with the `accept` / `mitigate` dispositions already documented; no new surface emerged during execution.

## Known Stubs

These are intentional and tracked for replacement by later plans — they do NOT prevent this plan's goal (establishing the contract) from being achieved:

| Stub                         | File                            | Lines (approx) | Resolved by |
| ---------------------------- | ------------------------------- | -------------- | ----------- |
| `refreshFor(iri, type)`      | `entity_graph.js`               | ~96–99         | Plan 07/08  |
| `expand(iri)`                | `entity_graph.js`               | ~101–104       | Plan 11     |
| `close()`                    | `entity_graph.js`               | ~106–108       | Plan 13     |
| `toggleFullscreen()`         | `entity_graph.js`               | ~110–113       | Plan 13     |
| `_onEntitySelected` body     | `entity_graph.js`               | ~85–94         | Plan 12     |

All stubs throw / reject with a message that names the target plan number, so any accidental early invocation surfaces loudly during downstream development.

## Self-Check

- File `folio_api/static/js/entity_graph.js` exists ✓
- File `folio_api/templates/jinja2/explore/tree.html` modified ✓
- Commit `efbf46c` exists ✓
- Commit `3f36d14` exists ✓

## Self-Check: PASSED
