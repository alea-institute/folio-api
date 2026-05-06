# Milestone v1.1 — Entity Graph Requirements

**Goal:** Add an ancestor-rooted entity graph (cubic-bezier SVG, ELK layout) to `/explore/tree`, ported from folio-enrich. Hidden behind a `Details | Entity Graph` tab so default tree-browsing UX is unchanged.

**Donor:** `folio-enrich/frontend/index.html` lines 8750–9232 (graph code) + lines 8976–8990 (`buildEdgePath()` cubic-bezier math).

---

## v1.1 Requirements

### Graph rendering

- [ ] **GRAPH-01**: User can view selected entity in an ancestor-rooted hierarchical graph rendered as cubic-bezier SVG inside the right detail pane
- [ ] **GRAPH-02**: User can pop the graph out to a full-screen modal overlay and back without losing graph state (pan/zoom/expanded nodes preserved)
- [ ] **GRAPH-07**: Graph is rooted at the topmost ancestor of the selected node and descends toward it ("go to oldest ancestor" default load)
- [ ] **GRAPH-08**: Edges are rendered as cubic-bezier curves with 90° entry/exit (matches folio-enrich `buildEdgePath()`)

### Graph contents & data

- [ ] **GRAPH-04**: User can expand a node's hidden children via a `+N Children` affordance, merging ALL of that node's children into the live graph without re-rendering existing nodes
- [ ] **GRAPH-09**: Default contents = **full ancestor chain to root only** (no children rendered by default); selected node always shows a permanent `+N Children` button with count visible
- [ ] **GRAPH-09b**: Subsequently-revealed nodes (after a `+N` click) show a hover-only `+N Children` badge on mouseover when their `child_count > 0`; leaves show no affordance
- [ ] **GRAPH-10**: Backend exposes `GET /api/entity-graph/{iri_hash}` returning JSON with `selected`, `ancestors[]` (root-first), and `children[]` (with `child_count` for each)

### Graph activation & UX

- [ ] **GRAPH-05**: Graph data is fetched only when the user activates the `Entity Graph` tab — not on every entity selection
- [ ] **GRAPH-11**: Right detail pane gains a `Details | Entity Graph` tab UI; graph replaces the entity card while the graph tab is active; switching back restores the card unchanged
- [ ] **GRAPH-12**: When the graph tab is active and the user selects a different entity in the left tree, the graph refreshes for the newly selected entity (rooted at its topmost ancestor)

### Graph navigation

- [ ] **GRAPH-03**: User can click any node in the graph to select that IRI in the left tree (reuses `selectNodeByIri()`); graph then refreshes per GRAPH-12
- [ ] **GRAPH-13**: User can drag-pan the graph canvas and scroll-to-zoom
- [ ] **GRAPH-14**: Graph initial render is < 500ms from tab activation to first paint; canvas auto-fits the full ancestor chain to viewport on initial render

### Visual identity

- [ ] **GRAPH-15**: Class nodes render with a Heroicons `tag` icon prefix; property nodes render with a Heroicons `link` icon prefix (inline SVG, no asset fetch)
- [ ] **GRAPH-16**: The currently-selected node is highlighted with a 2px blue border + subtle outer glow (no fill change, no animation)
- [ ] **GRAPH-17**: The topmost FOLIO ancestor in any rendered chain receives distinct visual styling (slightly larger / bolder + small "root" label or badge)

### UI states

- [ ] **GRAPH-18**: When the Graph tab is opened without an entity selected, a centered hint message ("Select an entity in the tree to see its graph") + small inline illustration display
- [ ] **GRAPH-19**: While a graph is being fetched and laid out, a skeleton (3–4 faded grey ancestor-stack rectangles with subtle pulse) displays in place of the eventual graph
- [ ] **GRAPH-20**: If the `/api/entity-graph/{iri_hash}` request fails, an inline error box ("Couldn't load graph for [Entity Name]") with a `Retry` button displays in the graph pane; user remains on the Graph tab

---

## Future Requirements

<!-- Captured during discuss phase but deferred -->

- Pan/zoom button controls + minimap UI (folio-enrich has these; defer until requested)
- Edge labels showing relationship type (`subClassOf`, `sub_property_of`)
- Mobile gesture support for full-screen graph
- Server-side caching for `/api/entity-graph/{iri}` (premature — folio-python is in-memory)
- Vendoring elkjs into `static/` instead of CDN (CDN is fine for v1.1)

---

## Out of Scope

<!-- Explicit exclusions with reasoning -->

- **Re-introducing `/properties/tree` and `/taxonomy/tree`** — Removed in v1.0 (commit `e28c82c`). Unified explore is sufficient.
- **Replacing the existing tree on the left** — The graph is an additive view, not a replacement. Tree remains the primary navigation.
- **Persistent graph state across sessions** — Per-session in-memory only; reload resets. Cookie/localStorage persistence is unjustified complexity.
- **Editing the ontology from the graph** — folio-api is read-only. Authoring tools live in folio-enrich / ontokit.
- **Adding ReactFlow / D3** — Stack constraint: jQuery + vanilla JS only. ELK + hand-rolled SVG is the right tool.

---

## Traceability

<!-- Filled by ROADMAP.md -->

| REQ-ID  | Phase                      |
|---------|----------------------------|
| GRAPH-01 through GRAPH-20 | Phase 1 — Entity Graph |
