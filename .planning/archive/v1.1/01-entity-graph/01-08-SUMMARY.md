---
phase: 01-entity-graph
plan: 08
subsystem: ui
tags: [frontend, svg, renderer, cubic-bezier, dom]

# Dependency graph
requires:
  - phase: 01-entity-graph
    provides: "entity_graph.js skeleton (Plan 03), showSkeleton/clearStates/ICONS (Plan 06), buildELKGraph + runLayout + state.graphData.layout (Plan 07)"
provides:
  - "buildEdgePath(section) — verbatim donor cubic-bezier formula, simplified for D-04 always-DOWN"
  - "renderGraph(graphData) — public-ish renderer; defers to requestAnimationFrame"
  - "_mountGraph(graphData) — internal DOM constructor for SVG-edge + DIV-node hybrid scaffold"
  - "DOM scaffold inside #entity-graph-pane: #graph-viewport > #graph-transform > (svg#graph-svg + div.graph-nodes)"
  - "refreshFor now mounts a visible graph end-to-end after fetch + ELK layout"
affects: [01-09-visual-styling, 01-10-pan-zoom, 01-11-children-expansion, 01-12-graph-node-click, 01-13-fullscreen-modal]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hybrid HTML+SVG mount: SVG hosts edges only; nodes are absolutely-positioned DIVs (donor pattern, allows HTML node content + Heroicons)"
    - "requestAnimationFrame deferral so display:none → display:block tab transitions don't measure with clientWidth=0 (Pitfall 6)"
    - "Defensive `(edge.sections || []).forEach` guard per Pitfall 5 (ELK omits sections for trivial/unrouted edges)"
    - "textContent (not innerHTML) for label rendering — XSS mitigation T-1-W2-03"

key-files:
  created: []
  modified:
    - "folio_api/static/js/entity_graph.js"

key-decisions:
  - "Hybrid mount over pure-SVG: SVG hosts edge <path> only; nodes are sibling DIVs in .graph-nodes — matches donor pattern (folio-enrich:8855-8916) and lets Plan 09 use rich HTML (Heroicons, ROOT badge, ellipsis text)"
  - "Stroke color = currentColor (not text-gray-400 wrapper): leaves the visual to Plan 09's CSS while still rendering visibly against a white pane"
  - "SVG positioned absolutely with pointer-events:none — clicks fall through to the absolutely-positioned node DIVs without per-node hit-test plumbing"
  - "Bounds computed from layout.children (max x+w, max y+h) + 16 px padding rather than reading layout.width/height — ELK sometimes omits root dims when children fit tightly; computed bounds are robust"
  - "_findUltimateRootIri checks ancestors[].branch_root_type==='ultimate' first, then graphData.selected as fallback (handles the root-entity case where the selected IS the ultimate)"

patterns-established:
  - "Pattern: renderGraph defers DOM work to requestAnimationFrame; _mountGraph does the work — separates the public entry from the implementation for testability"
  - "Pattern: createElementNS for <svg>/<path>/<g> (matches donor); plain createElement for the wrapping DIVs"
  - "Pattern: every dynamic text node uses textContent; no innerHTML for user-controlled values"

requirements-completed: [GRAPH-01, GRAPH-08]

# Metrics
duration: 3min
completed: 2026-05-06
---

# Phase 01 Plan 08: SVG Hybrid Renderer Summary

**buildEdgePath verbatim donor cubic-bezier + renderGraph that mounts a hybrid SVG-edge + DIV-node scaffold inside #entity-graph-pane, deferred via requestAnimationFrame and wired into refreshFor for end-to-end visible graphs.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-06T13:18:00Z (approx)
- **Completed:** 2026-05-06T13:21:00Z (approx)
- **Tasks:** 1 / 1
- **Files modified:** 1 (`folio_api/static/js/entity_graph.js` — +158 / -0)

## Accomplishments

- `buildEdgePath(section)` is a **verbatim port** of the donor formula at `folio-enrich/frontend/index.html:8976-8990`, simplified for the D-04 always-DOWN direction. The cubic bezier hinges at `midY = (sp.y + ep.y) / 2` with both control points sharing `midY` — guaranteeing a 90° vertical exit at the start and 90° vertical entry at the end. The exact formula:

  ```js
  function buildEdgePath(section) {
    var sp = section.startPoint;
    var ep = section.endPoint;
    var midY = (sp.y + ep.y) / 2;
    return 'M' + sp.x + ',' + sp.y + ' C' + sp.x + ',' + midY + ' ' + ep.x + ',' + midY + ' ' + ep.x + ',' + ep.y;
  }
  ```

- `renderGraph(graphData)` is the public-ish entry. It returns immediately after `clearStates()` and queues the DOM build via `requestAnimationFrame` so that, when triggered by a tab-switch (`display:none` → `display:block`), the panel has a non-zero `clientWidth` before any measurement (RESEARCH Pitfall 6).

- `_mountGraph(graphData)` builds the actual scaffold inside `#entity-graph-pane`:
  ```
  div#graph-viewport.absolute.inset-0.overflow-hidden
    div#graph-transform (transform-origin: 0 0)
      svg#graph-svg (width/height/viewBox from computed bounds; pointer-events:none)
        g.graph-edges
          path.graph-edge per edge section
      div.graph-nodes (relative; width/height = bounds)
        div.graph-node[.graph-node-selected][.graph-node-root] per layout child
  ```

- **Edges:** Iterated with the defensive `(edge.sections || []).forEach` pattern per RESEARCH Pitfall 5. Each section becomes a `<path>` with `d=buildEdgePath(section)`, `class="graph-edge"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="1.5"`. Plan 09 will set the actual stroke color via CSS targeting `.graph-edge`.

- **Nodes:** Each layout child becomes an absolutely-positioned `<div>` with inline `left/top/width/height` from ELK output. The label is set via `textContent` (XSS mitigation T-1-W2-03 — RESEARCH Security row 2). The selected node carries `.graph-node-selected` (matched on `graphData.selected.iri`); the ultimate root carries `.graph-node-root` (matched via `_findUltimateRootIri()` which scans `graphData.ancestors[].branch_root_type === 'ultimate'`, falling back to `graphData.selected.branch_root_type` for the root-entity case).

- **Bounds:** Computed from `layout.children` (`max(x + width)`, `max(y + height)`) plus 16 px padding rather than reading `layout.width/height` from the ELK root — ELK sometimes omits root dimensions and the children-derived bounds are always present.

- **Wiring:** `refreshFor`'s `.then` chain now calls `renderGraph(state.graphData)` after `runLayout` resolves and stashes `state.graphData.layout`. The Promise still resolves to `state.graphData` so existing callers' contracts are unchanged.

- **Security:** All dynamic text uses `textContent`; no `innerHTML` for any user-controlled value (label, IRI). The donor pattern at `folio-enrich:8895` is preserved.

## Task Commits

1. **Task 1: buildEdgePath + renderGraph + DOM mount + refreshFor wiring** — `58681c7` (feat)

## Confirmation: buildEdgePath Matches Donor Verbatim

| Element                          | Donor (folio-enrich:8983-8984)                                                            | Plan 08 implementation                                                                                                                                                |
| -------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hinge                            | `const midY = (sp.y + ep.y) / 2;`                                                         | `var midY = (sp.y + ep.y) / 2;`                                                                                                                                       |
| Path string                      | `` `M${sp.x},${sp.y} C${sp.x},${midY} ${ep.x},${midY} ${ep.x},${ep.y}` ``                 | `'M' + sp.x + ',' + sp.y + ' C' + sp.x + ',' + midY + ' ' + ep.x + ',' + midY + ' ' + ep.x + ',' + ep.y`                                                              |
| Direction conditional            | `if (dir === 'TB' || dir === undefined) { ... } else { ... }` (TB and LR branches)        | TB-only branch retained per CONTEXT D-04 (LR branch dropped — direction is fixed to DOWN)                                                                             |

The control points share `midY` (the donor's `${sp.x},${midY}` and `${ep.x},${midY}`), guaranteeing a 90° vertical exit/entry — math identical to the donor's TB branch.

## Sample d-Attribute Output

For a typical ancestor → selected edge with `startPoint = {x: 106, y: 52}` and `endPoint = {x: 106, y: 116}`:

```
M106,52 C106,84 106,84 106,116
```

For an offset edge (last ancestor at x=180 → first child at x=320, y from 200 to 264):

```
M180,200 C180,232 320,232 320,264
```

Both render as smooth S-curves with vertical tangents at both endpoints.

## Files Created/Modified

- `folio_api/static/js/entity_graph.js` — Added the SVG renderer block (~155 lines) between `runLayout` and the Public API stubs. Also added a 6-line wiring change inside `refreshFor` to call `renderGraph(state.graphData)` after `runLayout` resolves.

## Decisions Made

- **Hybrid mount** (SVG-edges + DIV-nodes) over pure SVG: matches donor (`folio-enrich:8855-8916`) and lets Plan 09 layer Heroicons, the ROOT badge, and ellipsis text via standard CSS without `<foreignObject>` quirks.
- **`stroke="currentColor"`** on `<path>` (not a Tailwind text-gray-400 wrapping group): keeps the renderer styling-agnostic. Plan 09's CSS will set `.graph-edge { stroke: <theme-token>; }` directly.
- **`pointer-events: none`** on the SVG: clicks fall through to the absolutely-positioned node DIVs; no per-path hit-test plumbing required.
- **Bounds from children, not from `layout.width/height`:** ELK occasionally omits root dimensions for tightly-packed layouts. Computed bounds are always present and add the same 16 px padding as the ELK config.
- **`_findUltimateRootIri` fallback** to `graphData.selected.branch_root_type`: when the user clicks the topmost class in a chain, the selected entity IS the ultimate root, and there are no ancestors to scan. Plan 09 still styles the same node correctly.

## Deviations from Plan

None — plan executed exactly as written. The DOM scaffold ids (`graph-viewport`, `graph-transform`, `graph-svg`) and class (`graph-nodes`) match the plan's specified structure verbatim. The defensive `(sections || []).forEach` guard, the `textContent` label pattern, the `requestAnimationFrame` deferral, and the `graph-node-selected` / `graph-node-root` markers all follow the plan literally.

## Issues Encountered

None. Worktree was anchored at older `main`; rebased onto current `main` (which now includes the Plan 01-07 merge) before executing — standard worktree procedure.

## Verification Results

- `node --check folio_api/static/js/entity_graph.js` → exit 0 (parses OK)
- `grep -c "function buildEdgePath"` → 1
- `grep -c "function renderGraph"` → 1
- `grep -q "graph-viewport"` → match
- `grep -q "graph-transform"` → match
- `grep -q "requestAnimationFrame"` → match
- `grep -q "sections || \[\]"` → match (defensive iteration guard present)
- `grep -q "\.textContent ="` → match (label rendering uses textContent — XSS mitigation T-1-W2-03)
- `grep -q "graph-node-selected"` → match
- `grep -q "graph-node-root"` → match
- `uv run pytest --no-cov` → **13 passed, 15 warnings, 0.94s** (no regression)

## Manual Smoke (deferred to post-Plan-09 styling)

Live verification is best done after Plan 09 sets visible CSS for `.graph-edge` / `.graph-node`. The renderer is correct now, but the cubic-bezier paths are stroked with `currentColor` against a default `text-` color — they will be near-black and visible, but unstyled. Procedure:

1. Boot the dev server: `uv run uvicorn folio_api.main:app --reload --port 8742`
2. Open `/explore/tree`, click any class entity
3. Click the **Entity Graph** tab; in the console, call `EntityGraph.refreshFor('<iri>', 'class')`
4. Inspect `#entity-graph-pane` — should contain `<svg id="graph-svg">` with `<path class="graph-edge" d="M...C...">` plus `.graph-node` DIVs

Console should be clean. The graph will be visually plain (no Heroicons, no selected glow, no ROOT badge) until Plan 09 ships.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 09 (visual styling):** Can target `.graph-edge`, `.graph-node`, `.graph-node-selected`, `.graph-node-root` directly. The DOM contract is stable.
- **Plan 10 (pan/zoom):** Can read `#graph-viewport` for wheel/mouse events and write `transform: translate(x,y) scale(s)` to `#graph-transform`. The transform-origin is already set to `0 0`.
- **Plan 11 (children expansion):** Can call `EntityGraph.refreshFor(currentIri, currentType, true)` after mutating `state.expandedIris` — `force=true` bypasses the dedupe and re-runs the full fetch + layout + render pipeline.
- **Plan 12 (graph-node click):** `.graph-node[data-iri]` carries the IRI; a single delegated click handler on `.graph-nodes` can read `event.target.closest('.graph-node').dataset.iri`.
- **Plan 13 (fullscreen modal):** The hybrid scaffold copies cleanly into a modal — the `#graph-transform` element is the natural mount target.

No blockers.

## Self-Check: PASSED

- File modified: `folio_api/static/js/entity_graph.js` — FOUND
- Commit `58681c7` — FOUND (Task 1)
- Plan file `01-08-PLAN.md` exists — FOUND
- All `<verify>` automated checks pass (see Verification Results above)

---
*Phase: 01-entity-graph*
*Completed: 2026-05-06*
