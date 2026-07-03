---
phase: 01-entity-graph
plan: 10
subsystem: ui
tags: [frontend, pan-zoom, transform, fit-to-viewport, entity-graph]

# Dependency graph
requires:
  - phase: 01-entity-graph
    provides: "renderGraph + #graph-viewport / #graph-transform scaffold (Plan 08), styled nodes (Plan 09)"
provides:
  - "applyTransform(): writes state.transform → #graph-transform style.transform"
  - "fitGraph(): zoom-to-fit on initial render with 16px padding (D-26 + GRAPH-14)"
  - "_onWheel: zoom-around-cursor with scale clamped 0.2..4.0 (UI-SPEC line 227)"
  - "_panMouseDown/_panMouseMove/_panMouseUp: drag-to-pan, ignores .graph-node clicks"
  - "wirePanZoom(): idempotent listener attachment via dataset.panZoomWired"
  - "Auto-fit invocation from inside _mountGraph (Pitfall 6 guarded with rAF + 0×0 reschedule)"
affects: [Plan-11-expand, Plan-12-node-clicks, Plan-13-fullscreen-modal]

# Tech tracking
tech-stack:
  added: []  # No new deps; pure DOM/CSS transform port
  patterns:
    - "Pan/zoom transform-tracking (donor folio-enrich:9054-9118 port)"
    - "Idempotent listener wiring via dataset flag (dataset.panZoomWired)"
    - "Auto-fit-on-first-render with rAF reschedule when viewport is 0×0 (Pitfall 6 mitigation)"

key-files:
  created: []
  modified:
    - "folio_api/static/js/entity_graph.js (+134 lines: pan/zoom + fitGraph + wirePanZoom + exports)"

key-decisions:
  - "Min/max zoom 0.2..4.0 — matches UI-SPEC line 227, slightly tighter than donor's 0.1..3.0"
  - "Pan listeners attached to document (mousemove/mouseup) so user can drag past viewport edges without losing the gesture"
  - "applyTransform exported (not just internal) so Plan 11 expand can refresh the matrix after layout merge while preserving D-26 user zoom"
  - "fitGraph reads from state.graphData.layout (already laid out by Plan 07) — no recomputation"
  - "wirePanZoom is idempotent (dataset.panZoomWired flag) so Plan 11's re-render does not double-bind handlers"

patterns-established:
  - "Pan/zoom CSS transform stored once on #graph-transform; never on individual nodes"
  - "All pan/zoom mutations go through applyTransform() (single source of truth for transform → DOM)"
  - "Auto-fit only runs from _mountGraph; later re-renders pass through but skip fit (Plan 11 will rely on this contract per D-26)"

requirements-completed: [GRAPH-13, GRAPH-14]

# Metrics
duration: 14min
completed: 2026-05-06
---

# Phase 01 Plan 10: Pan/Zoom Transform + Auto-Fit-to-Viewport Summary

**Drag-to-pan + scroll-to-zoom-around-cursor + initial zoom-to-fit on the entity graph, ported verbatim from folio-enrich:9054-9118 with min/max scale tightened to 0.2..4.0 per UI-SPEC.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-05-06T (worktree session start)
- **Completed:** 2026-05-06
- **Tasks:** 1 / 1
- **Files modified:** 1

## Accomplishments

- **Pan tracking** — `_panMouseDown` on viewport, `_panMouseMove`/`_panMouseUp` on document; respects left-button-only and ignores clicks originating inside `.graph-node` so Plan 12 can attach node-click handlers without a conflict
- **Zoom-around-cursor** — `_onWheel` computes zoom factor `1.12` per click; rescales `state.transform.{x,y}` so the cursor's data-space coordinate stays under the cursor; clamps `scale ∈ [0.2, 4.0]`; calls `preventDefault()` to suppress page scroll
- **Auto-fit-to-viewport** — `fitGraph()` reads viewport dimensions, computes laid-out graph bounds from `state.graphData.layout.children`, scales to fit with 16 px padding, and centers the graph; never scales above 1× (so small graphs aren't blown up); guards against `display:none` panes by rescheduling via `requestAnimationFrame` when `clientWidth/clientHeight` are 0 (Pitfall 6)
- **Idempotent listener attachment** — `wirePanZoom()` uses `vp.dataset.panZoomWired === '1'` to skip re-binding when Plan 11's expand re-renders the scaffold
- **Public API surface extended** — `applyTransform` and `fitGraph` exported on `window.EntityGraph`, satisfying Plan 11's need to re-apply the matrix after layout merges and Plan 13's need to re-fit after fullscreen toggle

## Task Commits

1. **Task 1: Add pan/zoom + applyTransform + fitGraph helpers** — `5b087df` (feat)

## Files Created/Modified

- `folio_api/static/js/entity_graph.js` — Added (+134 lines):
  - `applyTransform()` — writes state.transform to `#graph-transform` style.transform
  - `fitGraph()` — auto-fit-to-viewport with 16 px padding; rAF reschedule when 0×0
  - `_onWheel(e)` — zoom-around-cursor; clamp 0.2..4.0; preventDefault
  - `_panMouseDown/Move/Up` — drag-pan via document-level listeners; ignores `.graph-node` clicks
  - `wirePanZoom()` — idempotent attach to `#graph-viewport` via `dataset.panZoomWired`
  - `_mountGraph` extended: calls `wirePanZoom()` and `requestAnimationFrame(fitGraph)` after the scaffold is appended to the pane
  - Public API: `applyTransform` and `fitGraph` added to the `window.EntityGraph` export

## Decisions Made

- **Zoom limits 0.2..4.0** — UI-SPEC §Interaction Contract (line 227) specifies these tighter bounds than the donor's 0.1..3.0; followed the spec.
- **Pan handlers on `document`, not `vp`** — donor uses `window.addEventListener('mousemove', ...)`. Switched to `document.addEventListener` and attach/detach on each gesture so we don't leak listeners. Same effective coverage (drag past viewport still tracks).
- **`fitGraph` skip-up rule (`scale = min(..., 1)`)** — never zoom *in* automatically; small graphs render at 1×, large graphs zoom out to fit. Avoids the surprise of a 3-node ancestor chain rendered at 4× on first paint.
- **Single-frame rAF guard for 0×0 viewport** — defer fitGraph one frame and re-attempt; cheaper than `MutationObserver` and matches the Pitfall 6 prescription. Tab-switch flicker should not trigger more than 1 reschedule in practice.
- **Plan 11 contract via export, not internal call** — Plan 10 does NOT introduce a `{preserveZoom: true}` flag (the plan's success criteria mention the *convention* — Plan 11 will simply skip its own `fitGraph()` call and use `applyTransform()` directly, which is now exported).

## Deviations from Plan

None — plan executed exactly as written. Confirmed:

- node --check exits 0 (parse OK)
- `function fitGraph` appears (1 match)
- `function applyTransform` appears (1 match)
- `wirePanZoom` appears (3 matches: definition, _mountGraph call site, internal use)
- `Math.max(0.2` and `Math.min(4.0` literals present (1 each)
- Pytest 13/13 passing (no backend regression)

## Manual UAT Notes

The plan's `<output>` block requests:

- **Pan:** drag in empty viewport space → graph translates. Hand-trace of code: `_panMouseDown` records start, `_panMouseMove` sets `state.transform.x = startXform.x + (clientX − startX)`, `applyTransform()` writes the matrix. ✓ correct.
- **Zoom:** wheel over viewport → zoom around cursor; scale clamped 0.2..4.0. Hand-trace: `_onWheel` computes new scale via `oldScale * (deltaY < 0 ? 1.12 : 1/1.12)`, clamps via `Math.max(0.2, Math.min(4.0, ...))`, then re-anchors transform.x/y so `(mx, my)` in viewport coords maps to the same `(graphX, graphY)` in data coords before/after. ✓ matches donor's zoom-around-pointer formula.
- **Auto-fit:** initial render → graph centers and fits with 16 px padding. Hand-trace: `_mountGraph` builds DOM, then calls `wirePanZoom()` + `requestAnimationFrame(fitGraph)`. `fitGraph` reads `getBoundingClientRect()` (viewport now real because the rAF defers past the layout flush), computes `gw/gh` from layout children, sets `scale = min(availW/gw, availH/gh, 1)` clamped ≥ 0.2, centers via `(vw − gw*scale)/2`. ✓ correct.
- **Confirmed clamp values:** 0.2 (min) and 4.0 (max). ✓

A live browser smoke is gated on Plan 12 (graph-node click → tree-select wiring) and Plan 11 (children expansion) to be fully exercisable; for now, the structural verification + parse check + test pass form the contract.

## Threat Surface

No new threat surface beyond the plan's STRIDE register (T-1-W3-01 mousemove flood, T-1-W3-02 wheel preventDefault — both accepted). No network calls added; no new auth paths; no schema or trust-boundary changes.

## Issues Encountered

- **Worktree base behind main** — On entry, the worktree branch was based on origin/main (commit 9059e73) and did not contain Plans 01-07/08/09 or the `.planning/phases/01-entity-graph/` tree. Resolved by `git rebase main` per the orchestrator's `<worktree_base_note>` guidance. No conflicts (the worktree had no local commits before this plan).

## Self-Check: PASSED

- File `folio_api/static/js/entity_graph.js` exists and parses (node --check OK)
- Commit `5b087df` recorded in `git log` on branch `worktree-agent-a757387cdde10c257`
- All five plan-mandated greps pass with the expected match counts
- Test suite (pytest --no-cov) green: 13/13

## Next Phase Readiness

- `state.transform` is now mutated by every gesture and read by `applyTransform()` — Plan 11's expand can append children, re-run ELK, and call `applyTransform()` to redraw without re-fitting (D-26 preserved zoom).
- `wirePanZoom` is idempotent → Plan 11 can re-mount the scaffold without double-binding.
- `fitGraph` is exported → Plan 13's fullscreen modal toggle can call it on resize without re-fetching the graph.

---
*Phase: 01-entity-graph*
*Completed: 2026-05-06*
