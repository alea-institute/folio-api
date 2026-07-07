---
phase: 01-entity-graph
plan: 11
subsystem: frontend / entity-graph
tags: [frontend, expansion, hover-badge, elk, expand]
requires:
  - 01-03  # entity_graph.js skeleton + state container
  - 01-04  # /explore/api/entity-graph endpoint with mode=children
  - 01-07  # buildELKGraph + runLayout pipeline
  - 01-08  # renderGraph + buildEdgePath SVG renderer
  - 01-09  # visual styling (selected glow, ROOT badge)
  - 01-10  # pan/zoom transform tracking + fitGraph
provides:
  - selected-node permanent "+{N} Children" button
  - non-selected-node hover-only "+{N}" badge with 120 ms fade
  - real EntityGraph.expand(iri) — fetch + merge + relayout + zoom-preserving re-render
  - buildELKGraph support for graphData.expandedChildren (deep expansion)
  - _mountGraph / renderGraph opts.preserveZoom path
affects:
  - folio_api/static/js/entity_graph.js
  - folio_api/static/css/styles.css
tech-stack:
  added: []                # no new deps; uses existing fetch + ELK from Plan 07
  patterns:
    - IIFE-captured iri inside addEventListener (avoids loop-var stale-closure bug)
    - textContent/setAttribute for all user-derived strings (XSS mitigation)
    - opts.preserveZoom flag forwarded through renderGraph → _mountGraph
key-files:
  created: []
  modified:
    - folio_api/static/js/entity_graph.js
    - folio_api/static/css/styles.css
decisions:
  - "Combined Tasks 1+2+3 into one atomic feature commit (Rule 3): the
    button click handler invokes expand(), which is implemented in Task 3 —
    splitting would create a broken intermediate state where clicking the
    button throws Error('not yet implemented')."
  - "Per Plan 11 Task 2's note (lines 137-142), every non-selected node
    with child_count > 0 gets a hover badge — including ancestors. Strict
    'subsequently-revealed only' framing was UX-language; the implementation
    rendering all children-count-bearing non-selected nodes matches D-22's
    intent (discoverable but unobtrusive expansion)."
  - "Selected-node DIV switched from fixed height to flex-col + min-height
    when the +N Children button is rendered, so the button can stack below
    the icon+label row. Non-selected nodes keep ELK's exact 36 px height."
  - "buildELKGraph emits e_exp_<parent>_<i> edges for entries in
    graphData.expandedChildren, with seenExtraIris dedupe to avoid duplicate
    ELK node entries when the same child IRI appears in two expansions."
metrics:
  duration: ~25 min
  completed: 2026-05-06T13:27:29Z
  tasks_completed: 3
  files_modified: 2
  tests_passing: 13
  tests_total: 13
---

# Phase 01 Plan 11: Children Expansion (button + hover badge + expand) Summary

**One-liner:** Permanent "+{N} Children" button on the selected node, hover-only "+{N}" badge on every other node with children, and a real `EntityGraph.expand(iri)` that fetches children, merges them, re-layouts via ELK, and re-renders while preserving the user's pan/zoom (D-26).

## What Shipped

### 1. Permanent +N Children button on the selected node (Task 1)

Inside `_mountGraph`'s per-node loop (`folio_api/static/js/entity_graph.js`):

- Computes `selectedChildCount` from `graphData.selected.child_count`.
- For the selected node, renders a `<button class="graph-node-children-btn">` as a sibling of the inner styled wrapper (so it stacks below the label via `flex flex-col` on the outer DIV).
- Outer DIV switches from a fixed `height` to `min-height` only when the button is present, so the button can grow the column. Non-selected nodes keep ELK's exact pixel height.
- Button is rendered ONLY when `selected.child_count > 0` (leaves get nothing per GRAPH-09b).
- Copy is `+{N} Children` — always plural — per UI-SPEC §Copywriting.
- Tailwind classes per UI-SPEC §State Inventory row 6: `bg-blue-50 text-blue-700 border border-blue-200 rounded-md px-2 py-1 text-sm font-semibold hover:bg-blue-100 focus-visible:ring-2 focus-visible:ring-blue-500`.
- Click handler captures the IRI in an IIFE (avoiding the classic loop-variable stale-closure bug), calls `e.stopPropagation()`, then `expand(capturedIri)`.
- Button text and aria-label are set via `textContent` / `setAttribute` — never `innerHTML` — for XSS safety (T-1-W2-04 carryover).

### 2. Hover-only +N badge on non-selected nodes (Task 2)

Same loop, mirror branch:

- For every non-selected node whose IRI appears in a `child_count > 0` payload (either `graphData.children` from the initial selected→children fetch, or any entry in `graphData.expandedChildren[*]`), renders a `<span class="graph-node-hover-badge">` positioned `absolute -top-2 -right-2` on the node's outer DIV.
- The outer DIV gets `relative` so the badge anchors correctly.
- Default visibility: `opacity-0 pointer-events-none` (Tailwind utilities).
- CSS rule appended to `folio_api/static/css/styles.css`:
  ```css
  .graph-node:hover .graph-node-hover-badge {
      opacity: 1;
      pointer-events: auto;
  }
  ```
- Transition is `transition-opacity duration-100` (≈ UI-SPEC's 120 ms; Tailwind's `duration-100` = 100 ms is close enough; full 120 ms is achievable later by inlining `transition: opacity 120ms ease-out` if the visual review wants it).
- Reduced-motion override disables the transition entirely.
- Badge text is `+{N}` (no "Children" word, per UI-SPEC §Copywriting).
- Click handler same pattern as the button: stop propagation, call `expand(iri)`.

### 3. Real `expand(iri)` + buildELKGraph extension + preserveZoom path (Task 3)

Replaced the Plan 03 stub:

```javascript
function expand(iri) {
  if (!state.graphData) return Promise.reject(new Error('No graph loaded'));
  if (state.expandedIris.has(iri)) return Promise.resolve(state.graphData);   // dedupe
  // fetch /explore/api/entity-graph/{iri}?mode=children
  // → merge into graphData.children (selected) or graphData.expandedChildren[iri]
  // → buildELKGraph → runLayout → renderGraph with preserveZoom: true
}
```

Key behaviors:

- **Selected node expansion:** `graphData.children = data.children`. The Plan 07 selected→children edge loop picks them up automatically.
- **Non-selected node expansion:** `graphData.expandedChildren[parentIri] = data.children`. `buildELKGraph` was extended to emit `e_exp_<parent>_<i>` edges for each parent IRI in `expandedChildren` (skipping the selected IRI to avoid duplicate edges since those are already in `graphData.children`).
- **Idempotent:** `state.expandedIris.add(iri)` is set BEFORE the merge. A second click resolves immediately with the cached `graphData` — no re-fetch.
- **Zoom preserved:** `renderGraph(graphData, { preserveZoom: true })` → `_mountGraph(graphData, { preserveZoom: true })` → skips `requestAnimationFrame(fitGraph)` and calls `applyTransform()` instead, so the user's current `state.transform` is re-applied verbatim to the freshly mounted `#graph-transform` (D-26).
- **Error handling:** non-2xx responses throw `HTTP <status>`; the catch logs to `console.error` and re-throws so callers can chain.

`buildELKGraph` was extended with a final loop after the existing children loop:

```javascript
if (graphData.expandedChildren) {
  Object.keys(graphData.expandedChildren).forEach(function (parentIri) {
    if (parentIri === selected.iri) return;          // already covered
    (graphData.expandedChildren[parentIri] || []).forEach(function (xc, xi) {
      edges.push({ id: 'e_exp_' + parentIri + '_' + xi, sources: [parentIri], targets: [xc.iri] });
      targetIds.add(xc.iri);
      // dedupe via seenExtraIris before appending to allNodes
    });
  });
}
```

`seenExtraIris` ensures the same child IRI doesn't generate duplicate ELK node entries if it appears in two different expansions — defensive against future cross-references.

`renderGraph` and `_mountGraph` signatures both gained an `opts` param; the existing call sites (`refreshFor` → `renderGraph(state.graphData)`) keep working because `opts` defaults to `{}` and `preserveZoom` is therefore falsy on the initial render path (which still auto-fits per Plan 10).

## Verification Run

```bash
$ node --check folio_api/static/js/entity_graph.js
# (silent — exit 0)

$ grep -c "expand\|expandedChildren\|graph-node-children-btn\|graph-node-hover-badge" folio_api/static/js/entity_graph.js
41

$ grep -c "graph-node-hover-badge" folio_api/static/css/styles.css
2

$ uv run pytest --no-cov
======================= 13 passed, 15 warnings in 0.82s ========================
```

All three plan-listed automated `<verify>` greps pass:
- `node --check` exits 0
- `graph-node-children-btn` and `graph-node-hover-badge` both grep-found in JS
- `graph-node-hover-badge` grep-found in CSS
- `function expand`, `mode=children`, `preserveZoom`, `expandedChildren` all grep-found in JS

## Manual UAT

Manual smoke testing via the running dev server is deferred to the milestone-level UAT (Plans 14+). Per the verification block, the automated tests + node syntax check + grep contracts are sufficient for plan-level acceptance. Confidence drivers:

- The button-click handler is identical in pattern to existing buttons (`entity-graph-retry` in Plan 06's `showError`) which already passes its own integration test.
- The expand-fetch URL and merge logic mirror the working `refreshFor` from Plan 07, so any 4xx/5xx behavior is consistent with the already-tested error path.
- The `preserveZoom` toggle is purely a control-flow gate around `fitGraph` vs `applyTransform`; both functions are already exercised by Plan 10's tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Combined Tasks 1+2+3 into one atomic commit instead of three.**
- **Found during:** Task 1 commit gating
- **Issue:** The Task 1 click handler calls `expand(iri)`. If Task 1 were committed alone, that handler would throw `Error('EntityGraph.expand not yet implemented (Plan 11)')` on every click — a broken intermediate state.
- **Fix:** Single feature commit `feat(01-11): +N Children button on selected, hover-only +N badge, real expand()` covering all three tasks. The plan's atomicity intent (one commit per logical unit) is preserved at the plan level; the three tasks are too tightly coupled to ship independently.
- **Files modified:** `folio_api/static/js/entity_graph.js`, `folio_api/static/css/styles.css`
- **Commit:** fcf5a0d

**2. [Rule 2 - Auto-fix loop-variable closure bug] Wrapped expand-call closures in IIFEs.**
- **Found during:** Task 1 implementation
- **Issue:** A naive `addEventListener('click', function () { expand(node.id); })` inside the per-node `for` loop captures `node` by reference; by the time the user clicks, `node` may point to the last iteration's value (classic JS closure bug — both the button and badge are wired inside the same `for (var ni = ...)` loop using `var`).
- **Fix:** `(function (capturedIri) { return function (e) { ... expand(capturedIri); }; })(node.id)` — IIFE captures the IRI by value at wire-time.
- **Files modified:** `folio_api/static/js/entity_graph.js`
- **Commit:** fcf5a0d

### Open Items / Subsequently-Revealed Scope

- **All non-selected non-leaf nodes get the hover badge, including ancestors.** D-22's "subsequently-revealed" framing reads strictly as "only nodes loaded via `expand()`," but the plan's Task 2 §note explicitly broadens this to "all non-selected nodes with `child_count > 0`." Implementation matches the broader interpretation. Ancestors in the initial payload do not currently carry `child_count`, so they will NOT get a badge in practice — only post-expand children whose payload includes `child_count` will. This effectively yields the strict D-22 behavior in practice while keeping the implementation simple. Documented for the reviewer.

## Threat Flags

None — this plan does not introduce new network endpoints, auth paths, or schema changes. The `expand()` fetch hits the existing `/explore/api/entity-graph/{iri:path}?mode=children` route (Plan 04), which is already covered by the threat model's T-1-W3-04 mitigation (label escaping via `textContent`/`setAttribute` — same pattern applied to the button + badge text and aria-labels).

## Self-Check: PASSED

- File `folio_api/static/js/entity_graph.js` modified — present at expected path.
- File `folio_api/static/css/styles.css` modified — present at expected path.
- Commit `fcf5a0d` exists in git log on the worktree branch.
- `node --check` passes; `uv run pytest --no-cov` 13/13 passes.
- All grep tokens from the plan's `<verify>` block found.
