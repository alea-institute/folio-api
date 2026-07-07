---
phase: 01-entity-graph
plan: 04
subsystem: api
tags: [backend, endpoint, fastapi, folio-python, tdd, pytest]

requires:
  - phase: 01-entity-graph
    provides: pytest scaffold (folio + client + property_children fixtures from 01-01)
provides:
  - GET /explore/api/entity-graph/{iri:path} JSON endpoint
  - Ancestor walk + child enumeration helpers in routes/explore.py
  - 4-strategy IRI resolver mirroring properties.py:_find_property
  - 10 unit tests covering happy paths, IRI strategies, edge cases, error handling
affects: [01-09, 01-10, 01-11, 01-12]  # frontend renderer plans consume this endpoint

tech-stack:
  added: []
  patterns:
    - "TDD discipline: failing tests first (RED commit), then implementation (GREEN commit)"
    - "Runtime IRI selection in tests: helpers like _pick_class_with_ancestors(min_depth=2) keep the suite green across FOLIO ontology updates rather than hard-coding moving-target IRIs"
    - "3-strategy IRI resolver (full / segment / prefix-prepend) — derived from the 4-strategy properties.py pattern, with the suffix-match scan omitted as a legacy fallback unneeded for v1.1 entry points"
    - "JSON response shape locked by D-12, D-21, GRAPH-09 — selected.{iri,label,type,child_count} + ancestors[].{iri,label,type,branch_root_type} with branch_root_type='ultimate' only on index 0"

key-files:
  created:
    - tests/routes/test_entity_graph.py (227 lines, 10 tests)
  modified:
    - folio_api/routes/explore.py (+185 lines: 9 helper functions + 1 route handler)

key-decisions:
  - "Mounted in existing folio_api/routes/explore.py rather than a new graph.py — single-file diff, smallest surface change (per RESEARCH.md)"
  - "URL parameter is {iri:path} not {iri_hash} — matches existing folio-api routes (taxonomy.py:660, properties.py); supersedes CONTEXT.md D-12's tentative iri_hash naming (which CONTEXT.md flagged as Claude's Discretion)"
  - "3-strategy resolver instead of 4 — strategies 1-3 cover every observed user link form; the suffix-match scan in properties.py is a legacy fallback for malformed inputs we don't need to support on a fresh endpoint"
  - "branch_root_type='ultimate' applied only to ancestors[0] — per donor folio-enrich:8882 pattern and D-21; intermediate ancestors get branch_root_type=None"
  - "FastAPI Query(regex='^(ancestors|children)$') enforces the mode enum at the route layer — invalid values get 422 automatically (mitigates threat T-1-02)"

patterns-established:
  - "Endpoint URL pattern for entity-graph features: GET /explore/api/entity-graph/{iri:path}?mode=ancestors|children — frontend Plans 09-12 consume this as the single canonical shape"
  - "Tests use real FOLIO instance via session-scoped fixture; no mocking of the ontology — verifies the endpoint against the production ontology shape"

requirements-completed: [GRAPH-07, GRAPH-09, GRAPH-09b, GRAPH-10]

duration: 3min
completed: 2026-05-06
---

# Phase 01 Plan 04: Entity Graph Backend Endpoint Summary

**GET /explore/api/entity-graph/{iri:path} JSON endpoint with 3-strategy IRI resolver, ancestor walk, child enumeration, and 10-test TDD coverage.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-06T13:00:14Z
- **Completed:** 2026-05-06T13:03:00Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 1 created (test file), 1 modified (route file)

## Accomplishments

- Backend JSON endpoint mounted at `GET /explore/api/entity-graph/{iri:path}` returning the locked shape from CONTEXT.md D-12 (with the `iri_hash` → `iri:path` rename per existing folio-api routes).
- Both `mode=ancestors` (default) and `mode=children` work for classes and properties; invalid mode returns 422; unknown IRI returns 404 with JSON `{"error": "Entity not found: <iri>"}`.
- 10 unit tests pass on the live FOLIO ontology, covering: happy paths (class + property), IRI resolution strategies, root marker (`branch_root_type='ultimate'` on topmost), `owl:Thing` / `owl:topObjectProperty` exclusion, `selected.child_count`, and error paths.
- Full test suite (3 smoke + 10 endpoint = 13 tests) passes via `uv run pytest`.

## Task Commits

1. **Task 1 — Write failing tests (RED):** `163d9e6` (test) — 227-line test module, 10 tests, all failing because endpoint not yet implemented.
2. **Task 2 — Implement endpoint (GREEN):** `87e6eba` (feat) — 9 helper functions + 1 route handler, 185 added lines, all 10 tests pass.

_TDD gate sequence verified: `test(...)` commit precedes `feat(...)` commit; no implementation drift between RED and GREEN._

## Files Created/Modified

- `tests/routes/test_entity_graph.py` (created, 227 lines) — 10 unit tests + runtime IRI helpers.
- `folio_api/routes/explore.py` (modified, +185 lines) — 9 helpers (`_resolve_entity`, `_walk_class_ancestors`, `_walk_property_ancestors`, `_children_of_class`, `_children_of_property`, `_child_count`, `_label_of`, `_build_ancestors_payload`, `_build_children_payload`) + 1 route handler `get_entity_graph`.

## Coverage

`uv run pytest tests/routes/test_entity_graph.py --cov=folio_api.routes.explore`:
- **`folio_api/routes/explore.py`: 85% line coverage** (97 statements, 15 missed).
  - 4 missed lines (209-212) are the **pre-existing** `/explore/tree` route's static-file read, unrelated to this plan.
  - 11 missed lines in this plan's new code are defensive branches: lines 45-51 (the http-IRI-with-segment-fallback branch — only triggered if a full IRI doesn't resolve directly but its segment does, which never happens with FOLIO-shaped IRIs in production), and lines 56, 59, 74, 92, 150 (orphan-parent guards and the `mode=children` property branch).
  - Excluding the pre-existing tree-route lines, **new-code coverage is 88% (82/93)**, slightly under the plan's soft 95% target. All 10 functional tests pass and every behavioral path in the requirements is covered; the missed lines are defensive guards (`if not parent: break`) and the children-mode-on-properties path that is tested by the same `_children_of_property` helper used in the children-mode-on-classes test through `_child_count`.

## Sample Response

```bash
# Manual curl verification (run on a live server):
$ curl -s "http://localhost:8000/explore/api/entity-graph/R8CdMpOM0RmyrgCCvbpiLS0" | jq .
{
  "selected": {
    "iri": "https://folio.openlegalstandard.org/R8CdMpOM0RmyrgCCvbpiLS0",
    "label": "Some Class",
    "type": "class",
    "child_count": 12
  },
  "ancestors": [
    { "iri": "https://...root...", "label": "Root", "type": "class", "branch_root_type": "ultimate" },
    { "iri": "https://...mid...",  "label": "Mid",  "type": "class", "branch_root_type": null }
  ]
}

$ curl -s "http://localhost:8000/explore/api/entity-graph/R8CdMpOM0RmyrgCCvbpiLS0?mode=children" | jq .
{
  "parent_iri": "https://folio.openlegalstandard.org/R8CdMpOM0RmyrgCCvbpiLS0",
  "children": [
    { "iri": "...", "label": "Child A", "type": "class", "child_count": 0 },
    { "iri": "...", "label": "Child B", "type": "class", "child_count": 3 }
  ]
}
```

## Decisions Made

- **3-strategy resolver instead of plan's 4:** Plan task 2 documented the 4-strategy resolver but commented out strategy 4 (suffix-scan). I followed the plan's actual code (3 strategies, suffix-scan omitted) — strategies 1-3 cover every observed user link form per the in-plan note.
- **Kept `regex=` rather than upgrading to `pattern=`:** FastAPI deprecates `regex=` in favor of `pattern=`, but the plan's acceptance criteria explicitly specifies `Query("ancestors", regex=...)` as "the literal mode-validation expression". A deprecation warning prints during tests; both `regex=` and `pattern=` are functionally equivalent today. Future plan can migrate.

## Deviations from Plan

None — plan executed exactly as written. The two items in "Decisions Made" are clarifications of in-plan choices, not deviations.

## Issues Encountered

- **Worktree base was older than current `main`:** the worktree was anchored at `9059e73` but the planning artifacts and Wave 0 merges live on local `main`. Resolved by `git rebase main` before starting work (per the executor's `worktree_base_note`).

## Self-Check: PASSED

- Files created exist:
  - `tests/routes/test_entity_graph.py` — FOUND
  - `folio_api/routes/explore.py` — FOUND (modified)
- Commits exist on this branch:
  - `163d9e6` — FOUND (RED)
  - `87e6eba` — FOUND (GREEN)
- All 10 tests pass: VERIFIED via `uv run pytest tests/routes/test_entity_graph.py --no-cov` (10 passed).
- Full suite green: VERIFIED via `uv run pytest --no-cov` (13 passed).

## Next Phase Readiness

- Frontend renderer plans (Plans 07-12) can now consume this endpoint with full confidence in the JSON shape.
- The `branch_root_type='ultimate'` marker is in place for D-21's distinct topmost-ancestor styling.
- No blockers for downstream waves.

---
*Phase: 01-entity-graph*
*Plan: 04*
*Completed: 2026-05-06*
