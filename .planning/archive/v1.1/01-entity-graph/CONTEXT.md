# Phase 1: Entity Graph — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Add an entity-graph visualization to `/explore/tree` ported from folio-enrich. The graph renders the selected entity rooted at its topmost FOLIO ancestor, descending to it, plus the entity's 1-hop direct children. It lives behind a `Details | Entity Graph` tab inside the existing right detail pane (replacing the entity card while active) and can pop out to a full-screen modal. Default tree-browsing UX is unchanged — graph data only loads when the user activates the tab. Out of scope: replacing the existing left tree, edge labels, pan/zoom buttons + minimap, mobile gestures, server-side caching.

</domain>

<decisions>
## Implementation Decisions

### Donor source

- **D-01:** Port from `folio-enrich/frontend/index.html` (lines 8750–9232) — same stack (FastAPI + jQuery + vanilla JS), cubic-bezier already implemented in `buildEdgePath()` (lines 8976–8990). Folio-mapper (React) and ontokit-web (ReactFlow) are stack-mismatch and explicitly rejected as donors.
- **D-02:** Functions to copy/adapt from folio-enrich:
  - `buildELKGraph()` lines 8809–8840 — adapt node-list builder to folio-api's data model (selected node + ancestors + children with `child_count`)
  - `renderGraph()` lines 8855–8974 — extract from global state (`_graphData`, `_graphTransform`, `_graphExpandedNodes`); parameterize on a passed-in graph data object
  - `buildEdgePath()` lines 8976–8990 — copy **verbatim**; direction-agnostic cubic bezier
  - Pan/zoom transform tracking lines 9036–9048
  - CSS lines 1130–1170 — port to Tailwind tokens; reuse existing blue palette (`bg-blue-50 / text-blue-700 / border-blue-200`) from milestone v1.0

### Layout engine

- **D-03:** `elkjs@0.11.1` from CDN (matches folio-enrich exactly). Lazy-loaded on `/explore/tree` only, not on every folio-api page. CDN choice: jsdelivr or unpkg — researcher to confirm which folio-enrich uses.
- **D-04:** Layered top-to-bottom layout. Ancestors rendered as a vertical stack above the selected node (root at top, immediate parent just above selected). Children laid out below the selected node in tiers.

### Trigger UI

- **D-05:** `Details | Entity Graph` tab strip at the top of the right detail-pane container in `explore/tree.html`. Tabs are simple buttons with active-state styling — no jQuery UI tabs widget. Switching tabs swaps the visible panel via `.hidden` Tailwind class.
- **D-06:** Graph **replaces** the entity card while the Graph tab is active (not stacked, not bottom drawer, not new column). Switching back to Details restores the card with current selection unchanged.
- **D-07:** Full-screen mode = **modal overlay** (full viewport modal with X close + ESC dismiss). Single graph renderer, two host elements — DOM-swap the `#entity-graph-pane` between the in-pane container and the modal so state (pan/zoom/expanded children) is preserved across toggle.

### Graph contents & data fetch

- **D-08 [REVISED, Round 3+4]:** Default contents = **full ancestor chain to root only**. The selected node is rendered at the bottom of the chain with a permanent `+N Children` button. **Children are NOT rendered by default**, regardless of how many or how few children the selected node has. Children load only when the user clicks the `+N Children` button on the selected node — at which point **all** N children render at once (no pagination). This supersedes the original D-08 (which said "ancestors + 1-hop children"); rationale: keeps the default render small and snappy (D-25), keeps the focus on the "oldest ancestor" lineage framing, and matches the user's "session-only opt-in" mental model.
- **D-09 [REVISED, Round 2+3]:** Affordance behavior:
  - **Selected node:** always shows a permanent `+N Children` button with the count visible (e.g. `+12 Children`). Click → fetches and renders ALL children inline.
  - **Subsequently-revealed nodes** (children loaded after a +N click): each carries a `child_count`. Nodes where `child_count > 0` show a **hover-only** `+N Children` badge that appears on mouseover (per Round 2). Click → fetches and renders ALL of THAT node's children inline. Recursive use of the same endpoint.
  - **Leaves** (`child_count === 0`): no badge, no hover affordance.
- **D-10:** Lazy fetch — graph data is fetched ONLY when the user activates the `Entity Graph` tab. If a user clicks 30 entities while the Details tab is active, zero graph requests fire. When they finally click the Graph tab, fetch fires once for the currently selected entity.
- **D-11:** On tree-selection change while Graph tab is active → refresh the graph (fetch new data, re-render rooted at the new selection's topmost ancestor). Pan/zoom resets per refresh. Previously-expanded children are NOT preserved across selections (each selection is a fresh graph).

### Visual node styling [Round 2]

- **D-19:** **Type differentiation = icon prefix** at the left edge of each node label. Classes get a "tag" icon; properties get a "link" (chain) icon. Source: **Heroicons** (Tailwind's MIT-licensed icon set) — inline SVG `path` data embedded directly in `entity_graph.js`, no extra dependency, no asset fetch. Same color palette for both types (Tailwind blue from v1.0).
- **D-20:** **Selected node highlight = thick border + subtle glow.** 2px solid blue border (`border-blue-600`) + soft outer `box-shadow` (`shadow-[0_0_12px_rgba(37,99,235,0.35)]` or equivalent). No fill change, no animation. Selected node visually "pops" without color shift.
- **D-21:** **Topmost ancestor (root) gets distinct styling.** Adopt folio-enrich's `branch_root_type: 'ultimate'` pattern (folio-enrich line 8882) for the topmost FOLIO ancestor in any rendered chain — slightly larger font, bolder weight, and a small badge or label ("root" or similar). Reinforces the "go to oldest ancestor" framing visually.
- **D-22:** **Expandable nodes (subsequently-revealed) = hover-only `+N Children` badge.** No permanent chevron, no always-visible badge. Discoverable but unobtrusive. (The selected node's `+N Children` button is the exception — it's permanent per D-09.)

### Scale & rendering limits [Round 3]

- **D-23:** **Deep ancestor chains = render all, user pans.** No truncation, no "+N more ancestors" compression. If a node has 15+ ancestors, the graph extends vertically and the user drag-pans up to see them. Combined with D-26 (zoom-to-fit), even very deep chains are visible on initial render at a wider zoom.
- **D-24:** **Wide children handling = no children by default; click `+N Children` renders ALL.** No pagination, no "show first 12" cap, no filter input. If the user expands a node with 50 children, all 50 render. Consequence: the user opted into the layout cost by clicking; render time may exceed D-25's budget for very wide expansions, which is acceptable.
- **D-25:** **Initial render performance budget = < 500ms (snappy).** "Initial render" = from `+Entity Graph` tab click to first paint of laid-out graph. Achievable because default contents are ancestors-only (D-08), which is a small node count for most FOLIO entities. After-expansion render time is best-effort, not gated.
- **D-26:** **Initial zoom = zoom-to-fit (whole graph visible).** Canvas auto-fits so the full ancestor chain + selected node fit in the pane on first render. User scroll-zooms in to read details. After expansion (`+N Children` clicked), do NOT re-fit — preserve the user's zoom level so they don't lose their place.

### UI states [Round 4]

- **D-27:** **Empty state (no entity selected when Graph tab opens).** Centered hint text: *"Select an entity in the tree to see its graph"* + a small inline illustration (lightweight SVG; could be a simple stylized graph icon). No auto-selection, no recent-entities tile picker.
- **D-28:** **Loading state (graph fetch + ELK layout in flight).** Skeleton graph: 3–4 faded grey rounded rectangles stacked vertically (mimicking the eventual ancestor stack), with a subtle pulse animation. Anchors visual continuity — user sees the shape of what's coming, not a generic spinner.
- **D-29:** **Error state (fetch fails / 5xx / malformed data).** Red-tinted inline error box in the graph pane: *"Couldn't load graph for [Entity Name]"* with a `Retry` button. User stays on the Graph tab (no auto-fall-back to Details). Console error logged for devtools as well.

### Backend endpoint

- **D-12:** New endpoint: `GET /api/entity-graph/{iri_hash}` returning JSON:
  ```json
  {
    "selected": { "iri": "...", "label": "...", "type": "class|property" },
    "ancestors": [/* root-first → immediate parent last */],
    "children":  [/* {iri, label, type, child_count} */]
  }
  ```
  Implementation walks `subClassOf` / `sub_property_of` upward via `folio-python` until a top-class/top-property terminator. Children are looked up via the same inverse-lookup pattern already used in `folio_api/routes/properties.py:_get_child_properties` (line ~98).
- **D-13:** Endpoint location: planner to choose between adding to existing `folio_api/routes/explore.py` or a new `folio_api/routes/graph.py`. Either is acceptable; lean toward `explore.py` if the route is small.
- **D-14:** No server-side cache (deferred — `folio-python` is in-memory; no DB hit).

### Graph node click behavior

- **D-15:** Clicking any non-selected node in the graph calls existing `selectNodeByIri()` in `unified_tree.js` (line ~253) → left tree scrolls/selects → graph refreshes per D-11. **No re-rooting without tree selection** — the tree is always the source of truth for "what's selected".

### Pan / zoom

- **D-16:** Drag-to-pan and scroll-to-zoom only (matches folio-enrich's basic interactions). No buttons, no minimap. Implemented via the same transform-matrix approach as folio-enrich:9036–9048.

### Persistence

- **D-17:** No persistence across sessions. Graph state (pan, zoom, expanded children) is in-memory only and resets on page reload or new entity selection.
- **D-30 [Round 5]:** **No URL deep-linking.** The graph is purely session-state. `/explore/tree?graph=<iri>` is NOT a supported entry point. Users share entity links the existing way (whatever folio-api's current entity-URL convention is); the recipient opens the Graph tab manually. Browser URL never updates as the user navigates within the graph. Rationale: keeps the surface small for v1.1; deep-linking can be added in a future milestone if user demand emerges.

### Scope

- **D-18:** Only `/explore/tree`. The `/properties/tree` and `/taxonomy/tree` routes were removed in milestone v1.0 (commit `e28c82c`); they don't need entity-graph support.

### Claude's Discretion

(Most items previously listed here were resolved in discuss Rounds 2–5. The remaining open items:)

- Exact endpoint path mounting (in `explore.py` vs new `graph.py`) — either is fine.
- IRI-hashing scheme for the URL parameter — match whatever pattern existing routes use (likely an MD5 or short slug already established).
- Whether to vendor or CDN-load `elkjs` — D-03 says CDN; if researcher finds CDN reliability concerns, vendor is acceptable.
- Exact Heroicons SVG path strings to inline (D-19) — pick the current Heroicons v2 `tag` and `link` outline variants; researcher can pull the exact paths.
- Tab styling micro-decisions (underline vs pill, hover/focus states) — match Tailwind blue palette from v1.0.
- Skeleton graph node count and animation tempo (D-28) — small UX tuning, choose by feel.
- Empty-state illustration (D-27) — lightweight inline SVG, no asset fetch.
- ELK config knobs (`elk.algorithm`, spacing, edge routing) — start with folio-enrich's exact config and tune if layout looks off.

</decisions>

<specifics>
## Specific Ideas

- "Use the same type of entity graph that I used in FOLIO Mapper, FOLIO Enrich, Ontokit. Complete with bezier curves." — User's PRD. Donor source confirmed: folio-enrich (closest stack match; mapper and ontokit are React).
- "Hide the Entity Graph behind a panel, so it does not display every single time you select a new entity. But if the user clicks the pane 'Entity Graph' the end of the graph will appear, first in a pane, and able to be expanded to full screen." — User's PRD. Resolved as `Details | Entity Graph` tab + full-screen modal toggle.
- "Like the other entity graphs above, please keep the same 'go to oldest ancestor' behavior." — User's PRD. Resolved (D-08, D-21, D-26) as: default load = pure ancestor chain rooted at the topmost FOLIO ancestor; that ancestor gets distinct visual styling; canvas zooms-to-fit so the full chain is visible.
- "Reuse as much of the code as you're able, as will fit in the FOLIO Tree's codebase." — User's PRD. Reflected in D-01/D-02: `buildEdgePath()` copied verbatim; `buildELKGraph()` and `renderGraph()` adapted (extract from global state, parameterize on passed-in data); CSS palette swapped to Tailwind tokens.
- User added freeform on contents: "+N Children" affordance to expand children through an explicit click. Strengthened in Round 3 to **"+N is the ONLY way to see children"** — the default render shows ancestors only (D-08, D-09). Pure lineage view by default, branchy expansion on demand.
- User specified Round 2 icons by name: "Tag for classes, chain link for properties." Resolved as Heroicons `tag` + `link` (D-19).
- User explicitly chose folio-enrich's `branch_root_type: 'ultimate'` styling for the topmost ancestor (D-21) — reinforces the "oldest ancestor" framing visually.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context

- `.planning/PROJECT.md` — Project goals, constraints, key decisions
- `.planning/REQUIREMENTS.md` — All 13 GRAPH-NN requirements for milestone v1.1
- `.planning/ROADMAP.md` — Phase 1 success criteria

### Donor code (must read before planning the port)

- `../folio-enrich/frontend/index.html` lines **8750–9232** — Entity graph implementation (ELK + cubic-bezier SVG)
  - Lines **8809–8840** — `buildELKGraph()` — adapt
  - Lines **8855–8974** — `renderGraph()` — adapt (extract from global state)
  - Lines **8976–8990** — `buildEdgePath()` — **copy verbatim**
  - Lines **9036–9048** — Pan/zoom transform tracking
  - Lines **1130–1170** — CSS (port to Tailwind tokens)

### Existing folio-api integration points

- `folio_api/templates/jinja2/explore/tree.html` — Tab UI gets added inside the right detail-pane container
- `folio_api/static/js/unified_tree.js` — `selectNode()` (line ~179) and `selectNodeByIri()` (line ~253) are the integration points
- `folio_api/routes/explore.py` — Likely home for the new `/api/entity-graph/{iri_hash}` endpoint
- `folio_api/routes/properties.py` lines ~77–103 — Reference pattern for parent/descendant traversal via `folio-python`

### Reference patterns (read for context, not direct port)

- `../folio-mapper/packages/ui/src/components/mapping/ConceptDAG.tsx` — Quadratic-bezier React DAG; not a port target but informative for the affordance UX
- `../ontokit-web/components/graph/OntologyGraph.tsx` — ReactFlow + ELK graph; not a port target but informative for the layered ELK config

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`selectNode(li)`** in `unified_tree.js:~179` — Existing tree-node click handler. Hook into it to refresh the graph if the Graph tab is active.
- **`selectNodeByIri(iriHash)`** in `unified_tree.js:~253` — Selects a tree node by IRI hash. Reused as the destination of graph-node clicks (D-15).
- **`folio-python` in-memory ontology** — Already loaded via FastAPI startup. Provides `subClassOf` / `sub_property_of` traversal needed for the new endpoint without any new data layer.
- **`_get_child_properties()`** in `folio_api/routes/properties.py:~98` — Reference implementation for inverse-lookup of children. Pattern to mirror for the new endpoint's children list.
- **Tailwind blue palette** from v1.0 — `bg-blue-50 / text-blue-700 / border-blue-200` for tab buttons, graph node borders, and `+N Children` badges.

### Established Patterns

- **Right detail pane** is currently a single `#class-details` div populated via fetch on `selectNode`. Tab UI wraps this without changing the existing fetch flow.
- **Static JS files** live in `folio_api/static/js/` and are referenced from templates via `<script src="...">`. New `entity_graph.js` follows this pattern; no bundler.
- **No build step for JS** — vanilla files served directly. Avoid adding webpack/vite.
- **Jinja2 templates inline small CSS** — graph-specific CSS can either go in `static/css/` (compiled Tailwind output) or inline in the template. Inline is acceptable for the modal styles since they're page-specific.

### Integration Points

- `explore/tree.html` — Wrap right-pane container with tab strip and modal shell
- `unified_tree.js` — Add tab-switch handler + hook into `selectNode()` for graph refresh
- `entity_graph.js` (NEW) — Self-contained renderer module; exports `EntityGraph.{open, expand, close, toggleFullscreen}`
- `routes/explore.py` (or `routes/graph.py`) — `GET /api/entity-graph/{iri_hash}` returning the JSON shape in D-12
- `static/css/` (or inline) — Tab + graph node + bezier edge styles

</code_context>

<deferred>
## Deferred Ideas

(All deferred items are recorded in `.planning/REQUIREMENTS.md` under "Future Requirements" and `.planning/STATE.md` under "Deferred Items".)

- Pan/zoom button controls + minimap UI — explicit pan/zoom buttons that folio-enrich has; out of scope for v1.1 (drag-pan + scroll-zoom suffice).
- Edge labels (`subClassOf`, `sub_property_of`) on graph edges — added clutter; defer until UX research warrants.
- Mobile gesture support for the full-screen modal — desktop-first.
- Server-side caching for `/api/entity-graph/{iri}` — premature optimization; folio-python is in-memory.
- Vendoring elkjs into `static/` — CDN is fine for v1.1; revisit if CDN reliability becomes an issue.
- Persistent graph state across page reloads (cookie / localStorage) — explicitly out of scope.
- Editing the ontology from the graph — folio-api is read-only.

</deferred>

---

*Phase: 01-entity-graph*
*Context gathered: 2026-05-05*
