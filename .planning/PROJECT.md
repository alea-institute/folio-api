# folio-api

Public API + interactive web UI for the FOLIO (Federated Open Legal Information Ontology). FastAPI + Jinja2 templates, served at https://folio.openlegalstandard.org/.

## Stack

- Python 3.10+ / FastAPI / Uvicorn
- Jinja2 templates (`folio_api/templates/jinja2/`)
- Tailwind CSS (compiled in `folio_api/static/css/`)
- jQuery + vanilla JS (`folio_api/static/js/`)
- Three primary tree pages:
  - `/explore/tree` — unified classes + properties (template: `explore/tree.html`, JS: `unified_tree.js`)
  - `/properties/tree` — properties only (template: `properties/tree.html`, JS: `property_tree.js`)
  - `/taxonomy/tree` — classes only (template: `taxonomy/tree.html`, JS: `taxonomy_tree.js`)

## Reference projects

- **folio-enrich** (`../folio-enrich/`) — sister project. Source of the segmented expand/collapse UX pattern (frontend/index.html ~line 8062).

## Milestones

- **001 — Tree page UX polish** (active) — Compact header, remove redundant heading, adopt folio-enrich's segmented expand/collapse pattern across all tree pages.
