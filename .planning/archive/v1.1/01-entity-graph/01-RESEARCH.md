# Phase 1: Entity Graph - Research

**Researched:** 2026-05-05
**Domain:** Browser-side ELK + cubic-bezier SVG graph porting; FastAPI/folio-python ancestor traversal endpoint; Tailwind/jQuery integration
**Confidence:** HIGH (donor verified by direct file inspection; CDN URLs probed live; folio-python attributes confirmed via runtime introspection)

## Summary

Phase 1 ports an existing, working entity-graph implementation from `folio-enrich/frontend/index.html` into folio-api as an opt-in `Details | Entity Graph` tab on `/explore/tree`. The donor code is well-isolated (~480 lines), the math is direction-agnostic cubic-bezier from `buildEdgePath()`, and the layout engine (ELK 0.11.1) is the same version both projects already use.

Most architectural decisions are locked in CONTEXT.md (30 decisions) and UI-SPEC.md (6/6 dimensions APPROVED). Research therefore focused on **technical risk surface that the discuss/UI-spec rounds did not exercise**: donor mechanics deep-dive, folio-api integration patterns, folio-python API correctness, CDN/CSP correctness, performance levers, and validation infrastructure.

**Three landmines were found that the planner must address:**

1. **CDN URL in UI-SPEC is wrong.** The UI-SPEC pins `cdnjs.cloudflare.com/ajax/libs/elkjs/0.11.1/elk.bundled.min.js` — that URL returns **HTTP 404** [VERIFIED: live curl 2026-05-05]. elkjs is not on cdnjs at all. The donor folio-enrich uses `https://unpkg.com/elkjs@0.11.1/lib/elk.bundled.js` [VERIFIED: folio-enrich/frontend/index.html:7]. The folio-api CSP `script-src` (base.html:8) currently allows only `'self'`, `cdn.tailwindcss.com`, and `cdnjs.cloudflare.com` — it does NOT allow unpkg or jsdelivr. The plan must either (a) extend CSP to add jsdelivr/unpkg, or (b) vendor the 1.6MB elkjs bundle to `static/js/vendor/`. Both are acceptable per CONTEXT.md "Claude's Discretion" — recommendation: **vendor it** (smaller surface, no third-party reliability risk, no CSP change required).

2. **No test infrastructure exists yet.** `pyproject.toml` configures `pytest` with `--cov`, but there is no `tests/` directory and no test files [VERIFIED: filesystem scan]. Wave 0 of the plan must scaffold pytest fixtures (FOLIO instance, FastAPI TestClient) before any backend tests can be written.

3. **The "iri_hash" naming in CONTEXT.md is misleading.** Existing folio-api routes do NOT hash IRIs — they accept the **last URL segment** of the FOLIO IRI (e.g. `R8CdMpOM0RmyrgCCvbpiLS0`) and resolve via a 4-strategy fallback in `_find_property` [VERIFIED: properties.py:30-57] / `get_class_details_html` [VERIFIED: taxonomy.py:1190-1216]. The new endpoint must follow this same pattern. The route should be `GET /api/entity-graph/{iri:path}` (matching properties.py:267 / taxonomy.py:660) — `iri_hash` in D-12 should be read as "IRI identifier segment".

**Primary recommendation:** Mount the new endpoint at `GET /explore/api/entity-graph/{iri:path}` inside `routes/explore.py` (the existing explore router has only `/explore/tree`; adding the data endpoint there keeps the surface coherent and avoids creating a one-off `routes/graph.py`). Vendor `elk.bundled.js` to `folio_api/static/js/vendor/elk.bundled.js`. Create `folio_api/static/js/entity_graph.js` as a self-contained renderer module exporting a single `EntityGraph` global.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GRAPH-01 | Ancestor-rooted graph in detail pane | Donor `renderGraph()` adapted; new tab panel inside `#detail-container`. See "Donor Mechanics" + "Integration Points". |
| GRAPH-02 | Full-screen modal toggle, state preserved | DOM-swap pattern: single `#entity-graph-pane` element moved between `#tab-panel-graph` and `#graph-modal-host`. See "Architecture Patterns: DOM-swap state preservation". |
| GRAPH-03 | Click graph node → select IRI in tree | Reuse existing `selectNodeByIri()` (unified_tree.js:253). Confirmed cross-type (class/property) capable. See "Integration Points". |
| GRAPH-04 | `+N Children` opt-in expansion | Recursive call to same `/api/entity-graph/{iri}` endpoint with `mode=children` query param; merge into in-memory `_graphData`. See "Endpoint Design". |
| GRAPH-05 | Lazy fetch on tab activation only | Tab handler triggers fetch only on first activation per selection. See "Integration Points". |
| GRAPH-07 | Default rooted at oldest ancestor | Server walks `sub_class_of` / `sub_property_of` upward until terminator. See "folio-python Traversal API". |
| GRAPH-08 | Cubic-bezier edges (90° entry/exit) | Copy donor `buildEdgePath()` (8976-8990) verbatim — direction-agnostic, hardcodes 90° at both ends via fixed midY/midX. |
| GRAPH-09 | Default contents = ancestors only; selected node has permanent +N button | Endpoint returns `selected`, `ancestors[]`, and `selected.child_count` (no children list on first call). |
| GRAPH-09b | Subsequently-revealed nodes use hover-only `+N` badges | Same endpoint, `mode=children` returns one node's children with their child_counts. |
| GRAPH-10 | `GET /api/entity-graph/{iri_hash}` JSON endpoint | New endpoint in `routes/explore.py`. See "Endpoint Design" — returns `{selected, ancestors, children?}`. |
| GRAPH-11 | `Details \| Entity Graph` tab UI | Tab strip wraps existing `#class-details`. ARIA tablist. See "Integration Points". |
| GRAPH-12 | Refresh on entity reselect | Hook into `selectNode()` (unified_tree.js:179) — emit a custom `entity:selected` event the graph module listens for. |
| GRAPH-13 | Drag-pan + scroll-zoom | Copy donor pan/zoom transform-matrix tracking (9036-9118) verbatim. |
| GRAPH-14 | < 500ms initial render; auto-fit zoom | See "Performance Approach". Achievable for ancestors-only. |
| GRAPH-15 | Heroicons tag/link icon prefixes | Inline SVG paths confirmed below in "Heroicons Path Strings". |
| GRAPH-16 | Selected node = thick blue border + glow | Static CSS class `.graph-node.selected` per UI-SPEC. |
| GRAPH-17 | Topmost ancestor distinct styling | Server marks `branch_root_type: 'ultimate'` on root ancestor (matches donor pattern at index.html:8882). |
| GRAPH-18 | Empty state hint | Static centered HTML when `#tab-panel-graph` activated with no selection. |
| GRAPH-19 | Skeleton graph during fetch/layout | 4 stacked rectangles with `animate-pulse`. UI-SPEC State Inventory specifies geometry. |
| GRAPH-20 | Inline error + Retry on fetch failure | `role="alert"` div with Retry button. UI-SPEC State Inventory specifies copy. |
</phase_requirements>

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Donor source**
- D-01: Port from `folio-enrich/frontend/index.html` lines 8750-9232.
- D-02: Functions: `buildELKGraph()` 8809-8840 (adapt), `renderGraph()` 8855-8974 (adapt, extract from globals), `buildEdgePath()` 8976-8990 (verbatim), pan/zoom 9036-9048, CSS 1130-1170 (port to Tailwind).

**Layout engine**
- D-03: `elkjs@0.11.1` from CDN — lazy-loaded on `/explore/tree` only.
- D-04: Layered top-to-bottom layout. Ancestors above selected, children below.

**Trigger UI**
- D-05: `Details | Entity Graph` tab strip at top of right detail-pane container; plain buttons + `.hidden` class swap.
- D-06: Graph **replaces** entity card while Graph tab active (not stacked).
- D-07: Full-screen mode = modal overlay + DOM-swap of `#entity-graph-pane` to preserve state.

**Graph contents & data fetch**
- D-08: Default contents = ancestor chain to root only; **no children by default**. `+N Children` button on selected node renders all N children at once.
- D-09: Selected node has permanent `+N Children` button; subsequently-revealed nodes show hover-only `+N` badge; leaves show no affordance.
- D-10: Lazy fetch — graph data fetched ONLY on tab activation.
- D-11: On tree-selection change while Graph tab active → refresh graph; pan/zoom resets; expanded children NOT preserved across selections.

**Visual node styling (Round 2)**
- D-19: Type differentiation = Heroicons `tag` (class) and `link` (property) icon prefix; same color palette for both.
- D-20: Selected node = 2px solid `border-blue-600` + soft outer `box-shadow` glow; no fill change, no animation.
- D-21: Topmost ancestor uses `branch_root_type: 'ultimate'` styling — slightly larger font, bolder weight, "root" badge.
- D-22: Subsequently-revealed expandable nodes use hover-only `+N Children` badge (opacity 0 → 1 on hover).

**Scale & rendering (Round 3)**
- D-23: Deep ancestor chains = render all, user pans (no truncation).
- D-24: Wide children = render all on click, no pagination.
- D-25: Initial render budget < 500ms (ancestors only).
- D-26: Initial zoom = zoom-to-fit; do NOT re-fit after expansion.

**UI states (Round 4)**
- D-27: Empty state — centered hint text + small SVG illustration.
- D-28: Loading state — skeleton graph (3-4 faded grey rectangles, subtle pulse).
- D-29: Error state — red-tinted inline error box + Retry button.

**Backend endpoint**
- D-12: `GET /api/entity-graph/{iri_hash}` returning JSON `{selected, ancestors[], children[]}`.
- D-13: Endpoint location = `explore.py` OR new `graph.py` (planner choice).
- D-14: No server-side cache.

**Graph node click**
- D-15: Click non-selected node → `selectNodeByIri()`; tree is the source of truth.

**Pan/zoom**
- D-16: Drag-pan + scroll-zoom only; no buttons, no minimap.

**Persistence**
- D-17: No persistence across sessions.
- D-30: No URL deep-linking (`?graph=<iri>` not supported).

**Scope**
- D-18: Only `/explore/tree`.

### Claude's Discretion

- Exact endpoint path mounting (in `explore.py` vs new `graph.py`).
- IRI-hashing scheme for the URL parameter — match existing pattern.
- Whether to vendor or CDN-load `elkjs`.
- Exact Heroicons SVG path strings.
- Tab styling micro-decisions (underline vs pill, hover/focus).
- Skeleton graph node count and animation tempo.
- Empty-state illustration.
- ELK config knobs.

### Deferred Ideas (OUT OF SCOPE)

- Pan/zoom button controls + minimap UI.
- Edge labels (`subClassOf`, `sub_property_of`).
- Mobile gesture support for full-screen modal.
- Server-side caching for `/api/entity-graph/{iri}`.
- Vendoring elkjs (CDN is fine for v1.1) — **but see "Risks & Landmines": researcher recommends vendoring after finding CDN/CSP mismatch**.
- Persistent graph state across page reloads.
- Editing the ontology from the graph.

</user_constraints>

## Project Constraints (from project conventions)

No `./CLAUDE.md` exists in folio-api. Constraints derived from PROJECT.md and inspection:

- **Stack lock-in:** Python 3.10+ / FastAPI / Jinja2 / jQuery + vanilla JS / Tailwind CDN. **No build step.** No webpack/vite/rollup. New JS file goes directly into `folio_api/static/js/` and is referenced via `<script src="...">` in tree.html. [VERIFIED: pyproject.toml, tree.html:233-244]
- **No React/Vue/Svelte:** Donor code from React projects must be ported to vanilla JS. (folio-mapper, ontokit-web are explicitly not port targets.)
- **In-memory ontology:** All traversal via `request.app.state.folio` (a `FOLIO` instance) — no DB. [VERIFIED: api.py:82-93]
- **Read-only API:** No editing endpoints; folio-api never writes to the ontology.
- **Existing dependencies must not be touched:** `selectNode()` (unified_tree.js:179), `selectNodeByIri()` (unified_tree.js:253), and `loadDetails()` (unified_tree.js:197) are integration points — read-only references; do not refactor their signatures.
- **CSP is restrictive** [VERIFIED: base.html:8]: `default-src 'self'`; `script-src 'self' 'unsafe-inline' cdn.tailwindcss.com cdnjs.cloudflare.com`. Adding a new external CDN requires editing base.html.
- **Public API is CORS-open** [VERIFIED: api.py:225-231]: `allow_origins=["*"]`. The new endpoint inherits this — no auth, public read.

## Architectural Responsibility Map

The phase touches three logical tiers:

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Ancestor/descendant traversal of FOLIO ontology | **API/Backend** | — | folio-python is in-memory on the server; doing this client-side would require shipping the entire ontology. Same pattern as existing `taxonomy.py:get_class_details_html`. |
| ELK layout computation | **Browser/Client** | — | ELK is a 1.6MB JS library; running it server-side would require a Node sidecar. The donor (folio-enrich) runs it client-side and that works. |
| Cubic-bezier edge path math | **Browser/Client** | — | Pure SVG geometry; no server input needed beyond ELK output. |
| Pan/zoom transform tracking | **Browser/Client** | — | Direct DOM manipulation; mouse events are client-only. |
| Tab UI state (active tab, modal open) | **Browser/Client** | — | Per-session in-memory only (D-17). Server holds no graph state. |
| Tree selection (canonical) | **Browser/Client** | — | Tree state already lives in `unified_tree.js` DOM. Graph defers to `selectNodeByIri()`. |
| Empty/loading/error state rendering | **Browser/Client** | — | Pure DOM swap based on fetch lifecycle. |
| Heroicons SVG inlining | **Browser/Client** | — | Path strings inlined as JS string constants in `entity_graph.js` — no asset fetch. |
| `child_count` precomputation | **API/Backend** | — | Done once on the server using existing `property_children` reverse index (api.py:89-93) and OWLClass `parent_class_of` attribute. |
| Topmost-ancestor detection | **API/Backend** | — | Server walks parent chain until `owl:Thing` (classes) or `owl:topObjectProperty` (properties). |

**Tier sanity check:** No misassignments detected. The split mirrors the donor exactly and fits folio-api's existing pattern (server returns minimal JSON + `class_details.html` HTML; client renders interactive UI).

## Standard Stack

### Core (already in folio-api or required new)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| elkjs | 0.11.1 | Layered graph layout | [VERIFIED: npm view elkjs version → 0.11.1, latest as of 2026-05-05]. Same version folio-enrich uses. Eclipse Layout Kernel JS port; MIT license; battle-tested in production at folio-enrich for 18+ months. |
| jQuery | 3.x (existing) | DOM manipulation, event delegation | Already loaded via `static/js/vendor/jquery.min.js` (base.html:21). Existing `unified_tree.js` uses it. New code can also use vanilla DOM — both are acceptable per stack convention. |
| Tailwind CSS | (CDN, latest) | Styling | Already loaded via `cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio` (base.html:20). |
| FastAPI | ≥0.112.2 | Backend framework | Existing. New `APIRouter` follows pattern in `routes/explore.py`. |
| folio-python | ≥0.3.3 | Ontology traversal | Existing. Provides `OWLClass`, `OWLObjectProperty`, `FOLIO`, `FOLIO_TYPE_IRIS`. [VERIFIED: pyproject.toml, runtime introspection] |

### No new Python dependencies

The endpoint can be implemented with `fastapi.APIRouter`, `starlette.responses.JSONResponse`, and the already-imported `folio.FOLIO` / `folio.OWLClass` / `folio.OWLObjectProperty`. Do **not** add any new pip packages [CITED: PROJECT.md "Constraints" section].

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| elkjs | dagre (already vendored at `static/js/vendor/dagre.min.js`) | dagre exists in vendor/ but is wired to cytoscape, not direct SVG. Donor code is built around ELK's edge sections + bend-point output that dagre does not produce identically. **Rejected** — would require rewriting `renderGraph()` and `buildEdgePath()`, defeating "port verbatim" goal. |
| Inline SVG nodes | HTML-positioned divs (donor approach, lines 8879-8915) | Donor uses absolute-positioned `<div class="graph-node">` for nodes and `<svg>` only for edges. This is simpler than nested SVG `<foreignObject>` and gives free Tailwind styling. **Adopted** (matches donor). |
| Single `entity_graph.js` module | Split across 3 files (renderer/data/state) | Donor is monolithic ~480 lines; splitting adds module boundaries with no build step to enforce them. **Rejected** — keep single file. |
| Server-rendered SVG | Client-rendered (donor approach) | Server-rendered would precompute layout but would require Node sidecar to run ELK. **Rejected** — folio-api is Python-only. |

**Installation note:** Vendor elkjs by saving the bundle file to `folio_api/static/js/vendor/elk.bundled.js`. Curl command:
```bash
curl -sL "https://unpkg.com/elkjs@0.11.1/lib/elk.bundled.js" -o folio_api/static/js/vendor/elk.bundled.js
```
[VERIFIED: SHA-384 = `k7OFwtsMfFyYU75zZhPkC8VRASnGrW1pxavUnozOiO2B5M5gv6PYGOkEYZTrVtvo`, size 1,607,470 bytes]. The plan's verify wave should compare the file's SRI hash to this expected value.

### Version verification

- `elkjs@0.11.1` is the **current latest** [VERIFIED: `npm view elkjs version` → 0.11.1, 2026-05-05].
- folio-enrich uses 0.11.1 in production [VERIFIED: folio-enrich/frontend/index.html:7].
- No major version migration needed.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────── Browser (/explore/tree) ──────────────────────┐
│                                                                       │
│  [Tree LI click]                                                      │
│       ↓                                                               │
│  selectNode(li)  ──fires──→  custom event "entity:selected"           │
│       ↓                                ↓                              │
│  loadDetails(iri, type)        EntityGraph.onEntitySelected(iri,type) │
│       ↓                                ↓                              │
│  /taxonomy/class-details/{id}   if Graph tab active:                  │
│  /properties/property-details   1. show skeleton                      │
│       ↓                         2. fetch /explore/api/entity-graph/{id}│
│  HTML fragment → #class-details   3. ELK layout (browser)             │
│                                  4. renderGraph(elkResult, data)      │
│                                  5. fitGraph()                        │
│                                                                       │
│  [Graph node click]                                                   │
│       ↓                                                               │
│  if non-selected:  selectNodeByIri(iri)  ──→  feeds back to top loop  │
│  if selected: no-op                                                   │
│                                                                       │
│  [+N Children button click]                                           │
│       ↓                                                               │
│  fetch /explore/api/entity-graph/{id}?mode=children                   │
│       ↓                                                               │
│  mergeGraphData → ELK re-layout → re-render (preserve zoom)           │
│                                                                       │
│  [Full-screen toggle]                                                 │
│       ↓                                                               │
│  document.body.appendChild(#graph-modal-root)                         │
│  #graph-modal-host.appendChild(#entity-graph-pane)  ← DOM-swap        │
│  ESC / scrim click → reverse swap, return pane to #tab-panel-graph    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                              ↑
                              │ HTTP
                              ↓
┌──────────────────────────── FastAPI ─────────────────────────────────┐
│                                                                       │
│  GET /explore/api/entity-graph/{iri:path}?mode=ancestors|children     │
│       ↓                                                               │
│  _resolve_entity(iri) → 4-strategy lookup (matches taxonomy.py:1190)  │
│       ↓                                                               │
│  if mode==ancestors (default):                                        │
│      walk sub_class_of OR sub_property_of upward until terminator    │
│      (owl:Thing for classes, owl:topObjectProperty for properties)   │
│      → ancestors[] root-first                                         │
│      compute child_count for selected only                            │
│  if mode==children:                                                   │
│      enumerate parent_class_of (classes) or                           │
│      property_children[iri] (properties, reverse index)               │
│      → children[] with each child's child_count                       │
│       ↓                                                               │
│  JSONResponse({selected, ancestors?, children?})                      │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
folio_api/
├── routes/
│   └── explore.py              # ADD: GET /explore/api/entity-graph/{iri:path}
├── static/
│   ├── js/
│   │   ├── entity_graph.js     # NEW: self-contained renderer; window.EntityGraph
│   │   ├── unified_tree.js     # MINIMAL EDIT: emit "entity:selected" custom event
│   │   └── vendor/
│   │       └── elk.bundled.js  # NEW: vendored elkjs 0.11.1 (1.6MB)
│   └── css/
│       └── styles.css          # MINIMAL EDIT: append graph-node + tab-strip CSS
└── templates/jinja2/
    ├── explore/
    │   └── tree.html           # EDIT: wrap #class-details with tab strip;
    │                           #       add #graph-modal-root before </body>;
    │                           #       add <script src="/static/js/vendor/elk.bundled.js">;
    │                           #       add <script src="/static/js/entity_graph.js">.
    └── layouts/
        └── base.html           # NO CHANGE (CSP not touched if vendoring)

tests/                          # NEW (Wave 0): pytest scaffolding
├── conftest.py                 # FOLIO fixture, FastAPI TestClient fixture
├── routes/
│   └── test_entity_graph.py    # endpoint behavior + edge cases
└── (existing tests, if any, also get scaffolded)
```

### Pattern 1: Custom-Event-Based Coupling (decoupled tree → graph)

**What:** Graph module listens for a custom `entity:selected` event dispatched from `selectNode()` rather than monkey-patching the function.

**When to use:** Whenever new functionality must react to an existing function call without modifying the caller's behavior.

**Why:** Adding `EntityGraph.onEntitySelected()` calls inside `selectNode()` couples the two modules. A custom event keeps the graph optional and lets the tree module remain unaware of graph existence.

**Example:**

```javascript
// In unified_tree.js — add ONE line at end of selectNode():
function selectNode(li, updateUrl) {
  // ... existing code unchanged ...
  document.dispatchEvent(new CustomEvent('entity:selected', {
    detail: { iri: li.data('id'), type: li.data('type') }
  }));
}

// In entity_graph.js — listener:
document.addEventListener('entity:selected', (e) => {
  if (EntityGraph.activeTab === 'graph') {
    EntityGraph.refreshFor(e.detail.iri, e.detail.type);
  }
});
```

[CITED: established pattern; folio-api does not currently use custom events but they are vanilla DOM API and zero-cost.]

### Pattern 2: DOM-Swap State Preservation (in-pane ↔ modal)

**What:** A single `#entity-graph-pane` element is moved between two host containers (`#tab-panel-graph` and `#graph-modal-host`) via `appendChild()`. Pan/zoom transform, expanded-children DOM, and ELK output all live inside the pane and survive the move.

**When to use:** Whenever the same complex component must appear in two places without re-rendering.

**Example:**

```javascript
function toggleFullscreen() {
  const pane = document.getElementById('entity-graph-pane');
  const modal = document.getElementById('graph-modal-root');
  const inPane = document.getElementById('tab-panel-graph');
  const modalHost = document.getElementById('graph-modal-host');
  if (modal.classList.contains('hidden')) {
    modalHost.appendChild(pane);     // move (does not clone)
    modal.classList.remove('hidden');
  } else {
    inPane.appendChild(pane);
    modal.classList.add('hidden');
  }
}
```

[CITED: standard DOM `appendChild` semantics — moving a node does not destroy its descendants or event listeners.]

### Pattern 3: Lazy CDN/Vendor Script Loading

**What:** elkjs is ~1.6MB. Loading it on every folio-api page would slow the tree page noticeably. Load it once on first activation of the Graph tab.

**Example:**

```javascript
let _elkLoadPromise = null;
function loadELK() {
  if (window.ELK) return Promise.resolve(window.ELK);
  if (_elkLoadPromise) return _elkLoadPromise;
  _elkLoadPromise = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = '/static/js/vendor/elk.bundled.js';
    s.onload = () => resolve(window.ELK);
    s.onerror = () => reject(new Error('Failed to load ELK'));
    document.head.appendChild(s);
  });
  return _elkLoadPromise;
}
```

The `<script>` tag for ELK should NOT be in `tree.html` — it should be appended dynamically on first tab activation. This satisfies D-03 ("lazy-loaded on tree pages only") and the < 500ms budget for users who never click the tab.

### Anti-Patterns to Avoid

- **Re-rendering the graph on every entity selection:** D-10 explicitly says lazy fetch — only fire when Graph tab is active. Don't preload on `entity:selected` if `activeTab !== 'graph'`.
- **Storing graph state in the URL:** D-30 forbids URL deep-linking. Do not push history entries from the graph module.
- **Animating the selected-node glow:** D-20 / UI-SPEC explicitly says static. CSS `box-shadow` only, no `@keyframes`.
- **Pluralizing "Children" conditionally:** UI-SPEC Copywriting says always "Children" even when N=1. "+1 Child" is wrong.
- **Building edges as straight lines or polylines:** GRAPH-08 / D-02 require cubic bezier with 90° entry/exit. Copy `buildEdgePath()` verbatim.
- **Caching entity-graph responses on the server:** D-14 forbids it (folio-python is in-memory; cache adds invalidation complexity for no gain).
- **Calling `fitGraph()` after `+N Children` expand:** D-26 says preserve user's zoom after expansion.
- **Tab-focusable graph nodes:** UI-SPEC says graph nodes are NOT individually tabbable in v1.1 (rationale: 50+ nodes is poor UX; tree is the canonical keyboard-accessible surface).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Layered graph layout | Custom DAG levelling + crossing-minimization | elkjs `layered` algorithm | Crossing minimization alone is NP-hard; ELK's layer-sweep + network-simplex is decades of research. |
| 90°-entry cubic-bezier path math | Re-derive S-curve formula | Copy donor `buildEdgePath()` verbatim | Donor is correct, direction-agnostic, 12 lines. Re-deriving introduces off-by-one errors at bend points. |
| IRI lookup with fallbacks | New resolver | Match `_find_property` 4-strategy pattern (properties.py:30-57) and `get_class_details_html` (taxonomy.py:1190-1216) | Existing pattern handles full IRI, last-segment, prefix-prepend, and suffix-match. Users link both ways. |
| `child_count` for properties | Linear scan over `folio.object_properties` per node | Use `request.app.state.property_children` reverse index (api.py:89-93) | Already precomputed at startup; O(1) child enumeration. |
| Custom modal/scrim | jQuery UI Dialog or another modal lib | Plain `<div class="fixed inset-0 ...">` per UI-SPEC | UI-SPEC fully specifies the modal CSS; jQuery UI is not loaded; adding a lib violates "no new deps". |
| ARIA tab strip | Custom focus management code | Standard `role="tablist" / role="tab" / role="tabpanel"` ARIA pattern with arrow-key handlers | The pattern is documented in UI-SPEC and has known correct implementations. |
| Heroicons SVG runtime fetch | `<img src="...">` or `fetch()` | Inline SVG path strings as JS constants | UI-SPEC mandates inline; avoids extra request and CSP `img-src` complications. |
| Skeleton/loading spinner | Animated GIF or custom canvas pulse | Tailwind `animate-pulse` utility | Already available via Tailwind CDN; respects `prefers-reduced-motion` natively when paired with the override CSS in UI-SPEC. |
| Public Sans font loading | Add another `<link>` to Google Fonts | Already loaded by `styles.css:2` | The body already has `font-['Public_Sans']`; nothing to add. |

**Key insight:** The donor file solves 95% of the visual/interaction problems already. The temptation will be to "improve" the donor while porting — resist this. The first commit should be a near-verbatim port; visual polish belongs in a later commit (or future milestone).

## Runtime State Inventory

> Skipped — this is a greenfield phase. No renames, refactors, or migrations involved. No existing graph state to preserve.

## Common Pitfalls

### Pitfall 1: CDN URL mismatch between UI-SPEC and reality
**What goes wrong:** Following the UI-SPEC literally, the executor adds `<script src="https://cdnjs.cloudflare.com/ajax/libs/elkjs/0.11.1/elk.bundled.min.js">`. Page loads. Console: `Failed to load resource: net::ERR_HTTP_RESPONSE_CODE_FAILURE 404`. Graph silently doesn't work.
**Why it happens:** elkjs is not on cdnjs. The UI-SPEC was written from training-data assumptions, not verified against the registry. [VERIFIED: live curl 2026-05-05 returns 404]
**How to avoid:** Vendor the bundle to `static/js/vendor/elk.bundled.js`. The plan's task to load ELK should reference `/static/js/vendor/elk.bundled.js` — not any external URL.
**Warning signs:** Network tab shows 404 on graph initialization; `window.ELK is undefined` errors; "Failed to load entity graph" appearing on every fetch.

### Pitfall 2: CSP blocks ELK if loaded from unpkg/jsdelivr without CSP edit
**What goes wrong:** Executor decides to use unpkg/jsdelivr instead of vendoring; adds the script tag; Chrome reports `Refused to load the script 'https://unpkg.com/...' because it violates the following Content Security Policy directive: "script-src 'self' 'unsafe-inline' cdn.tailwindcss.com cdnjs.cloudflare.com"`.
**Why it happens:** base.html:8 CSP directive does not include unpkg.com or cdn.jsdelivr.net.
**How to avoid:** Either vendor (recommended), OR explicitly extend `script-src` in base.html. Vendoring is preferable because it changes one file (vendor/elk.bundled.js exists or doesn't), not security policy.
**Warning signs:** "Refused to load" CSP errors in console; ELK never initializes despite 200 OK on the script.

### Pitfall 3: "iri_hash" parameter name is misleading
**What goes wrong:** Executor implements MD5 or SHA hashing on the client, sends a hash to the server, and the server cannot resolve the hash to an entity. CONTEXT.md uses "iri_hash" loosely — the actual project convention is the **IRI's last URL segment**.
**Why it happens:** CONTEXT.md D-12 uses "iri_hash"; UI-SPEC reuses the term; but no existing folio-api route hashes IRIs. Look at `taxonomy.py:1170` (`/class-details/{iri}`) and `properties.py:559` (`/property-details/{iri}`) — both accept the raw last URL segment (e.g., `R8CdMpOM0RmyrgCCvbpiLS0`), and `unified_tree.js:62` extracts it via `extractIdFromIri()` (split on `/` and take last non-empty segment).
**How to avoid:** Define the route as `GET /explore/api/entity-graph/{iri:path}` (path converter accepts slashes for full-IRI form too). Resolve on the server using the 4-strategy fallback pattern. Document in the OpenAPI summary that the parameter is "FOLIO IRI or its last URL segment". Client-side, reuse `extractIdFromIri()` for consistency.
**Warning signs:** 404s on every fetch despite the entity existing in the tree; `_find_property` / `folio[iri]` returning None.

### Pitfall 4: `parent_class_of` may be missing on some classes
**What goes wrong:** Executor writes `for child_iri in cls.parent_class_of:` and gets `AttributeError: parent_class_of` on certain entities, or `TypeError: 'NoneType' is not iterable`.
**Why it happens:** The taxonomy code defensively guards with `hasattr(owl_class, "parent_class_of") and owl_class.parent_class_of` (taxonomy.py:1245). Some classes may have the attribute set to `None` rather than an empty list.
**How to avoid:** Use the same defensive pattern. For object properties, use `request.app.state.property_children.get(parent_iri, [])` (the reverse index built at startup) instead of scanning. [VERIFIED: api.py:89-93]
**Warning signs:** 500 errors on entities that work in the tree; `AttributeError` in logs.

### Pitfall 5: ELK's edge `sections` array is empty for self-loops or unrouted edges
**What goes wrong:** `renderGraph()` iterates `elkEdge.sections` and skips any edge with no sections. Donor has this guard (line 8926). Executor that simplifies the iteration to `elkEdge.sections[0]` will throw `Cannot read properties of undefined`.
**Why it happens:** ELK omits sections for trivial edges or when layout fails partially.
**How to avoid:** Match donor's `(elkEdge.sections || []).forEach(section => { ... })` pattern. Don't simplify.
**Warning signs:** Graph renders for some entities but throws for others; console shows undefined-property errors.

### Pitfall 6: Running ELK while pane is `display: none`
**What goes wrong:** User opens Graph tab, immediately switches to Details tab, switches back. The auto-fit zoom calculation reads `viewport.clientWidth` while the parent is hidden — gets 0 — and the graph renders at 0× zoom (invisible).
**Why it happens:** `display: none` zeroes layout dimensions. UI-SPEC uses `.hidden` (Tailwind utility = `display: none`) for inactive panels.
**How to avoid:** Run ELK layout asynchronously after the panel is visible. Use `requestAnimationFrame` after activating the tab; only call `fitGraph()` once `clientWidth > 0`. Alternatively, defer fit to next animation frame and re-attempt if dimensions are still 0.
**Warning signs:** First-tab-activation graph appears blank; subsequent activations work; user has to scroll-zoom out to find the graph.

### Pitfall 7: `selectNodeByIri` from a graph node click triggers re-fetch loop
**What goes wrong:** User clicks graph node A. `selectNodeByIri(A)` selects tree node A. `selectNode()` dispatches `entity:selected`. Graph module re-fetches A. Same A is selected. Infinite loop or wasteful re-render.
**Why it happens:** Selecting an already-selected entity should be a no-op; the graph module currently lacks the deduplication.
**How to avoid:** In `EntityGraph.refreshFor(iri, type)`, early-return if `iri === EntityGraph.currentIri && type === EntityGraph.currentType`. Caveat: must NOT early-return if the user explicitly clicked Retry or pressed F5 — gate by event source if needed.
**Warning signs:** Network tab shows two consecutive identical fetches per click; layout flashes twice.

### Pitfall 8: Test infrastructure does not exist
**What goes wrong:** Plan tasks specify "add unit test for X"; executor finds there is no `tests/` directory, no `conftest.py`, and no FOLIO fixture. Either tests are skipped or executor invents an ad-hoc fixture that doesn't match how the app initializes.
**Why it happens:** `pyproject.toml` has `pytest` configured with `--cov` (line: `addopts = "--cov=folio_api --cov-report=term-missing --cov-report=xml"`), but the project has not yet written any tests. [VERIFIED: filesystem scan]
**How to avoid:** Wave 0 of the plan must scaffold:
- `tests/__init__.py`
- `tests/conftest.py` with two fixtures: a session-scoped `folio` instance (real, loaded from cache) and a `client` (FastAPI `TestClient(app)`).
- `tests/routes/__init__.py`
- An initial smoke test (`test_app_starts.py`) to verify the scaffolding works before adding entity-graph tests.

**Warning signs:** `ModuleNotFoundError: No module named 'tests'`; coverage report shows 0% even when pytest reports 0 tests collected.

## Code Examples

Verified patterns from the donor and folio-api codebase:

### Endpoint skeleton (mirrors `properties.py:_find_property` + `taxonomy.py:get_class_details_html`)

```python
# Source: synthesized from properties.py:30-57 and taxonomy.py:1170-1216
from fastapi import APIRouter, Request, Query, status
from folio import FOLIO, OWLClass, OWLObjectProperty
from starlette.responses import JSONResponse

OWL_THING = "http://www.w3.org/2002/07/owl#Thing"
OWL_TOP_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#topObjectProperty"


def _resolve_entity(folio: FOLIO, iri: str):
    """4-strategy IRI resolution; returns (entity, type) or (None, None)."""
    cls = folio[iri]
    if cls:
        return cls, "class"
    prop = folio.get_property(iri)
    if prop:
        return prop, "property"
    if iri.startswith("http"):
        seg = iri.rstrip("/").split("/")[-1]
        cls = folio[seg]
        if cls:
            return cls, "class"
        prop = folio.get_property(seg)
        if prop:
            return prop, "property"
    if not iri.startswith("http"):
        full = f"https://folio.openlegalstandard.org/{iri}"
        cls = folio[full]
        if cls:
            return cls, "class"
        prop = folio.get_property(full)
        if prop:
            return prop, "property"
    return None, None


@router.get("/api/entity-graph/{iri:path}", include_in_schema=True)
async def get_entity_graph(
    request: Request,
    iri: str,
    mode: str = Query("ancestors", regex="^(ancestors|children)$"),
) -> JSONResponse:
    folio: FOLIO = request.app.state.folio
    property_children = getattr(request.app.state, "property_children", {})
    entity, etype = _resolve_entity(folio, iri)
    if entity is None:
        return JSONResponse(
            content={"error": f"Entity not found: {iri}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if mode == "ancestors":
        return JSONResponse(content=_build_ancestors_payload(folio, entity, etype, property_children))
    return JSONResponse(content=_build_children_payload(folio, entity, etype, property_children))
```

### Ancestor walk (classes)

```python
# Source: pattern lifted from taxonomy.py:899-925
def _walk_class_ancestors(folio: FOLIO, cls: OWLClass) -> list[OWLClass]:
    """Returns root-first ancestor chain, EXCLUDING the cls itself, EXCLUDING owl:Thing."""
    chain = []
    current = cls
    visited = {current.iri}
    while current and getattr(current, "sub_class_of", None):
        parent_iri = current.sub_class_of[0]  # first parent (single-inheritance assumption)
        if parent_iri == OWL_THING or parent_iri in visited:
            break
        parent = folio[parent_iri]
        if not parent:
            break
        chain.insert(0, parent)
        visited.add(parent_iri)
        current = parent
    return chain
```

### Ancestor walk (properties)

```python
# Source: pattern lifted from properties.py:382-405
def _walk_property_ancestors(folio: FOLIO, prop: OWLObjectProperty) -> list[OWLObjectProperty]:
    chain = []
    current = prop
    visited = {current.iri}
    while current and getattr(current, "sub_property_of", None):
        parent_iri = current.sub_property_of[0]
        if parent_iri == OWL_TOP_OBJECT_PROPERTY or parent_iri in visited:
            break
        parent = folio.get_property(parent_iri)
        if not parent:
            break
        chain.insert(0, parent)
        visited.add(parent_iri)
        current = parent
    return chain
```

### Child enumeration (uses pre-built reverse index for properties)

```python
# Source: pattern from properties.py:98-104 and api.py:89-93
def _children_of_class(cls: OWLClass, folio: FOLIO) -> list:
    """parent_class_of attribute on the class is the canonical child list."""
    iris = getattr(cls, "parent_class_of", None) or []
    return [folio[iri] for iri in iris if folio[iri]]


def _children_of_property(prop: OWLObjectProperty, property_children: dict) -> list:
    """Reverse index built at app startup (api.py:89-93). O(1) lookup."""
    return list(property_children.get(prop.iri, []))


def _child_count(entity, etype: str, folio: FOLIO, property_children: dict) -> int:
    if etype == "class":
        return len(_children_of_class(entity, folio))
    return len(_children_of_property(entity, property_children))
```

### JSON payload shape

```python
def _build_ancestors_payload(folio, entity, etype, prop_children):
    if etype == "class":
        chain = _walk_class_ancestors(folio, entity)
    else:
        chain = _walk_property_ancestors(folio, entity)
    selected_count = _child_count(entity, etype, folio, prop_children)
    payload = {
        "selected": {
            "iri": entity.iri,
            "label": strip_folio_prefix(entity.label or "Unnamed"),
            "type": etype,
            "child_count": selected_count,
        },
        "ancestors": [
            {
                "iri": a.iri,
                "label": strip_folio_prefix(a.label or "Unnamed"),
                "type": etype,
                # branch_root_type marks the topmost ancestor for visual distinction (D-21)
                "branch_root_type": ("ultimate" if i == 0 else None),
            }
            for i, a in enumerate(chain)
        ],
    }
    return payload


def _build_children_payload(folio, entity, etype, prop_children):
    if etype == "class":
        kids = _children_of_class(entity, folio)
    else:
        kids = _children_of_property(entity, prop_children)
    return {
        "parent_iri": entity.iri,
        "children": [
            {
                "iri": c.iri,
                "label": strip_folio_prefix(c.label or "Unnamed"),
                "type": etype,
                "child_count": _child_count(c, etype, folio, prop_children),
            }
            for c in sorted(kids, key=lambda x: (x.label or x.iri).lower())
        ],
    }
```

### `buildELKGraph` adaptation (ports donor 8809-8840)

```javascript
// Source: folio-enrich/frontend/index.html:8809-8840 — adapted for ancestors-only render
function buildELKGraph(graphData) {
  const allNodes = [graphData.selected, ...graphData.ancestors, ...(graphData.children || [])];
  const targetIds = new Set();  // for layerConstraint FIRST
  // build edges: each ancestor → its child in chain; selected → each child
  const edges = [];
  // ancestors are root-first; build ancestor[i] → ancestor[i+1] edges
  for (let i = 0; i < graphData.ancestors.length - 1; i++) {
    edges.push({
      id: `e_${i}`,
      sources: [graphData.ancestors[i].iri],
      targets: [graphData.ancestors[i + 1].iri],
    });
    targetIds.add(graphData.ancestors[i + 1].iri);
  }
  // last ancestor → selected
  if (graphData.ancestors.length > 0) {
    const lastAnc = graphData.ancestors[graphData.ancestors.length - 1];
    edges.push({ id: `e_anc_sel`, sources: [lastAnc.iri], targets: [graphData.selected.iri] });
    targetIds.add(graphData.selected.iri);
  }
  // selected → each loaded child
  (graphData.children || []).forEach((c, i) => {
    edges.push({ id: `e_child_${i}`, sources: [graphData.selected.iri], targets: [c.iri] });
    targetIds.add(c.iri);
  });

  const children = allNodes.map(n => {
    const w = Math.max(180, (n.label || '').length * 7.5 + 32);
    const node = { id: n.iri, width: w, height: 36, labels: [{ text: n.label }] };
    // Donor pattern: branch_root_type: 'ultimate' nodes pinned to first layer
    if (n.branch_root_type === 'ultimate' && !targetIds.has(n.iri)) {
      node.layoutOptions = { 'elk.layered.layering.layerConstraint': 'FIRST' };
    }
    return node;
  });

  return {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',  // D-04: top-to-bottom; ancestors above
      'elk.spacing.nodeNode': '32',  // UI-SPEC: 32 px (was donor 30)
      'elk.layered.spacing.nodeNodeBetweenLayers': '64',  // UI-SPEC: 64 px (was donor 70)
      'elk.layered.spacing.edgeNodeBetweenLayers': '24',
      'elk.layered.spacing.edgeEdgeBetweenLayers': '12',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
      'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
      'elk.edgeRouting': 'POLYLINE',
      'elk.padding': '[top=16,left=16,bottom=16,right=16]',  // UI-SPEC: 16 px
    },
    children,
    edges,
  };
}
```

### `buildEdgePath` (copy verbatim — donor 8976-8990, simplified for D-04 always-DOWN)

```javascript
// Source: folio-enrich/frontend/index.html:8976-8990 — copy verbatim, simplify since D-04 fixes direction=DOWN
function buildEdgePath(section) {
  const sp = section.startPoint;
  const ep = section.endPoint;
  // Top-down only (D-04): cubic bezier with 90° vertical entry/exit
  const midY = (sp.y + ep.y) / 2;
  return `M${sp.x},${sp.y} C${sp.x},${midY} ${ep.x},${midY} ${ep.x},${ep.y}`;
}
```

### Pan/zoom transform (port donor 9036-9048 verbatim, scoped to graph instance)

```javascript
// Source: folio-enrich/frontend/index.html:9054-9118 — scope globals to module IIFE
const _xform = { x: 0, y: 0, scale: 1 };
let _panning = false, _panStart = { x: 0, y: 0 }, _panStartXform = { x: 0, y: 0 };

function _onWheel(e) {
  e.preventDefault();
  const vp = document.getElementById('graph-viewport');
  const rect = vp.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  const oldScale = _xform.scale;
  const zoomFactor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
  const newScale = Math.max(0.2, Math.min(4.0, oldScale * zoomFactor));  // UI-SPEC: 0.2..4
  _xform.x = mx - (mx - _xform.x) * (newScale / oldScale);
  _xform.y = my - (my - _xform.y) * (newScale / oldScale);
  _xform.scale = newScale;
  applyTransform();
}

function applyTransform() {
  const el = document.getElementById('graph-transform');
  if (!el) return;
  el.style.transform = `translate(${_xform.x}px, ${_xform.y}px) scale(${_xform.scale})`;
}
```

## Heroicons Path Strings

[VERIFIED: pulled from `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/<name>.svg` 2026-05-05.]

All icons render at `viewBox="0 0 24 24"`, `stroke="currentColor"`, `fill="none"`, `stroke-width="1.5"`, `stroke-linecap="round"`, `stroke-linejoin="round"`.

| Icon | Path d (verbatim) |
|------|------------------|
| `tag` (path 1) | `M9.568 3H5.25A2.25 2.25 0 0 0 3 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 0 0 5.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 0 0 9.568 3Z` |
| `tag` (path 2) | `M6 6h.008v.008H6V6Z` |
| `link` | `M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244` |
| `arrows-pointing-out` | `M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15` |
| `x-mark` | `M6 18 L18 6M6 6l12 12` |
| `arrow-path` | `M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99` |
| `share` | `M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z` |

**Usage pattern in `entity_graph.js`:**

```javascript
const ICONS = {
  tag: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M9.568 3H5.25A2.25 2.25 0 0 0 3 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 0 0 5.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 0 0 9.568 3Z"/><path stroke-linecap="round" stroke-linejoin="round" d="M6 6h.008v.008H6V6Z"/></svg>',
  link: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"/></svg>',
  // ... etc.
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cytoscape.js for ontology graphs | elkjs + hand-rolled SVG | folio-enrich pivot ~2024 (donor 8750-9232) | Much smaller per-entity payload; cubic-bezier edges look better; no plugin chain. folio-api still has cytoscape vendored (`static/js/vendor/cytoscape*.min.js`) for legacy class-detail page — keep it; new code does NOT use it. |
| Server-rendered class HTML | Client renders the graph; server stays JSON-only for the new endpoint | This phase | Mirrors `unified_tree.js` fallback path. Server endpoint stays small; client owns layout. |
| URL deep-linking for graph state | Per-session in-memory only (D-30) | This phase | Simpler. Sharing entities still works via existing `?node=<id>&type=<class\|property>` URL params. |

**Deprecated/outdated (do not use in this phase):**
- `routes/properties.py:200` `/properties/tree` — already redirects to `/explore/tree` (301). Do not add graph support there.
- `cytoscape_graph.js` (`static/js/cytoscape_graph.js`) — legacy class-detail visualization. Untouched by this phase.

## Endpoint Design

**Recommendation:** Put the new endpoint in `folio_api/routes/explore.py`, mounted under the existing `/explore` prefix.

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| `routes/explore.py` (existing router) | Smallest surface change; single new function in a 37-line file; co-located with the only consumer (`/explore/tree`); URL `/explore/api/entity-graph/{iri:path}` is self-describing. | Mixes a page route and a JSON route in the same file. | **PICK THIS.** |
| New `routes/graph.py` | Strict separation page/data. | New file + new router registration in api.py:280 + new test file path. Marginal value when the file would have one route. | Skip. |
| Top-level `/api/entity-graph` (no prefix) | Looks like a public API. | Inconsistent with existing routing (no other endpoint omits its router prefix); needs new router. | Skip. |

**Final route signature:**

```python
@router.get(
    "/api/entity-graph/{iri:path}",
    tags=["explore"],
    response_model=None,
    summary="Get Ancestor-Rooted Entity Graph",
    description="Returns selected entity + its ancestors (mode=ancestors, default) or its direct children (mode=children) for the entity-graph visualization on /explore/tree.",
    status_code=status.HTTP_200_OK,
)
async def get_entity_graph(
    request: Request,
    iri: str,
    mode: str = Query("ancestors", regex="^(ancestors|children)$"),
) -> JSONResponse:
    ...
```

Full URL: `GET /explore/api/entity-graph/<iri-or-segment>?mode=ancestors`.

**Why `path` converter:** Allows `iri` to contain slashes (full IRI form `http://folio.openlegalstandard.org/Rxxx`). FastAPI matches the same way `taxonomy.py:660` does it. Existing client code (`extractIdFromIri`) sends only the last segment, but the path converter keeps the full-IRI option open for future use without a rewrite.

**Why `?mode` instead of two endpoints:** Lets the client use one fetch helper. Two endpoints (`/ancestors` + `/children`) would also be acceptable; this is "Claude's Discretion" per CONTEXT.md. Single-endpoint with mode flag is more idiomatic for this read-only shape.

## Performance Approach

The < 500ms initial render budget (D-25) is achievable but requires honoring all of the following:

| Lever | Why it matters | What to do |
|-------|---------------|------------|
| Lazy-load elkjs | 1.6MB bundle on the critical path of every tree page = ~150ms parse on cold load. | Inject `<script src="/static/js/vendor/elk.bundled.js">` only on first Graph-tab activation. Cache the load promise (`_elkLoadPromise`). |
| Skip children on initial fetch (D-08) | Each ancestor depth is a single layer; ancestors-only is ≤ ~10 nodes for typical FOLIO entities. Adding all children even at depth=1 doubles or triples node count. | Endpoint default `mode=ancestors` returns no children, only `selected.child_count`. |
| Run ELK off the main thread | elkjs supports a Web Worker option; donor does not use it. | Not required for ancestors-only (≤ 10 nodes lays out in < 30ms). Skip the worker for v1.1. |
| Avoid layout thrash | Calling `getBoundingClientRect()` after every DOM write triggers reflow per call. | Donor's `renderGraph()` does all writes in one batch then reads dims once for `fitGraph()`. Preserve this ordering. |
| Defer `fitGraph()` to next frame | Pane may be `display: none → block` synchronously; clientWidth = 0. | `requestAnimationFrame(() => fitGraph())` after activating the tab. |
| Skip skeleton flicker on cached-recently fetches | If user toggles tabs faster than fetch latency, skeleton flashes. | Show skeleton only if fetch takes > 100ms (debounce render). |

**Server-side perf:**

- The ancestor walk is bounded by depth (typically < 10) — O(depth) `folio[iri]` lookups, each O(1) since folio-python is a dict-backed in-memory store.
- Child count for properties via reverse index = O(1).
- Child count for classes uses `parent_class_of` attribute = O(1).
- Total endpoint cost: < 5ms for typical entity. No caching needed (D-14).

**No new perf-related dependencies.**

## Risks & Landmines

(See "Common Pitfalls" above for full detail. This is the consolidated risk list.)

1. **CDN URL in UI-SPEC is wrong** (HIGH risk; will silently fail). Recommend vendor.
2. **CSP would block unpkg/jsdelivr if used as workaround** (HIGH risk). Vendor avoids this.
3. **No test infrastructure** (MEDIUM risk; tests will fail or be skipped). Wave 0 must scaffold.
4. **`iri_hash` parameter naming is misleading** (MEDIUM risk; could cause executor to add real hashing).
5. **`parent_class_of` may be `None` on some classes** (LOW risk; defensive guard pattern is in donor).
6. **ELK `sections` may be empty** (LOW risk; donor handles correctly with `|| []`).
7. **ELK runs while pane has `display: none`** (LOW-MEDIUM risk; `requestAnimationFrame` deferral fixes it).
8. **Re-fetch loop on graph-node click** (LOW risk; trivial early-return guard).
9. **elkjs bundle is 1.6MB** (MEDIUM perceived; LOW actual). UI-SPEC and CONTEXT.md cite "~500 KB" but the actual minified bundle is 1.6MB [VERIFIED: `wc -c` on download]. Vendoring under `static/js/vendor/` means it ships with folio-api and is gzipped by uvicorn — practical wire size ≈ 400KB. Acceptable.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend runtime | ✓ | 3.13.7 (project requires ≥3.10) | — |
| uv | Package management | ✓ | 0.9.22 | pip via uv-managed venv |
| pytest | Test runner | ✓ | 9.0.2 (project requires ≥8.3.1, < 9 — NOTE: dev installed pytest 9 may conflict; check uv.lock or use uv run) | — |
| node / npm | Verifying CDN versions only | ✓ | npm 11.8.0 | — |
| curl | Vendoring elkjs at install time | ✓ | system | wget |
| folio-python | Ontology runtime | ✓ (via uv.lock) | ≥0.3.3 | — |
| FastAPI | Web framework | ✓ (via uv.lock) | ≥0.112.2 | — |
| elkjs | Browser layout (vendored) | (will-be-vendored) | 0.11.1 | jsdelivr/unpkg CDN with CSP edit |
| Heroicons | Icons (inline) | ✓ (paths captured above) | v2 outline | — |
| Tailwind CDN | Styling | ✓ runtime via base.html:20 | (CDN-latest) | — |
| jQuery | Existing JS dep | ✓ vendor/jquery.min.js | (existing) | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** `elkjs` is not yet present — will be added by Wave 0 either via the curl vendor step or a `<script src=cdn>` tag with CSP edit. Vendoring is recommended.

**Note on pytest version:** pyproject.toml says `pytest>=8.3.1,<9` but the user's local pytest is 9.0.2. Plan should run tests via `uv run pytest` to use the locked version, not the system pytest.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (≥8.3.1, <9 per pyproject.toml) + pytest-asyncio (≥0.23.8) + pytest-cov |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) — `addopts = "--cov=folio_api --cov-report=term-missing --cov-report=xml"` |
| Quick run command | `uv run pytest tests/routes/test_entity_graph.py -x` |
| Full suite command | `uv run pytest` |
| JS testing | None today (no jest/vitest configured); manual UAT only for browser code |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| GRAPH-10 | Endpoint returns valid JSON for known class IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_returns_class_ancestors -x` | ❌ Wave 0 |
| GRAPH-10 | Endpoint accepts last-segment OR full IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_iri_resolution_strategies -x` | ❌ Wave 0 |
| GRAPH-10 | Endpoint returns valid JSON for known property IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_returns_property_ancestors -x` | ❌ Wave 0 |
| GRAPH-10 | Endpoint returns 404 for unknown IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_unknown_iri_returns_404 -x` | ❌ Wave 0 |
| GRAPH-10 | `?mode=children` returns child list with `child_count` per child | unit | `uv run pytest tests/routes/test_entity_graph.py::test_children_mode -x` | ❌ Wave 0 |
| GRAPH-07 | Topmost ancestor in chain has `branch_root_type=='ultimate'` | unit | `uv run pytest tests/routes/test_entity_graph.py::test_root_marker -x` | ❌ Wave 0 |
| GRAPH-07 | `owl:Thing` is excluded from ancestor chain (classes) | unit | `uv run pytest tests/routes/test_entity_graph.py::test_owl_thing_excluded -x` | ❌ Wave 0 |
| GRAPH-07 | `owl:topObjectProperty` is excluded (properties) | unit | `uv run pytest tests/routes/test_entity_graph.py::test_owl_top_obj_prop_excluded -x` | ❌ Wave 0 |
| GRAPH-09 | Selected node payload includes `child_count` | unit | `uv run pytest tests/routes/test_entity_graph.py::test_selected_has_child_count -x` | ❌ Wave 0 |
| GRAPH-10 | mode parameter rejects invalid values (422) | unit | `uv run pytest tests/routes/test_entity_graph.py::test_invalid_mode_rejected -x` | ❌ Wave 0 |
| GRAPH-01..05, 08, 11..20 | All UI/interaction behaviors | manual UAT | (not automated) | n/a |
| GRAPH-14 | < 500ms initial render | manual perf observation in `/gsd-verify-work` | (DevTools timeline) | n/a |

**Manual UAT script** (consumed by `/gsd-verify-work`):

1. Load `/explore/tree`. Confirm tree renders normally; no graph-related console errors; no extra network requests.
2. Click any class entity. Observe Details tab populates. Confirm no graph fetch fired (Network tab).
3. Click `Entity Graph` tab. Observe skeleton (~3-4 grey rectangles), then graph appears within 500ms. Topmost ancestor visually distinct (larger, ROOT badge); selected node has 2px blue border + glow.
4. Click `+N Children` button on selected node. All N children render inline below.
5. Hover a non-selected, non-leaf node. `+N` badge fades in. Click badge → that node's children render.
6. Click any non-selected graph node. Tree scrolls to and selects that entity. Graph refreshes for the new selection (skeleton → graph). Pan/zoom resets.
7. Click `⛶ Full screen`. Modal opens; pan/zoom/expanded-children persist. ESC closes; pane returns; state still preserved.
8. Disconnect network. Click a different tree entity (Graph tab still active). Inline error box appears with Retry button. Reconnect, click Retry → graph loads.
9. Click Graph tab with no entity selected (collapse all sections first or load `/explore/tree` fresh). Empty state hint + illustration.
10. Reload page. Confirm Details tab is active by default; no graph fetch fired.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/routes/test_entity_graph.py -x` (< 5 seconds for the planned tests).
- **Per wave merge:** `uv run pytest` (full suite, projected < 30 seconds once scaffolded).
- **Phase gate:** Full suite green + manual UAT script green before `/gsd-verify-work` accepts.

### Wave 0 Gaps

- [ ] `tests/__init__.py` — empty file to make `tests/` a package.
- [ ] `tests/conftest.py` — session-scoped fixtures: `folio` (real `FOLIO` instance loaded from cache), `client` (`TestClient(app)` with lifespan triggered).
- [ ] `tests/routes/__init__.py`
- [ ] `tests/routes/test_entity_graph.py` — covers 10 endpoint test cases above.
- [ ] `tests/test_app_starts.py` (optional smoke test) — confirms TestClient can boot the app, useful as the first sanity check.
- [ ] No JS test framework today — JS code is verified by the manual UAT script. Adding jest/vitest is OUT OF SCOPE for this phase (no CONTEXT.md decision to do so).

## Security Domain

`security_enforcement: true` in `.planning/config.json` with `security_asvs_level: 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | NO | Endpoint is public (folio-api is a public read-only API; CORS allow-origins=`*`). No auth surface added. |
| V3 Session Management | NO | No sessions; endpoint is stateless. |
| V4 Access Control | NO | All ontology data is public — no record-level access checks needed. |
| V5 Input Validation | YES | The `iri` path parameter is user-controlled; `mode` query is user-controlled. |
| V6 Cryptography | NO | No new crypto operations. |
| V7 Error Handling | YES | Must not leak internal paths or stack traces in 404/500 responses. Pattern in existing code returns plain JSON `{"error": ...}` — adopt. |
| V12 File and Resources | YES (browser side) | The vendored `elk.bundled.js` is a third-party file pinned by version; verify SHA-384 hash matches expected value during install. |
| V14 Configuration | YES | CSP must not be weakened. Vendoring elkjs avoids touching CSP. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `{iri:path}` | Tampering | FastAPI's `path` converter does not allow `..` to escape the route; the iri is passed to `folio[]` (a dict lookup) and `folio.get_property()` (also dict lookup). No filesystem/network calls. **Mitigated by design.** |
| Reflected XSS via entity label or IRI in error message | Tampering / Information Disclosure | Endpoint returns JSON only; no HTML interpolation server-side. Browser inserts `entity.label` into innerText (not innerHTML) — confirm in implementation. The donor's `renderGraph()` uses `textContent` (line 8895) which is safe. **Adopt textContent pattern.** |
| Mode-injection via `?mode=...&malicious` | Tampering | `Query("ancestors", regex="^(ancestors\|children)$")` rejects anything else with FastAPI 422. |
| Long-IRI DoS (very long path triggering slow lookup) | DoS | folio-python lookups are O(1) dict ops; long IRIs simply miss and return 404. **Negligible.** |
| Supply chain (vendored elkjs is replaced with malicious code) | Tampering | Pin SHA-384 in plan; verify after vendoring. SHA-384 from this research: `k7OFwtsMfFyYU75zZhPkC8VRASnGrW1pxavUnozOiO2B5M5gv6PYGOkEYZTrVtvo`. |
| `prefers-reduced-motion` ignored | Accessibility (cross-cutting) | UI-SPEC mandates the override CSS; verify in DevTools by toggling the preference. |

**No new authentication, sessions, secrets, or privileged operations are introduced by this phase.** The endpoint is pure read-only and its response is the same for every caller.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | folio-python `OWLClass.parent_class_of` always returns iterable-or-None (never raises) | Code Examples | Medium — defensive `getattr(..., [])` mitigates but worth confirming during Wave 0 with a smoke test against the real ontology. |
| A2 | Custom DOM event coupling (`entity:selected`) is acceptable to the project (no existing convention forbids it) | Pattern 1 | Low — the alternative (direct module reference) is trivial to switch to in code review if the user prefers tighter coupling. |
| A3 | gzip on the uvicorn static-file response is enabled by default for vendored elkjs | Risks #9 | Low — even uncompressed 1.6MB is loaded once on first tab activation, not per page load. |
| A4 | The "ROOT" badge label (UI-SPEC Copywriting) is acceptable English for legal-domain users | n/a | Low — purely cosmetic; can change in code review without architectural impact. |
| A5 | `folio[iri]` returns `None` (not raise) on miss | Code Examples | Low — taxonomy.py:1194 uses `folio[iri]` and tests for truthiness; pattern is established. |

If A1 is wrong, Wave 0 testing catches it immediately. All other assumptions are low-risk.

## Open Questions (RESOLVED)

1. **Should the endpoint accept a depth parameter for ancestor traversal?**
   - What we know: D-08 says default = full chain to root. No truncation per D-23.
   - What's unclear: Should the endpoint hard-code "walk to terminator" or accept `?max_depth=N` as a defensive limit? FOLIO chains are bounded (rarely > 12) so no real need.
   - Recommendation: No depth parameter for v1.1. Hard-code "walk until terminator". Add later if user demand emerges.
   - **RESOLVED:** Adopted "walk to terminator" with NO depth parameter. Implemented in Plan 01-04 (route signature has no `?max_depth`). Future addition tracked under REQUIREMENTS.md "Future Requirements".

2. **Should we vendor elkjs in this phase or follow CONTEXT.md's "CDN is fine" decision?**
   - What we know: CONTEXT.md D-03 says CDN; "Future Requirements" lists vendoring. UI-SPEC's CDN URL is wrong (cdnjs returns 404).
   - What's unclear: Whether the user wants to update D-03 in light of the URL mismatch, or accept a CSP edit to allow unpkg.
   - Recommendation: **Vendor it.** This satisfies "Claude's Discretion" (CONTEXT.md "Whether to vendor or CDN-load `elkjs` — D-03 says CDN; if researcher finds CDN reliability concerns, vendor is acceptable"). The fact that the planned cdnjs URL doesn't exist counts as a "CDN reliability concern". Document the decision in the plan.
   - **RESOLVED:** Vendoring elected. Implemented in Plan 01-02 (downloads `elk.bundled.js` to `folio_api/static/js/vendor/` with SHA-384 pin). D-03's CDN preference is overridden under the "Claude's Discretion" clause; rationale is the empirical CDN 404 finding plus folio-api's CSP not allowing unpkg/jsdelivr.

3. **Should JS unit tests be added in this phase or deferred?**
   - What we know: pyproject.toml has pytest configured, no JS test framework, all donor code came in production-tested.
   - What's unclear: Whether adding jest/vitest now is worth it.
   - Recommendation: Defer JS unit tests. Manual UAT script is sufficient for v1.1; adding a JS test framework is out of scope unless explicitly requested.
   - **RESOLVED:** Deferred. No plan introduces jest/vitest. JS coverage strategy = the 16-item Manual UAT script in VALIDATION.md, browser DevTools console error check, and Plans 14 (perf) + 15 (a11y) checkpoints.

## Sources

### Primary (HIGH confidence)

- `folio-enrich/frontend/index.html` lines 7, 1100-1170, 8750-9232 — donor source code (read directly).
- `folio_api/api.py`, `routes/explore.py`, `routes/properties.py` (full), `routes/taxonomy.py` lines 880-1325, `static/js/unified_tree.js` (full), `templates/jinja2/explore/tree.html`, `templates/jinja2/layouts/base.html`, `static/css/styles.css` — folio-api integration points (read directly).
- `pyproject.toml` — dependency and pytest configuration.
- `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/optimized/24/outline/{tag,link,arrows-pointing-out,x-mark,arrow-path,share}.svg` — exact path strings (fetched 2026-05-05).
- Live `npm view elkjs version` 2026-05-05 → 0.11.1.
- Live `curl -sI` probes confirming cdnjs 404 and unpkg/jsdelivr 200 for elkjs 0.11.1.
- Context7 `/kieler/elkjs` docs — browser-bundled usage pattern (matches donor).
- `/home/damienriehl/Coding Projects/folio-api/.planning/phases/01-entity-graph/CONTEXT.md` (full).
- `/home/damienriehl/Coding Projects/folio-api/.planning/phases/01-entity-graph/01-UI-SPEC.md` (full).

### Secondary (MEDIUM confidence)

- Heroicons v2 outline icon catalog (heroicons.com) — confirmed icon names exist; path data fetched from the GitHub raw source.

### Tertiary (LOW confidence)

- None — every claim in this research is backed by a HIGH or MEDIUM source.

## Metadata

**Confidence breakdown:**

- Donor mechanics: HIGH — every line referenced was read in this session.
- folio-api integration points: HIGH — all five integration files read end-to-end.
- folio-python API correctness: HIGH — verified by Python introspection + existing usage in taxonomy.py and properties.py.
- elkjs CDN URL: HIGH — verified by live HTTP HEAD probes.
- Heroicons paths: HIGH — fetched verbatim from upstream source.
- ELK config tuning recommendations: MEDIUM — donor's exact values are proven; UI-SPEC's tuned values (32/64 px) are educated extrapolation.
- Pitfalls list: MEDIUM-HIGH — items 1-4 are verified; items 5-8 are pattern-recognition from similar codebases.
- Performance estimate of < 500ms: MEDIUM — based on node-count math + folio-python O(1) lookup; not benchmarked in this session.

**Research date:** 2026-05-05.
**Valid until:** 2026-06-05 (elkjs is stable; folio-python 0.3.x is stable; donor file is unchanged in folio-enrich since 2024).
