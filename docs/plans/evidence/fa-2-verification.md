# fa-2 verification

The graph now provides native pan, zoom and Fit buttons, a passive overview that
frames both graph and camera, and readable node visibility and zoom information.
Fit and the overview use measured rendered nodes, including the child button and
dragged positions. Resize preserves the camera; replacement disposes observers
and frame callbacks. Keyboard expansion restores logical focus without taking it
from another surface. The full-screen trigger has its own layout column so it
cannot overlap the graph tab in a narrow pane.

## Scope and starting state

- Item: fa-2, expansion; branch: `drawdown/fa-2`.
- Plan: `docs/plans/2026-10-27-0846-feat-accessible-graph-controls-minimap-plan.md`.
- Initial HEAD: `bd5f94b`, containing the committed plan; working tree clean.
- Rechecked the renderer, styles, tab integration, split pane, API tests and plan.
  The documented gaps were still present. No existing test was changed.
- Only graph controls/overview, their layout and opt-in browser coverage changed.
  No migration, data rewrite, outside service, release or production work.
- The chief repository is absent here. Its Goal Capsule and Campaign R11, R15,
  R16, R17, R19 and R20 still require the controller's source check before merge.
  The supplied campaign rules governed this build; the missing source is not
  represented as inspected.

## Actual checks (2026-10-27)

| Command | Result |
| --- | --- |
| `uv run pytest tests/test_app_starts.py -x` | 3 passed, 15 existing deprecation warnings |
| `uv run pytest tests -q` | Baseline: 46 passed, 16 warnings, 64.46 seconds; existing coverage configuration retained |
| `uv run --group browser pytest -o addopts='' --collect-only browser_tests/entity_graph_controls.py -q` | Initial 5 cases collected without API conftest import; final collection recorded below |
| `node --check folio_api/static/js/entity_graph.js` | Passed |
| `uv run --group browser pytest -o addopts='' browser_tests/entity_graph_controls.py --browser chromium --base-url http://127.0.0.1:9616 --graph-evidence-dir docs/plans/evidence -q` | 16 passed, 21.83 seconds after the narrow tab layout correction |
| `git diff --check` | Passed |

The server command was `uv run uvicorn folio_api.api:app --host 127.0.0.1 --port 9616`.
It started with the real ontology and no LLM credentials. Python 3.13.11,
pytest 8.4.2, pytest-playwright 0.10.0 and Playwright 1.64.1 were used. The provided
Chromium cache worked. The optional browser installation attempt did not finish
against the read-only cache and was stopped; no sandbox settings or socket
behavior were changed. The historical sandbox blocker did not prevent these runs.

Before implementation, the four characterization cases passed (wheel anchoring,
pan, expansion, full screen, real class/property deep links and node selection,
empty/error states). The new controls case failed at the missing Pan right button.
The first implementation pass exposed fractional viewport rounding in centered
zoom; using the actual viewport rectangle fixed it. Screenshot inspection exposed
the overlapping full-screen/tab text, now covered by a non-overlap assertion.

## Acceptance coverage

- AE1 / R1, R3, R4: native Tab/Enter/Space, all pan directions, center zoom,
  exact 20%/400% limits, guarded unavailable buttons, stable focus, no navigation
  fetch, no expansion loss, no control-triggered drag/wheel navigation.
- AE2 / R2, R3: fully offscreen camera, zero-visible text and Fit recovery;
  actual blue node pixels and dark viewport pixels remain inside the map and
  match a projection independently derived from DOM rectangles.
- AE3 / R2, R4, R5: negative/positive dragged positions, full selected-node height,
  child-button-only intersection, oversized graph at the fit floor, divider resize,
  browser resize, hide/resize/show, full screen, expansion and logical focus.
- AE4 / R1, R5: empty/error/loading views, stale detached buttons, repeated mount
  cleanup, no page errors, missing canvas context, backing ratios 1 and 2 without
  compounded drawing transforms.
- R3 / R6: 36px command targets, visible 3px keyboard outlines, wrapping controls
  and overview, desktop/narrow/stacked layouts, 200% root text sizing and reduced
  motion. Full-screen Close, Escape, backdrop and Tab trapping are exercised.

New cues use opaque colors: control borders `#6b7280`, focus outline `#1d4ed8`,
map nodes `#2563eb`, and viewport outline `#111827` on white, all above 3:1.
The readable summary is `#374151` on `#f9fafb`. This is targeted control/overview
coverage, not a whole-page WCAG certification or a manual screen-reader pass.
200% root text sizing is tested; browser-menu page zoom is not claimed.

## Screenshot provenance

Playwright captured the actual local `/explore/tree` page with its normal
Tailwind styling, real tree data and vendored ELK. Only the graph API responses
for the screenshot scenario use the public synthetic branched fixture in
`browser_tests/fixtures/entity_graph.json`. The fixture is expanded to six nodes;
keyboard focus is visible on Pan left. The class/property integration smoke uses
unintercepted graph responses.

- `docs/plans/evidence/fa-2-graph-controls-embedded.png` — 1440 × 1000.
- `docs/plans/evidence/fa-2-graph-controls-fullscreen.png` — 1440 × 1000.
- `docs/plans/evidence/fa-2-graph-controls-narrow.png` — 900 × 1000, divider narrowed.

Reproduction instructions are in `browser_tests/README.md`. The controller owns
publication, campaign reviews and merge. No user decision or held change is needed.
