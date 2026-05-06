# folio-api

## What This Is

Public API and interactive web UI for FOLIO (Federated Open Legal Information Ontology). FastAPI backend + Jinja2 templates serving an explorable taxonomy at https://folio.openlegalstandard.org/. Used by lawyers, legal technologists, and ontology researchers to browse and reference FOLIO classes and properties.

## Core Value

The taxonomy must be browsable, searchable, and visually clear — users come here to *find and understand* legal concepts in their hierarchy.

## Stack

- Python 3.10+ / FastAPI / Uvicorn
- Jinja2 templates (`folio_api/templates/jinja2/`)
- Tailwind CSS (compiled in `folio_api/static/css/`)
- jQuery + vanilla JS (`folio_api/static/js/`)
- `folio-python` library (in-memory ontology with `subClassOf` / `sub_property_of` traversal)
- Primary tree page: `/explore/tree` — unified classes + properties (template `explore/tree.html`, JS `unified_tree.js`)

> Note: legacy routes `/properties/tree` and `/taxonomy/tree` were removed in commit `e28c82c` (milestone v1.0). `/explore/tree` is the sole surviving tree UI.

## Reference projects (sister repos)

- **folio-enrich** (`../folio-enrich/`) — donor for the segmented expand/collapse pattern (milestone v1.0) and for the planned entity-graph (milestone v1.1, ELK + cubic-bezier SVG, `frontend/index.html` lines 8750–9232).
- **folio-mapper** (`../folio-mapper/`) — React `ConceptDAG.tsx` with quadratic bezier; not a port target (stack mismatch).
- **ontokit-web** (`../ontokit-web/`) — Next.js + ReactFlow + ELK; not a port target (stack mismatch).

## Requirements

### Validated

<!-- Shipped and confirmed valuable -->

- ✓ Compact tree-page header — milestone v1.0
- ✓ Segmented expand/collapse pattern (Expand to depth-N, Expand all, Collapse one level, Collapse all) — milestone v1.0
- ✓ Alternative Labels exclude non-English translations — milestone v1.0 (PR #16)

### Active

<!-- Current scope: milestone v1.1 (Entity Graph) -->

- [ ] **GRAPH-01**: User can view selected entity in an ancestor-rooted hierarchical graph (cubic-bezier SVG) inside the right detail pane
- [ ] **GRAPH-02**: User can pop the graph out to a full-screen modal and back without losing graph state
- [ ] **GRAPH-03**: User can click any node in the graph to select that IRI in the left tree (graph then refreshes)
- [ ] **GRAPH-04**: User can expand a node's hidden children via a `+N Children` affordance, merging them into the live graph
- [ ] **GRAPH-05**: Graph contents lazy-load only when the user activates the `Entity Graph` tab — not on every entity selection

### Out of Scope

<!-- Explicit boundaries -->

- Pan/zoom buttons + minimap UI — defer to a later milestone (drag-to-pan + scroll-to-zoom suffice for v1.1)
- Edge labels (`subClassOf`, `sub_property_of`) on the graph — defer; visual clutter in early UX testing
- Mobile gesture support for the full-screen graph — desktop-first; revisit if mobile usage warrants
- Server-side caching of the `/api/entity-graph/*` endpoint — premature; folio-python is in-memory and fast
- Re-introducing `/properties/tree` and `/taxonomy/tree` — explicitly deprecated in v1.0

## Constraints

- **Tech stack**: jQuery + vanilla JS + Jinja2 — no React/Next.js/Vue. Donor code from React projects must be ported.
- **Dependency**: `elkjs` 0.11.1 from CDN (matches folio-enrich) — adds ~500 KB on tree pages only, lazy-loaded.
- **Compatibility**: Existing `selectNode()` and `selectNodeByIri()` in `unified_tree.js` are integration points for the graph; do not break them.
- **Data**: All ancestor / child traversal is in-memory via `folio-python`; no database.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Donor for entity graph = folio-enrich | Same FastAPI + jQuery + vanilla JS stack; cubic-bezier already implemented in `buildEdgePath()` (lines 8979–8990); ELK layout proven | — Pending (v1.1) |
| Layout engine = elkjs from CDN | Matches folio-enrich exactly; clean layered layouts; lazy-loaded only on tree pages | — Pending (v1.1) |
| Graph hidden behind `Entity Graph` tab in detail pane | Keeps default tree-browsing UX unchanged; graph is opt-in per session | — Pending (v1.1) |
| Drop legacy `/properties/tree` and `/taxonomy/tree` | Unified `/explore/tree` covers both; less surface to maintain | ✓ Good (v1.0, commit `e28c82c`) |
| Lightweight `.planning/milestones/<n>/PLAN.md` pattern → full GSD | User wants formal GSD workflow (CONTEXT.md → research → PLAN.md → execute → verify) for milestone v1.1+ | ✓ Good (this commit) |

---
*Last updated: 2026-05-05 after bootstrap to GSD format and start of milestone v1.1*
