---
phase: 01-entity-graph
plan: 12
subsystem: explore-ui
tags: [frontend, lazy-fetch, navigation, lifecycle]
requires:
  - 01-03 (entity_graph.js skeleton + entity:selected listener)
  - 01-05 (wireDetailTabs in unified_tree.js — already calls onTabActivated)
  - 01-06 (showEmpty / showSkeleton state renderers)
  - 01-07 (refreshFor with fetch + ELK layout pipeline)
  - 01-08 (renderGraph + _mountGraph DOM construction)
  - 01-10 (pan/zoom; preserves user view across re-renders)
provides:
  - "EntityGraph.onTabActivated() — public lifecycle hook"
  - "Real entity:selected handler — refreshes graph when tab is active"
  - "Graph node click → window.selectNodeByIri navigation"
affects:
  - folio_api/static/js/entity_graph.js (only file modified)
tech-stack:
  added: []
  patterns:
    - "Delegated click listener on .graph-nodes container (one bind per render, not per-node)"
    - "Three-layer re-fetch loop guard: self-click guard → _onEntitySelected dedupe → refreshFor dedupe"
    - "Selected-tree-LI as source-of-truth for current entity (.tree-node.selected[data-id])"
key-files:
  created: []
  modified:
    - folio_api/static/js/entity_graph.js
decisions:
  - "Source of truth for current entity is the .tree-node.selected[data-id] LI in the unified tree (no parallel state)"
  - "Self-click on selected graph node is a no-op (D-15) — re-rooting only happens via tree selection change"
  - "Tab-toggle while same graph already loaded is a no-op so pan/zoom is preserved (D-26 spirit)"
metrics:
  duration: ~80s
  completed: 2026-05-06T13:32:07Z
  tasks: 2
  files: 1
requirements: [GRAPH-03, GRAPH-05, GRAPH-12, GRAPH-18]
---

# Phase 01 Plan 12: Lazy-fetch lifecycle + graph-node click navigation Summary

Wire `onTabActivated()` lifecycle, replace the Plan 03 stub `_onEntitySelected` with a real refresh handler, and delegate graph-node clicks to `window.selectNodeByIri` so the entity-graph tab fetches lazily, refreshes on tree-driven entity changes, and lets the user navigate by clicking ancestors/children in the rendered graph.

## What Changed

### `folio_api/static/js/entity_graph.js`

**1. Real `_onEntitySelected(ev)` handler (replaces Plan 03 console-debug stub)**

```js
function _onEntitySelected(ev) {
  var detail = (ev && ev.detail) || {};
  if (state.activeTab !== 'graph') return;
  if (!detail.iri) return;
  if (detail.iri === state.currentIri && detail.type === state.currentType) return;
  refreshFor(detail.iri, detail.type).catch(...);
}
```

- **Lazy gate (D-10 / GRAPH-05):** early-return when tab is `details` → zero graph fetches during details-only sessions.
- **Re-fetch loop guard (RESEARCH Pitfall 7 / T-1-W3-05):** dedupes when `(iri, type)` matches the currently-rendered graph. This is the linchpin that breaks the otherwise-cyclic chain: graph-node click → `selectNodeByIri` → `entity:selected` → `_onEntitySelected` → `refreshFor` → `renderGraph` → graph-node click.
- **Defensive `!detail.iri`** check so a malformed event doesn't kick off a `fetch('/explore/api/entity-graph/undefined')`.

**2. New `onTabActivated()` lifecycle hook**

```js
function onTabActivated() {
  var sel = document.querySelector('.tree-node.selected[data-id]');
  if (!sel) { showEmpty(); return; }
  var iri = sel.getAttribute('data-id');
  var type = sel.getAttribute('data-type') || 'class';
  if (!iri) { showEmpty(); return; }
  if (state.currentIri === iri && state.graphData && state.graphData.layout) return;
  refreshFor(iri, type).catch(...);
}
```

**Selector for selected tree LI:** `.tree-node.selected[data-id]`. Verified against `unified_tree.js:179-182` (`selectNode` adds `class="selected"` to the LI) and `unified_tree.js:95` (LI markup carries `data-id` and `data-type`).

Three branches:
- **No selection** → `showEmpty()` (GRAPH-18 empty-state render).
- **Same graph already loaded** → no-op. Lets the user toggle Details ↔ Entity Graph without losing their pan/zoom (D-26 spirit; the previous transform stays mounted because `clearStates()` is only called inside `refreshFor`).
- **New entity OR first-time activation** → `refreshFor(iri, type)`.

**3. Exported on `window.EntityGraph`**

Added `onTabActivated: onTabActivated` to the public API. `unified_tree.js`'s `wireDetailTabs()` already invokes it on tab activation (line 354-358 of that file from Plan 05) — the export was the only missing piece for that wiring to work.

**4. Delegated graph-node click handler**

Inside `_mountGraph`, after `nodesDiv` is populated and before it is appended to the viewport:

```js
nodesDiv.addEventListener('click', function (ev) {
  var nodeEl = ev.target.closest && ev.target.closest('.graph-node');
  if (!nodeEl) return;
  if (ev.target.closest('.graph-node-children-btn')) return;
  if (ev.target.closest('.graph-node-hover-badge')) return;
  var iri = nodeEl.getAttribute('data-iri');
  if (!iri) return;
  if (iri === state.currentIri) return;          // self-click no-op (D-15)
  if (typeof window.selectNodeByIri === 'function') {
    window.selectNodeByIri(iri);
  } else if (window.console && window.console.warn) {
    window.console.warn('[EntityGraph] selectNodeByIri not available on window');
  }
});
```

- **One delegated listener per render**, not one per node — cheap and survives the wholesale `pane.innerHTML = ''` reset that `_mountGraph` performs at the start of every refresh.
- **Self-click guard:** `iri === state.currentIri` short-circuits before reaching `selectNodeByIri`. Spec-compliant with D-15.
- **+N control guards:** `closest('.graph-node-children-btn')` and `closest('.graph-node-hover-badge')` prevent the +N expansion controls from being interpreted as navigation. Plan 11 already calls `e.stopPropagation()` on those buttons, so this is belt-and-braces — but it future-proofs against a future markup change that omits the stopPropagation.

## Why this wires correctly (no infinite loop)

The full click cycle is:

```
[user clicks ancestor in graph]
  → nodesDiv delegated handler
  → window.selectNodeByIri(iri)
  → unified_tree.js selectNode(li)
  → li.addClass('selected') AND dispatchEvent(new CustomEvent('entity:selected', {detail:{iri,type}}))
  → entity_graph.js _onEntitySelected(ev)
      ├─ state.activeTab === 'graph' ✓ (we're in the graph tab to even see the click)
      ├─ detail.iri !== state.currentIri ✓ (clicked an *ancestor*, not self)
      └─ refreshFor(detail.iri, detail.type)
  → renderGraph rooted at the new entity
  → user sees ancestor's lineage; they may click further
```

The cycle terminates because (a) the rendered selected node has `iri === state.currentIri`, so the self-click guard fires before `selectNodeByIri`; and (b) even if it didn't, `_onEntitySelected`'s `(iri,type)` dedupe matches and aborts.

## Manual UAT (per VALIDATION.md steps 1-2 + 6 — to be performed by verifier)

1. Open `/explore/tree`, click 5 entities while staying on the Details tab → DevTools Network panel should show **0** `/explore/api/entity-graph/*` requests (lazy-fetch contract).
2. Click the **Entity Graph** tab → exactly **1** request fires for the currently-selected entity.
3. Click another entity in the tree → exactly **1** more request fires (refresh on entity change while tab active).
4. Switch back to **Details** → no further graph requests; switching back to Entity Graph re-renders the cached graph with no fetch (state.currentIri match short-circuits onTabActivated).
5. Click an ancestor inside the graph → tree scrolls and selects that ancestor; graph re-renders rooted at the new branch's ultimate root.
6. Click the *selected* graph node → nothing happens (D-15 self-click no-op).
7. Click the +N Children button on the selected node → children fan out, no navigation occurs (handler stopPropagation + closest() guard).
8. Open Entity Graph tab with no entity selected (e.g. fresh page load before clicking anything) → empty state renders ("No entity selected").

## Selector convention

The selector used to find the currently-selected tree LI is **`.tree-node.selected[data-id]`** — verified against `unified_tree.js`:
- Line 95: LI markup is `<li class="tree-node ${nodeClass}" data-id="${node.id}" data-type="${sectionType}">`.
- Line 181-182: `selectNode(li)` adds the `selected` class.
- Line 728: `$('.tree-node.selected').removeClass('selected')` confirms `.selected` is the canonical marker (only one selected at a time).

## Deviations from Plan

**None — plan executed exactly as written.** The plan's optional fallback to `window.currentEntity` was unnecessary because `unified_tree.js` already maintains a single `.tree-node.selected` LI with both `data-id` and `data-type` attributes, satisfying the selector route the plan recommended as primary.

## Verification

```bash
node --check folio_api/static/js/entity_graph.js          # exits 0
grep -q "function onTabActivated" entity_graph.js          # ✓
grep -q "showEmpty"            entity_graph.js              # ✓
grep -q "state.activeTab"      entity_graph.js              # ✓
grep -q "onTabActivated:"      entity_graph.js              # ✓ (export)
grep -q "selectNodeByIri"      entity_graph.js              # ✓ (delegated handler)
grep -q "graph-nodes"          entity_graph.js              # ✓
uv run pytest --no-cov                                     # 13 passed
```

## Commits

- `dd3a2df` feat(01-12): onTabActivated lifecycle + real entity:selected handler
- `a8ecf5d` feat(01-12): graph-node click delegates to selectNodeByIri

## Self-Check: PASSED

- folio_api/static/js/entity_graph.js exists and contains `function onTabActivated`, `selectNodeByIri`, `graph-nodes`, `state.activeTab` references.
- Both task commits present in `git log`.
- Test suite green (13/13).
