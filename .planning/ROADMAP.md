# Milestone v1.1 — Entity Graph Roadmap

**Goal:** Ship the ancestor-rooted, cubic-bezier entity graph on `/explore/tree`, ported from folio-enrich and hidden behind a `Details | Entity Graph` tab.

**Phase numbering:** Continues from milestone v1.0 (which had a single phase). v1.1 starts at **Phase 1** of this milestone.

**Total: 1 phase** | **20 requirements** | **All covered ✓**

---

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Entity Graph | Port folio-enrich's ELK + cubic-bezier graph into folio-api with a `Details \| Entity Graph` tab, full-screen modal, ancestors-only default render, `+N Children` opt-in expansion, click-to-select-in-tree, distinct styling for the topmost ancestor and selected node, skeleton/empty/error states, and < 500ms initial render | GRAPH-01–05, 07–14, 15–20, plus GRAPH-09b (20) | 7 (see below) |

---

## Phase Details

### Phase 1: Entity Graph

**Goal:** A user browsing `/explore/tree` can click `Entity Graph` in the right pane and see the selected entity rendered as a hierarchical SVG graph rooted at its topmost ancestor, expand any node's children inline, click nodes to navigate the tree, and pop the graph to full-screen — all without disturbing the existing tree-browsing UX.

**Requirements covered:**

- GRAPH-01 — Ancestor-rooted graph in detail pane
- GRAPH-02 — Full-screen modal toggle, state preserved
- GRAPH-03 — Click graph node → select IRI in tree
- GRAPH-04 — `+N Children` opt-in expansion (renders ALL children of clicked node)
- GRAPH-05 — Lazy fetch on tab activation only
- GRAPH-07 — Default rooted at oldest ancestor
- GRAPH-08 — Cubic-bezier edges (90° entry/exit)
- GRAPH-09 — Default contents = ancestors only (no children); selected node has permanent `+N Children` button
- GRAPH-09b — Subsequently-revealed nodes use hover-only `+N Children` badges
- GRAPH-10 — `GET /api/entity-graph/{iri_hash}` JSON endpoint
- GRAPH-11 — `Details | Entity Graph` tab UI
- GRAPH-12 — Refresh on entity reselect
- GRAPH-13 — Drag-pan + scroll-zoom
- GRAPH-14 — < 500ms initial render; auto-fit zoom
- GRAPH-15 — Heroicons `tag` (class) and `link` (property) icon prefixes
- GRAPH-16 — Selected node = thick blue border + subtle glow
- GRAPH-17 — Topmost ancestor gets distinct "root" styling
- GRAPH-18 — Empty state hint when no entity selected
- GRAPH-19 — Skeleton graph while fetching/laying out
- GRAPH-20 — Inline error + Retry on fetch failure

**Success criteria (observable user behaviors):**

1. User can browse `/explore/tree` exactly as before; the new graph is invisible until the `Entity Graph` tab is clicked.
2. Clicking the `Entity Graph` tab on a selected entity shows that entity rooted at its topmost FOLIO ancestor, with the full chain descending; the topmost ancestor is visually distinct and the selected node is highlighted with a thick blue border + glow. Classes show a tag icon, properties a chain icon. **No children are rendered by default.** The selected node displays a permanent `+N Children` button (e.g., `+12 Children`).
3. User can click `+N Children` on the selected node and see ALL N children render inline; subsequently-revealed nodes that have further children show a `+N Children` badge on hover only; clicking that recursively renders their children.
4. User can click any node in the graph and the left tree scrolls to and selects that IRI (graph then refreshes rooted at the new selection's topmost ancestor; previously expanded children are not preserved across selections).
5. User can click `⛶ Full screen` to expand the graph to a viewport modal; pan/zoom/expanded children persist across the in-pane ↔ full-screen swap.
6. Edges are visually cubic-bezier curves (smooth S-shape, not straight lines).
7. Empty / loading / error states each render correctly: hint message when no entity selected; skeleton during fetch; inline error + Retry on backend failure. Initial graph render completes in < 500ms for typical FOLIO entities.

**Donor reference (port targets):**

- `folio-enrich/frontend/index.html` lines 8809–8840 → `buildELKGraph()`
- `folio-enrich/frontend/index.html` lines 8855–8974 → `renderGraph()`
- `folio-enrich/frontend/index.html` lines 8976–8990 → `buildEdgePath()` (copy verbatim)
- `folio-enrich/frontend/index.html` lines 9036–9048 → pan/zoom transform tracking
- `folio-enrich/frontend/index.html` lines 1130–1170 → CSS (port to Tailwind tokens)

**Dependencies:** None. Backend endpoint is the only new server work; frontend port is independent.

---

## Phase order

Single-phase milestone — no ordering decisions needed.
