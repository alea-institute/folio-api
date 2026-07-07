---
phase: 1
slug: entity-graph
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract derived from RESEARCH.md `## Validation Architecture`. Used by gsd-executor for feedback sampling during execution and by gsd-verify-work for the phase gate.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8.3.1 + pytest-asyncio ≥0.23.8 + pytest-cov |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) — already configured with `--cov=folio_api --cov-report=term-missing --cov-report=xml` |
| **Quick run command** | `uv run pytest tests/routes/test_entity_graph.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | < 5s quick / < 30s full (post-scaffold) |
| **JS testing** | None today — manual UAT only for browser code (out of scope to add jest/vitest in this phase) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/routes/test_entity_graph.py -x`
- **After every plan wave:** Run `uv run pytest` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green AND manual UAT script must pass
- **Max feedback latency:** < 5s for the per-task quick run

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-W0-01 | 01 | 0 | infra | — | tests/ scaffold | scaffold | `test -f tests/conftest.py` | ❌ W0 | ⬜ pending |
| 1-W0-02 | 01 | 0 | infra | — | TestClient boot | unit | `uv run pytest tests/test_app_starts.py -x` | ❌ W0 | ⬜ pending |
| 1-EP-01 | 01 | 1 | GRAPH-10 | T-1-01 | Endpoint returns valid JSON for known class IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_returns_class_ancestors -x` | ❌ W0 | ⬜ pending |
| 1-EP-02 | 01 | 1 | GRAPH-10 | T-1-01 | Endpoint accepts last-segment OR full IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_iri_resolution_strategies -x` | ❌ W0 | ⬜ pending |
| 1-EP-03 | 01 | 1 | GRAPH-10 | T-1-01 | Endpoint returns valid JSON for known property IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_returns_property_ancestors -x` | ❌ W0 | ⬜ pending |
| 1-EP-04 | 01 | 1 | GRAPH-10 | T-1-01 | Endpoint returns 404 for unknown IRI | unit | `uv run pytest tests/routes/test_entity_graph.py::test_unknown_iri_returns_404 -x` | ❌ W0 | ⬜ pending |
| 1-EP-05 | 01 | 1 | GRAPH-10 | T-1-02 | `?mode=children` returns child list with `child_count` per child | unit | `uv run pytest tests/routes/test_entity_graph.py::test_children_mode -x` | ❌ W0 | ⬜ pending |
| 1-EP-06 | 01 | 1 | GRAPH-07 | — | Topmost ancestor in chain has `branch_root_type=='ultimate'` | unit | `uv run pytest tests/routes/test_entity_graph.py::test_root_marker -x` | ❌ W0 | ⬜ pending |
| 1-EP-07 | 01 | 1 | GRAPH-07 | — | `owl:Thing` is excluded from class ancestor chain | unit | `uv run pytest tests/routes/test_entity_graph.py::test_owl_thing_excluded -x` | ❌ W0 | ⬜ pending |
| 1-EP-08 | 01 | 1 | GRAPH-07 | — | `owl:topObjectProperty` is excluded from property ancestor chain | unit | `uv run pytest tests/routes/test_entity_graph.py::test_owl_top_obj_prop_excluded -x` | ❌ W0 | ⬜ pending |
| 1-EP-09 | 01 | 1 | GRAPH-09 | — | Selected node payload includes `child_count` | unit | `uv run pytest tests/routes/test_entity_graph.py::test_selected_has_child_count -x` | ❌ W0 | ⬜ pending |
| 1-EP-10 | 01 | 1 | GRAPH-10 | T-1-03 | mode parameter rejects invalid values (422) | unit | `uv run pytest tests/routes/test_entity_graph.py::test_invalid_mode_rejected -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — empty file to make `tests/` a package
- [ ] `tests/conftest.py` — session-scoped fixtures: `folio` (real `FOLIO` instance loaded from cache), `client` (`TestClient(app)` with lifespan triggered)
- [ ] `tests/routes/__init__.py` — empty
- [ ] `tests/routes/test_entity_graph.py` — covers 10 endpoint test cases above
- [ ] `tests/test_app_starts.py` — smoke test confirming TestClient can boot the app
- [ ] No JS test framework today — JS code is verified by the manual UAT script. Adding jest/vitest is OUT OF SCOPE for this phase.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Graph renders with cubic-bezier edges | GRAPH-08 | Visual SVG path inspection | DevTools → inspect graph SVG → confirm `<path>` `d` attr matches `M x,y C x1,y1 x2,y2 x,y` (cubic), not straight `L` |
| Tab UI works (Details ↔ Entity Graph) | GRAPH-11 | Visual + interaction | Click each tab; confirm content swap; confirm details card preserved when switching back |
| Skeleton shows during load | GRAPH-19 | Visual + timing | Throttle network to 3G; click Graph tab; confirm 3–4 grey rects with pulse appear before graph |
| Selected node has 2px blue border + glow | GRAPH-16 | Visual | DevTools → inspect selected node element → confirm `border: 2px solid #2563EB` + glow box-shadow |
| Topmost ancestor has distinct styling + ROOT badge | GRAPH-17 | Visual | Inspect topmost node; confirm larger font + bolder weight + ROOT badge SVG |
| `+N Children` button (selected) renders ALL children on click | GRAPH-04 | Interaction + count match | Click selected node's `+N` button; count rendered children; verify === N |
| Hover-only `+N` badge on subsequently-revealed nodes | GRAPH-09b | Interaction | After expanding selected, hover a child with `child_count > 0`; confirm `+N` badge appears; mouseout → fades |
| Click graph node → selects in left tree + refreshes graph | GRAPH-03, GRAPH-12 | Interaction + state | Click any non-selected graph node; confirm tree scrolls/selects that IRI; confirm graph re-renders rooted at NEW topmost ancestor |
| Drag-pan + scroll-to-zoom | GRAPH-13 | Interaction | Drag canvas; confirm pan transform applies. Scroll wheel; confirm zoom in/out around cursor |
| Full-screen modal preserves state | GRAPH-02 | Interaction + state | Pan/zoom/expand children; click ⛶ Full screen; confirm state preserved; ESC; confirm restored to pane with same state |
| Auto-fit zoom on initial render | GRAPH-14 | Visual | Open Graph tab; confirm whole ancestor chain fits viewport without scrolling |
| Heroicons tag (class) and link (property) icons | GRAPH-15 | Visual | Open graph for a class; confirm tag icon prefix on class nodes. Repeat for a property entity. |
| Empty state when no entity selected | GRAPH-18 | Visual | Reload `/explore/tree` (collapse all sections so nothing selected) → click Graph tab → confirm hint text + illustration |
| Inline error + Retry on backend failure | GRAPH-20 | Interaction (with throttling) | DevTools → block `/explore/api/entity-graph/*` → click Graph tab → confirm red error box + Retry button. Unblock + Retry → graph loads. |
| Lazy fetch — no graph requests on detail-only sessions | GRAPH-05 | Network observation | Open `/explore/tree`, click 5 different entities while staying on Details tab. Confirm 0 requests to `/explore/api/entity-graph/*`. |
| Initial render < 500ms (typical entity) | GRAPH-14 | Performance timing | DevTools Performance tab → record from Graph tab click → measure to first paint of laid-out graph. Acceptance: < 500ms p50 across 5 trials with depth ≤ 8 ancestors. |
| `prefers-reduced-motion` disables animations | UI-SPEC §motion | Setting + visual | Set OS prefers-reduced-motion: reduce → reload → confirm skeleton has no pulse, glow has no transition, modal opens instantly |

---

## JS Coverage Strategy

JS code (`entity_graph.js`, modifications to `unified_tree.js`) has no automated test framework in this phase. Coverage strategy:

1. **Manual UAT script** (above) covers all observable behaviors for GRAPH-01..GRAPH-09b, GRAPH-11..GRAPH-20.
2. **Browser DevTools console** must show zero errors during the full UAT walkthrough.
3. **Defer**: introducing jest/vitest is explicitly out of scope (no CONTEXT.md decision to add JS test infra).

---

## Backend Coverage Targets

- **Endpoint route handler** (`folio_api/routes/explore.py:entity_graph`): ≥ 90% line coverage via the 10 unit tests.
- **Helper functions** (ancestor walk, child enumeration, root-marker tagging): ≥ 95% line coverage.
- **Coverage report**: `uv run pytest --cov=folio_api.routes.explore` should show no uncovered lines except defensive error paths.

---

## Phase Gate Checklist

Before `/gsd-verify-work` can accept this phase:

- [ ] Wave 0 test scaffold complete (5 files exist; `pytest` runs without collection errors)
- [ ] All 10 endpoint unit tests green
- [ ] Manual UAT script green (16 behaviors above)
- [ ] DevTools console zero errors during UAT walkthrough
- [ ] Initial render < 500ms p50 confirmed via Performance tab
- [ ] Coverage thresholds met for the new endpoint handler

---

## Source

Derived from `01-RESEARCH.md` § Validation Architecture. Cross-referenced against REQUIREMENTS.md GRAPH-01..GRAPH-20 and UI-SPEC.md state inventory.
