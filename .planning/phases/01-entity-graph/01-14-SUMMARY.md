---
phase: 01-entity-graph
plan: 14
subsystem: performance-instrumentation
tags: [performance, instrumentation, manual-uat, observability]
requires: [01-07, 01-08, 01-10, 01-11, 01-12]
provides:
  - performance.mark/measure instrumentation around fetch + layout + render
  - eg:total measure for the < 500 ms p50 budget gate
affects:
  - folio_api/static/js/entity_graph.js
tech-stack:
  added: []
  patterns:
    - "User Timing API (performance.mark / performance.measure) with typeof-guard helpers"
    - "Defensive instrumentation: silent no-op when API absent"
key-files:
  created: []
  modified:
    - folio_api/static/js/entity_graph.js
decisions:
  - "Marks stay in production code as a permanent observability hook (zero cost when not actively measured)"
  - "eg:total spans refreshFor entry → _mountGraph append complete (excludes the rAF-deferred fitGraph)"
  - "All performance API calls routed through _perfMark / _perfMeasure helpers that swallow exceptions so instrumentation cannot break render"
metrics:
  completed: 2026-05-06
  duration: under 30 minutes for instrumentation; manual 5-trial measurement deferred to user
requirements: [GRAPH-14]
---

# Phase 01 Plan 14: Performance Instrumentation + < 500 ms Render Budget Checkpoint Summary

Adds lightweight User Timing instrumentation (`performance.mark` / `performance.measure`) at the four phase boundaries of the entity-graph tab-activation flow so the < 500 ms p50 initial-render budget (CONTEXT D-25, GRAPH-14) is observable in DevTools without re-instrumenting. The plan is a measurement-and-checkpoint plan and intentionally adds NO features; it sets up the harness the user runs the 5-trial UAT against.

## Tasks Completed

| Task | Name | Status | Commit | Files |
|------|------|--------|--------|-------|
| 1 | Add performance.mark instrumentation around fetch + layout + render phases | DONE | `b6c19f4` | `folio_api/static/js/entity_graph.js` |
| 2 | Manual checkpoint: 5-trial p50 verification on running server | DEFERRED to user (instructions below) | n/a | n/a |

## What Changed

### `folio_api/static/js/entity_graph.js`

Added a defensive performance-instrumentation helper block at the top of the IIFE:

```javascript
function _perfMark(name) {
  if (typeof performance === 'undefined') return;
  if (typeof performance.mark !== 'function') return;
  try { performance.mark(name); } catch (_) { /* swallow */ }
}
function _perfMeasure(name, startMark, endMark) {
  if (typeof performance === 'undefined') return;
  if (typeof performance.measure !== 'function') return;
  try { performance.measure(name, startMark, endMark); } catch (_) { /* swallow */ }
}
```

Then dropped four mark sets at the phase boundaries of the existing pipeline:

| Boundary | Location | Marks emitted |
|----------|----------|---------------|
| 1 | `refreshFor` entry, after dedupe early-return | `eg:fetch:start` |
| 2 | After `res.json()` resolves, before `buildELKGraph` | `eg:fetch:end`, measure `eg:fetch`, `eg:layout:start` |
| 3 | After `runLayout()` resolves, before `renderGraph()` | `eg:layout:end`, measure `eg:layout`, `eg:render:start` |
| 4 | End of `_mountGraph` (after SVG + nodes appended, fit queued) | `eg:render:end`, measure `eg:render`, measure `eg:total` |

The `eg:total` measure is what the < 500 ms p50 budget gates on. It spans `eg:fetch:start` → `eg:render:end` and excludes the `requestAnimationFrame`-deferred `fitGraph` paint (which is consistently sub-frame and not attributable to this code path).

## Manual Checkpoint Instructions (Task 2 — user runs)

This plan's second task is a `checkpoint:human-verify` gate. Run the 5-trial UAT at your convenience:

### Setup

1. Pull this branch and start the server:
   ```bash
   uv run uvicorn folio_api.api:app
   ```
2. Open Chrome DevTools → Performance tab. Confirm "User Timing" is enabled in the recording config (it is by default).

### Trial procedure (repeat 5 times with distinct entities)

Pick 5 entities of varying depth from `/explore/tree` covering the test population (UI-SPEC §Performance: depth ≤ 8 ancestors). Suggested mix:

- **Trial 1:** A leaf class (no children, shallow ancestor chain)
- **Trial 2:** A mid-depth class (3–4 ancestors)
- **Trial 3:** A deep class (≥ 6 ancestors)
- **Trial 4:** An object property (mid-depth)
- **Trial 5:** A deep object property

For each entity:
1. Hard refresh `/explore/tree` (Cmd+Shift+R / Ctrl+Shift+R)
2. Click the entity in the left tree (Details tab loads)
3. Click DevTools Performance "Record" button
4. Click the **Entity Graph** tab
5. Wait for the graph to be visible (laid-out nodes + bezier edges)
6. Click "Stop" in DevTools
7. In the recording, find the **User Timing** track (look for "Entity Graph" group or filter by `eg:`)
8. Read the value of the `eg:total` measure — record it in the table below

### Recording table

| Trial | Entity Label | IRI / hash | Ancestor depth | `eg:fetch` (ms) | `eg:layout` (ms) | `eg:render` (ms) | `eg:total` (ms) |
|-------|--------------|-----------|---------------:|----------------:|-----------------:|-----------------:|----------------:|
| 1     |              |           |                |                 |                  |                  |                 |
| 2     |              |           |                |                 |                  |                  |                 |
| 3     |              |           |                |                 |                  |                  |                 |
| 4     |              |           |                |                 |                  |                  |                 |
| 5     |              |           |                |                 |                  |                  |                 |

**p50 (median of 5 `eg:total`):** _____ ms

### Acceptance

- **PASS:** p50 < 500 ms → reply with the resume signal `approved p50=<value>ms`
- **FAIL:** p50 ≥ 500 ms → identify the dominant phase (whichever of `eg:fetch`, `eg:layout`, `eg:render` is consistently largest), save 3 representative DevTools profiles via "Save profile…", and reply with `exceeded p50=<value>ms dominant=<phase>` so a follow-up optimization plan can target it.

### What to do if the budget is exceeded

Per the plan: do NOT modify code in this plan. Instead:

1. Capture 3 representative `.json` profiles from DevTools (right-click recording → Save profile…). Stash them in `.planning/phases/01-entity-graph/perf-traces/` (create dir).
2. Identify the dominant phase from the User Timing track.
3. File a follow-up plan recommending one optimization based on which phase dominates:
   - **`eg:fetch` dominates:** add server-side cache for `/explore/api/entity-graph/` (currently deferred per CONTEXT D-14), or precompute ancestor chains at folio-python load time.
   - **`eg:layout` dominates:** swap ELK `layered` for a lighter algorithm on shallow graphs (e.g. heuristic when ancestors ≤ 3), or move ELK to a Web Worker so layout doesn't block the main thread.
   - **`eg:render` dominates:** batch DOM appends inside a DocumentFragment, or render edges with a single `<path>` element using `Path2D` operations rather than one `<path>` per section.

## Verification

### Automated

```bash
node --check folio_api/static/js/entity_graph.js                       # PASS — syntax valid
grep -q "performance.mark" folio_api/static/js/entity_graph.js          # PASS
grep -q "eg:fetch:start" folio_api/static/js/entity_graph.js            # PASS
grep -q "eg:layout:start" folio_api/static/js/entity_graph.js           # PASS
grep -q "eg:render:end" folio_api/static/js/entity_graph.js             # PASS
grep -q "eg:total" folio_api/static/js/entity_graph.js                  # PASS
uv run pytest --no-cov                                                  # 13 passed
```

All automated criteria green.

### Acceptance Criteria

- [x] All four mark pairs present with names `eg:fetch`, `eg:layout`, `eg:render`, `eg:total`
- [x] Marks gated on `typeof performance !== 'undefined'` (in `_perfMark` helper)
- [x] No regression: graph still renders identically (test suite 13/13)
- [ ] DevTools Performance recording shows the four named measures under User Timing — **deferred to user manual run**
- [ ] p50 < 500 ms across 5 typical entities — **deferred to user manual run**

## Deviations from Plan

### Auto-fixed Issues

None. The plan's instructions specified inline `if (typeof performance !== 'undefined' && performance.mark)` guards; I refactored that into reusable `_perfMark` / `_perfMeasure` helpers (functionally identical but DRY across 9 call sites and easier to extend later). Additionally wrapped the underlying calls in `try/catch` so a misbehaving polyfill cannot break render — instrumentation must never block the user's graph from appearing. This is a tightening of the spec, not a deviation from intent.

### Authentication Gates

None.

### Architectural Changes

None.

## Threat Flags

None — the plan's threat register (T-1-W4-01) marked phase labels as accept-disposition because they carry no IRIs / PII. Confirmed: only the labels `eg:fetch:start`, `eg:fetch:end`, `eg:layout:start`, `eg:layout:end`, `eg:render:start`, `eg:render:end`, `eg:fetch`, `eg:layout`, `eg:render`, `eg:total` are emitted. No entity IRI, label, or user data flows into any mark name.

## Known Stubs

None.

## Test / Verify

To verify locally:
- **Syntax:** `node --check folio_api/static/js/entity_graph.js`
- **Tests:** `uv run pytest --no-cov` (expect 13/13)
- **Manual perf UAT:** run the 5-trial procedure above and report `eg:total` p50

## Self-Check: PASSED

- File `folio_api/static/js/entity_graph.js` exists and contains all six required mark/measure labels
- Commit `b6c19f4` exists in the worktree branch git log
- `node --check` passes (syntax valid)
- Test suite green (13/13)
- SUMMARY.md frontmatter valid; manual checkpoint instructions complete
