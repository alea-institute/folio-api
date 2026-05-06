---
phase: 01-entity-graph
plan: 01
subsystem: testing
tags: [pytest, fixtures, scaffold, fastapi, testclient, folio-python]

# Dependency graph
requires:
  - phase: bootstrap
    provides: pyproject.toml pytest config (--cov=folio_api, pytest>=8.3.1, pytest-asyncio, pytest-cov)
provides:
  - tests/ Python package with routes/ subpackage
  - Session-scoped FOLIO ontology fixture (real, lifespan-loaded)
  - Function-scoped TestClient fixture bound to a once-booted app
  - Session-scoped property_children reverse-index fixture
  - Working smoke test proving the fixture chain
affects:
  - 01-04-PLAN (entity-graph endpoint tests reuse client + folio + property_children)
  - All future folio-api backend tests in any phase

# Tech tracking
tech-stack:
  added: []  # No new dependencies — all required libs already in dev group
  patterns:
    - "Session-scoped TestClient context manager to fire FastAPI lifespan once per test session"
    - "Function-scoped TestClient piggy-backed on a session-scoped booted app (cheap per-test client, ontology loaded once)"

key-files:
  created:
    - tests/__init__.py
    - tests/routes/__init__.py
    - tests/conftest.py
    - tests/test_app_starts.py
  modified: []

key-decisions:
  - "Session-scoped _booted_app uses `with TestClient(app) as _: yield app` to invoke FastAPI lifespan exactly once per test session"
  - "client fixture is function-scoped (fresh client per test) but reuses the session-scoped booted app to avoid reloading FOLIO"
  - "folio and property_children fixtures read directly from app.state — no second copy of the ontology"
  - "Smoke test pins on /openapi.json (FastAPI built-in) so it stays stable as routes evolve"

patterns-established:
  - "Pytest fixture chain: _booted_app (session) → client/folio/property_children (function or session) — downstream tests should reuse, not re-instantiate FOLIO"
  - "Smoke-test convention: tests/test_<surface>_starts.py for boot-correctness checks; route-level tests live in tests/routes/"

requirements-completed: []  # Plan frontmatter requirements: [] — Wave 0 infra, no GRAPH-* requirement closes here

# Metrics
duration: ~2min
completed: 2026-05-06
---

# Phase 1 Plan 01: Pytest Scaffold Summary

**Pytest scaffold + session-scoped FOLIO/TestClient fixtures, validated by a 3-test smoke suite that boots the FastAPI app and confirms `app.state.folio` + `app.state.property_children` are populated by the lifespan.**

## Performance

- **Duration:** ~2 min (92 seconds wall clock from plan start to final task commit)
- **Started:** 2026-05-06T12:54:26Z
- **Completed:** 2026-05-06T12:55:58Z (approx)
- **Tasks:** 3
- **Files created:** 4
- **Files modified:** 0
- **FOLIO load time observed:** ~1.75s for the full 3-test smoke run end-to-end (pytest ran in 1.75s including FOLIO startup, ELK-free; well under the 10s acceptance budget)

## Accomplishments

- Created the `tests/` package skeleton (`tests/__init__.py`, `tests/routes/__init__.py`) so pytest can collect modules and downstream `tests/routes/test_entity_graph.py` (Plan 04) can land cleanly.
- Authored `tests/conftest.py` with four fixtures (`_booted_app`, `client`, `folio`, `property_children`) that wire the real FastAPI lifespan into the test session — no mocks, no second FOLIO instance.
- Authored `tests/test_app_starts.py` with three smoke tests (`test_app_boots`, `test_folio_loaded`, `test_property_children_built`); all 3 pass via `uv run pytest tests/test_app_starts.py -x -v`.
- Verified `uv run pytest tests/ --collect-only` exits 0 with no collection or import errors.

## Task Commits

Each task was committed atomically on the worktree branch:

1. **Task 1: Create tests/ package skeleton** — `3d77238` (chore)
2. **Task 2: Create conftest.py with folio + client fixtures** — `df276df` (feat)
3. **Task 3: Create test_app_starts.py smoke test** — `8d9d3df` (test)

**Plan metadata commit:** _added by this SUMMARY commit, see git log after merge_

## Files Created/Modified

- `tests/__init__.py` — Empty package marker so `tests/` is a Python package (0 bytes).
- `tests/routes/__init__.py` — Empty package marker for the routes subpackage (0 bytes).
- `tests/conftest.py` — Four pytest fixtures (`_booted_app` session-scoped, `client` function-scoped, `folio` session-scoped, `property_children` session-scoped). Imports `from folio_api.api import app`. Uses `with TestClient(app) as _: yield app` to invoke the FastAPI lifespan exactly once per session.
- `tests/test_app_starts.py` — Three smoke tests covering app boot via `/openapi.json`, `folio.classes` non-empty, and `property_children` reverse index non-empty.

## Confirmed Run Commands

```bash
# Smoke run (canonical per plan):
uv run pytest tests/test_app_starts.py -x -v
# Output: 3 passed in 1.75s

# Collection check:
uv run pytest tests/ --collect-only -q
# Output: 3 tests collected

# Full suite (still small at this stage):
uv run pytest
# Output: 3 passed
```

## Decisions Made

- **Followed plan exactly:** the conftest.py and test_app_starts.py contents are the verbatim spec from 01-01-PLAN.md (Tasks 2 and 3 each provided exact source). No design freedom was needed — the plan was prescriptive.
- **No new dependencies:** pytest, pytest-asyncio, pytest-cov are already in the `dev` dependency group of `pyproject.toml`. Verified before Task 2.

## Deviations from Plan

None — plan executed exactly as written.

The three task verification blocks all passed on the first run; no Rule 1/2/3 fixes were necessary. No checkpoints in this plan (`autonomous: true`, no `type="checkpoint:*"` tasks).

## Issues Encountered

None.

Pre-existing Pydantic v2 deprecation warnings (`PydanticDeprecatedSince20: Using extra keyword arguments on Field`) and a Starlette deprecation warning (`HTTP_422_UNPROCESSABLE_ENTITY`) surface in pytest output — these are pre-existing in `folio_api/models/owl.py`, `folio_api/models/health.py`, and `folio_api/routes/taxonomy.py`, not introduced by this plan. Per CLAUDE.md scope-boundary guidance these were left untouched and are not the responsibility of Wave 0 scaffold work.

## User Setup Required

None — no external service configuration required for the pytest scaffold.

## Next Phase Readiness

**Ready for Wave 1 (Plan 04 — entity-graph endpoint tests):**

- `client`, `folio`, `property_children` fixtures are available for import in any `tests/routes/test_*.py` module.
- Pytest collection works; `uv run pytest tests/routes/test_entity_graph.py -x` will run as soon as Plan 04 lands the test file.
- The 10 endpoint test cases enumerated in `01-VALIDATION.md` (rows 1-EP-01 through 1-EP-10) can now begin TDD-RED execution.

**No blockers.**

## Self-Check: PASSED

Verified before commit:

- `tests/__init__.py` exists (0 bytes)
- `tests/routes/__init__.py` exists (0 bytes)
- `tests/conftest.py` exists (1500+ bytes, 4 fixtures)
- `tests/test_app_starts.py` exists (3 test functions)
- Commits `3d77238`, `df276df`, `8d9d3df` exist on worktree branch (verified via `git log --oneline -5`)
- `uv run pytest tests/test_app_starts.py -x -v` → 3 passed in 1.75s
- `uv run pytest tests/ --collect-only` → 3 tests collected, exit 0

---
*Phase: 01-entity-graph*
*Plan: 01*
*Completed: 2026-05-06*
