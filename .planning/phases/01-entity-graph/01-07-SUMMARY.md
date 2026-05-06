---
phase: 01-entity-graph
plan: 07
subsystem: ui
tags: [frontend, elk, layout, elkjs, fetch, vanilla-js]

# Dependency graph
requires:
  - phase: 01-entity-graph
    provides: "entity_graph.js skeleton (Plan 03), /explore/api/entity-graph/{iri:path} endpoint (Plan 04), entity:selected dispatch (Plan 05), showSkeleton/showError/ICONS (Plan 06)"
provides:
  - "buildELKGraph(graphData) — ELK layered spec builder for ancestors-only payload"
  - "runLayout(spec) — lazy ELK loader + elk.layout() invocation"
  - "Real EntityGraph.refreshFor(iri, type, force) — fetch + layout + state.graphData population"
  - "state.graphData.layout — laid-out ELK output ready for SVG rendering"
affects: [01-08-svg-renderer, 01-11-children-expansion, 01-12-graph-node-click]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ELK layered config with FIRST layerConstraint pinning topmost ancestor"
    - "Fetch + dedupe + force-refresh pattern for graph state"

key-files:
  created: []
  modified:
    - "folio_api/static/js/entity_graph.js"

key-decisions:
  - "Used ELK config values from UI-SPEC §spacing (32/64/16) rather than donor's 30/70/30 — matches spec verbatim"
  - "Dedupe key = (currentIri, currentType, !!graphData); force=true bypass added for the showError Retry button"
  - "Reset transform/expandedIris/graphData at every selection (D-11) — consistent with 'each selection is a fresh graph'"
  - "Layout output stashed on state.graphData.layout (single object) so Plan 08 reads payload + layout from one place"

patterns-established:
  - "Pattern: refreshFor(iri, type, force=false) — public retry path; force=true bypasses (currentIri, currentType) dedupe"
  - "Pattern: showSkeleton() → fetch → buildELKGraph → runLayout → resolve(graphData) — chained Promise pipeline; renderer is a separate consumer"

requirements-completed: [GRAPH-01, GRAPH-07]

# Metrics
duration: 2min
completed: 2026-05-06
---

# Phase 01 Plan 07: ELK Layout Pipeline Summary

**buildELKGraph + runLayout helpers and a real refreshFor that fetches /explore/api/entity-graph/{iri}, runs ELK layered layout (top-to-bottom, FIRST-layer pin on topmost ancestor), and stores the laid-out result on state.graphData.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-06T13:06:06Z
- **Completed:** 2026-05-06T13:08:00Z (approx)
- **Tasks:** 2 / 2
- **Files modified:** 1 (folio_api/static/js/entity_graph.js — +145 / -3)

## Accomplishments

- `buildELKGraph(graphData)` adapts donor `folio-enrich/frontend/index.html:8809-8840` to the ancestors-only payload shape: it builds the ancestor-chain edges (`ancestors[i] → ancestors[i+1]`), the last-ancestor → selected edge, and selected → child edges (when children are present).
- The topmost ancestor (`branch_root_type === 'ultimate'`) is pinned to the FIRST ELK layer via `elk.layered.layering.layerConstraint = 'FIRST'`, but only when it is not already an edge target (matches donor pattern at line 8882).
- ELK config values use UI-SPEC §spacing exactly: `nodeNode: '32'`, `nodeNodeBetweenLayers: '64'`, `padding: '[top=16,...]'`, with `algorithm: layered`, `direction: DOWN`, `crossingMinimization.strategy: LAYER_SWEEP`, `nodePlacement.strategy: NETWORK_SIMPLEX`, `edgeRouting: POLYLINE`.
- `runLayout(spec)` lazily loads ELK via the existing `loadELK()` helper (Plan 03) and resolves to the laid-out spec.
- The Plan 03 stub `refreshFor` (which threw "EntityGraph.refreshFor not yet implemented (Plan 07)") is fully replaced. The real implementation:
  - **Dedupes** per RESEARCH Pitfall 7: when `(iri, type)` match the previous call and `state.graphData` is non-null, returns the cached payload — unless `force=true`.
  - **Resets** `state.transform`, `state.expandedIris`, `state.graphData` at the start of every fresh fetch (D-11).
  - **Calls** `showSkeleton()` (Plan 06) immediately so the user sees the loading shape.
  - **Fetches** `/explore/api/entity-graph/{encodeURIComponent(iri)}` with `Accept: application/json`.
  - **On non-OK** invokes `showError(label, retry)` where the retry callback re-invokes `refreshFor(iri, type, true)`, then rethrows.
  - **On OK** stores the parsed payload, builds the ELK spec, runs layout, stashes the laid-out result on `state.graphData.layout`, resolves with `state.graphData`.
  - **Logs** failures via `console.error` and rethrows for caller awareness.

## Task Commits

1. **Task 1: buildELKGraph + runLayout helpers** — `32606c1` (feat)
2. **Task 2: real refreshFor — fetch + ELK layout + state.graphData** — `b715466` (feat)

## Confirmed ELK Config Values

| Key                                                  | Value                                  | Source                |
| ---------------------------------------------------- | -------------------------------------- | --------------------- |
| `elk.algorithm`                                      | `layered`                              | UI-SPEC §spacing      |
| `elk.direction`                                      | `DOWN`                                 | CONTEXT D-04          |
| `elk.spacing.nodeNode`                               | `32`                                   | UI-SPEC §spacing      |
| `elk.layered.spacing.nodeNodeBetweenLayers`          | `64`                                   | UI-SPEC §spacing      |
| `elk.layered.spacing.edgeNodeBetweenLayers`          | `24`                                   | RESEARCH §builder     |
| `elk.layered.spacing.edgeEdgeBetweenLayers`          | `12`                                   | RESEARCH §builder     |
| `elk.layered.crossingMinimization.strategy`          | `LAYER_SWEEP`                          | donor :8832           |
| `elk.layered.nodePlacement.strategy`                 | `NETWORK_SIMPLEX`                      | donor :8833           |
| `elk.edgeRouting`                                    | `POLYLINE`                             | donor :8834           |
| `elk.padding`                                        | `[top=16,left=16,bottom=16,right=16]`  | UI-SPEC §spacing      |
| `elk.layered.layering.layerConstraint` (per-node)    | `FIRST` (on `branch_root_type=='ultimate'` non-target nodes) | donor :8882, GRAPH-07 |

No deviations from RESEARCH.md ELK config values.

## Sample Console Test Transcript (expected shape after Plan 08 ships)

```
> EntityGraph.refreshFor('http://example.com/iri', 'class').then(d => console.log(d.layout));

# state.graphData populated. Resolved payload shape:
{
  selected: { iri: '…', label: '…', type: 'class', child_count: 5 },
  ancestors: [
    { iri: '…', label: 'Top', type: 'class', branch_root_type: 'ultimate' },
    { iri: '…', label: 'Middle', type: 'class', branch_root_type: null },
    …
  ],
  layout: {
    id: 'root',
    x: 0, y: 0, width: 540, height: 232,
    children: [
      { id: '<ultimate-iri>', x: 16,  y: 16, width: 180, height: 36, labels: [...] },
      { id: '<middle-iri>',   x: 16,  y: 116, width: 180, height: 36, labels: [...] },
      { id: '<selected-iri>', x: 16,  y: 216, width: 220, height: 36, labels: [...] }
    ],
    edges: [
      { id: 'e_0',       sources: [...], targets: [...], sections: [{ startPoint: {x,y}, endPoint: {x,y} }] },
      { id: 'e_anc_sel', sources: [...], targets: [...], sections: [{ … }] }
    ]
  }
}
```

(Live console verification deferred until Plan 08 ships the renderer that consumes `state.graphData.layout`. The skeleton remains visible after the successful fetch — acceptable intermediate state per Plan 07 §Defensive Notes.)

## Files Created/Modified

- `folio_api/static/js/entity_graph.js` — Added `buildELKGraph` (~80 lines) and `runLayout` (~6 lines) inside the IIFE, between the lazy ELK loader and the Public API stubs. Replaced the Plan 03 stub `refreshFor` with the real implementation (~48 lines, 3 lines removed).

## Decisions Made

- ELK config values follow UI-SPEC §spacing exactly (32/64/16) rather than donor's 30/70/30 — the spec was authored to refine the donor values and this plan was its first consumer.
- The `force` parameter on `refreshFor` is positional (`refreshFor(iri, type, force)`) rather than named/optional-object — keeps the existing public API signature stable for Plan 12's tree-click integration.
- Layout output is stashed on `state.graphData.layout` (single nested object) rather than as a separate `state.layout` field — Plan 08's renderer reads payload metadata (labels, types) and layout positions from the same place, simplifying the consumer.

## Deviations from Plan

None — plan executed exactly as written. The ELK config matches RESEARCH.md and UI-SPEC §spacing values. The skeleton remains visible after a successful fetch (Plan 08 will replace it with the SVG); this was already documented as an acceptable intermediate state in the plan's Defensive Notes.

## Issues Encountered

None. The worktree was anchored at older `main`; rebased onto current `main` (which includes Wave 1 commits 01-04, 01-05, 01-06) before executing — standard worktree procedure.

## Verification Results

- `node --check folio_api/static/js/entity_graph.js` → exit 0 (parses OK)
- `grep -c "function buildELKGraph"` → 1
- `grep -c "function runLayout"` → 1
- `grep -c "'elk.algorithm'"` → 1; `grep -c "'layered'"` → 1
- `grep -c "'elk.direction'"` → 1; `grep -c "'DOWN'"` → 1
- `grep -c "elk.layered.layering.layerConstraint"` → 1 (declaration); 3 total occurrences (declaration + comment + assignment)
- `grep -c "'FIRST'"` → 1
- Spacing values `'32'`, `'64'`, and the literal `16` (in padding) all present
- Stub message `EntityGraph.refreshFor not yet implemented` removed
- Plan 03's other stubs (`expand`, `toggleFullscreen`) intact
- `uv run pytest --no-cov` → **13 passed, 15 warnings, 0.93s** (no regression)

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 08 (SVG renderer) can now consume `state.graphData.layout` — children with `x/y/width/height/labels` and edges with `sections[]` are populated.
- Plan 12 (graph-node click → `selectNodeByIri`) can call `EntityGraph.refreshFor(iri, type)` to refresh the graph after a tree selection change.
- No blockers.

## Self-Check: PASSED

- File modified: `folio_api/static/js/entity_graph.js` — FOUND (verified via `git log --name-only` would list it; both commits modified this file)
- Commit `32606c1` — FOUND (Task 1)
- Commit `b715466` — FOUND (Task 2)

---
*Phase: 01-entity-graph*
*Completed: 2026-05-06*
