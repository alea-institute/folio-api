---
phase: 01-entity-graph
plan: 05
subsystem: explore-tree-detail-pane
tags: [frontend, tabs, html-structure, custom-events, aria, tablist]
requirements: [GRAPH-05, GRAPH-11, GRAPH-12]
dependency-graph:
  requires: [01-03]
  provides: [tab-strip-dom, entity:selected-event, wireDetailTabs, EntityGraph.state.activeTab]
  affects: [06, 07, 08, 09, 10, 11, 12, 13]
tech-stack:
  added: []
  patterns: [aria-tablist, custom-event-pubsub, defensive-DOM-guards]
key-files:
  created: []
  modified:
    - folio_api/templates/jinja2/explore/tree.html
    - folio_api/static/js/unified_tree.js
decisions:
  - Tab swap toggles `.hidden` class + HTML5 `hidden` attr — never destructive DOM moves (D-06)
  - `entity:selected` CustomEvent placed at end of `selectNode()` so subscribers see post-loadDetails state
  - Dispatch covers both selectNode and selectNodeByIri (latter ultimately routes through selectNode)
  - Defensive try/catch on dispatch — graph wiring is additive, never load-bearing for detail card
  - `wireDetailTabs` boots on DOMContentLoaded and is idempotent against missing DOM (returns early)
  - `EntityGraph.onTabActivated` hook is called only when activating Graph tab; Plan 12 will implement it
metrics:
  duration: ~12min
  completed: 2026-05-06
---

# Phase 01 Plan 05: Detail-pane Tab Strip + entity:selected Wiring Summary

Added Details / Entity Graph tab strip to `/explore/tree`'s detail pane and wired `entity:selected` CustomEvent dispatch so the Wave 0 graph module skeleton (Plan 01-03) can subscribe to tree-selection changes without `unified_tree.js` knowing about graphs.

## What Shipped

### Tab strip DOM (tree.html)

The interior of `#detail-container` is now:

```
div#detail-container
├── div#detail-tabs role=tablist aria-label="Detail view"
│   ├── button#tab-details role=tab aria-selected=true tabindex=0      → "Details"
│   └── button#tab-graph   role=tab aria-selected=false tabindex=-1   → "Entity Graph"
└── div#tab-panels.flex-grow.flex.flex-col.overflow-hidden
    ├── div#tab-panel-details role=tabpanel aria-labelledby=tab-details
    │   └── div#class-details (ORIGINAL CONTENT preserved byte-for-byte)
    └── div#tab-panel-graph role=tabpanel aria-labelledby=tab-graph .hidden hidden
        └── div#entity-graph-pane (empty placeholder for later plans)
```

**Tailwind classes (verbatim per UI-SPEC §State Inventory):**

- Tab strip container: `flex border-b border-gray-300 mb-3 -mx-3 px-3 bg-white sticky top-0 z-20`
- Active tab: `px-4 py-2 text-sm font-semibold border-b-2 border-blue-600 bg-white text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2`
- Inactive tab: `px-4 py-2 text-sm font-semibold border-b-2 border-transparent bg-gray-100 text-gray-600 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2`
- Details panel: `flex-grow overflow-y-auto`
- Graph panel: `flex-grow overflow-hidden hidden` + bare `hidden` attribute as defensive default
- Entity-graph pane: `w-full h-full bg-white relative`

**Copy:** "Details" and "Entity Graph" exactly (matches UI-SPEC §Copywriting).

**No deviation from UI-SPEC.**

### selectNode dispatch (unified_tree.js)

Added at end of `selectNode(li, updateUrl)`:

```js
try {
    var _iri  = (typeof li !== 'undefined' && li && li.data) ? li.data('id') : null;
    var _type = (typeof li !== 'undefined' && li && li.data) ? li.data('type') : null;
    if (_iri) {
        document.dispatchEvent(new CustomEvent('entity:selected', {
            detail: { iri: _iri, type: _type }
        }));
    }
} catch (e) {
    if (window.console && window.console.warn) {
        window.console.warn('entity:selected dispatch failed:', e);
    }
}
```

The defensive try/catch keeps legacy detail-card flow load-bearing — if the dispatch ever throws (e.g. unexpected `li` shape), the warning logs but selection still works.

**D-11 coverage:** `selectNodeByIri()` ultimately routes through `selectNode()` via `loadAndSelectNode()` in all branches (DOM-found nodes call `selectNode(li, true)` directly at line 258; path-loaded nodes call `selectNode(loadedNode, updateUrl)` inside `loadAndSelectNode`). Therefore dispatching from `selectNode` alone covers both code paths. The single fallback `loadDetails(iri, 'class', true)` at line 291 fires only when neither path API can locate the IRI — an error edge case where graph refresh is moot since the tree never selects anything.

### wireDetailTabs (unified_tree.js)

A new function inserted before `window.selectNodeByIri = selectNodeByIri;`:

- Looks up the four tab/panel ids; returns silently if any are missing (page without tabs)
- `activate(which)` swaps panel visibility via `.hidden` class + HTML5 `hidden` attr, updates aria-selected + tabindex, swaps the active/inactive className strings
- Click handlers on both tabs call `activate('details' | 'graph')`
- Arrow-Left / Arrow-Right key handlers cycle between the two tabs and refocus the newly active button (standard ARIA tablist pattern)
- Updates `window.EntityGraph.state.activeTab` to `'details' | 'graph'` if EntityGraph is loaded
- Calls `window.EntityGraph.onTabActivated()` only when activating Graph tab AND the function exists (defensive — Plan 12 wires this)
- Boots on DOMContentLoaded (or immediately if already loaded)

## Verification

### Automated checks (all green)

```
$ node --check folio_api/static/js/unified_tree.js   → exit 0 (parses)
$ grep -q 'id="detail-tabs"'                          → match
$ grep -q 'id="tab-graph"'                            → match
$ grep -q 'id="entity-graph-pane"'                    → match
$ grep -q 'role="tablist"'                            → match (1x)
$ grep -c 'role="tabpanel"' tree.html                 → 2
$ grep -c "wireDetailTabs"                            → 3 (decl + DOMContentLoaded + else-call)
$ grep -c "entity:selected"                           → 3 (1 dispatch + 2 comments)
$ grep -c "dispatchEvent(new CustomEvent('entity:selected'" → 1
$ grep -c "window.selectNodeByIri = selectNodeByIri;" → 1 (preserved)
```

### #class-details preservation (git diff inspection)

The original `#class-details` div content (the placeholder svg + "Search or Browse Items" heading) is preserved byte-for-byte; the diff for tree.html shows only insertions wrapping that block, no edits inside. The `loadDetails()` `getElementById('class-details').innerHTML = …` contract is preserved — the same id remains on the same inner div.

### Manual smoke (recommended before merge)

1. Run `uv run uvicorn folio_api.api:app` and open `/explore/tree`.
2. Confirm Details tab is active by default; placeholder card is visible.
3. Click "Entity Graph" tab — Details panel hides, Graph panel becomes visible (empty white pane until later plans add rendering).
4. Click "Details" — entity card returns unchanged.
5. Press Arrow-Right while focused on a tab — focus + active state cycle.
6. In DevTools console: `document.addEventListener('entity:selected', e => console.log(e.detail))` then click any tree node — confirm `{iri, type}` payload logs.
7. With `entity_graph.js` loaded (Plan 03 skeleton), click Graph tab and confirm `window.EntityGraph.state.activeTab === 'graph'`.

## Deviations from Plan

None — plan executed exactly as written. All Tailwind classes, ARIA attributes, copy, and event semantics match UI-SPEC and the plan body.

## Self-Check: PASSED

- `folio_api/templates/jinja2/explore/tree.html` modified — FOUND
- `folio_api/static/js/unified_tree.js` modified — FOUND
- Commit `7016f0d` (Task 1) — FOUND in branch
- Commit `82c3bd6` (Task 2) — FOUND in branch
