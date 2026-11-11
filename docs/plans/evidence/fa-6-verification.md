# Graph controls replacement verification

Date: 2026-11-11. Item: fa-6. Branch: `drawdown/fa-6`.

The controller's replacement PR supersedes **#24 and #34**. This lane commits
locally; publication and campaign review/merge gates remain with the controller.

## Integration

- Build intake was clean at `3594c42`, the committed fa-6 plan on integration
  baseline `53a615e`. The supplied head `efb88fa54bcaa47b274486f3e9d96f8376d71da0`
  existed. Its five commits after merge base `9b34af3` were cherry-picked in order.
- The only cherry-pick conflict was `uv.lock`. Resolution retained every existing
  package version and current Python/application requirements, adding only the
  browser group's five packages. `uv sync --locked --dev --group browser` passed.
- Graph JavaScript, tree template, and the inherited browser-test module match the
  supplied PR head byte-for-byte. Graph styling has one further selector repair
  for Canon's existing single-tab layout. No existing API test was changed.
- Implementation and added tests were committed at `6767765`. The graph source
  was restored by `ffe356d` and `78067ed`; the latest imported commit is `fb35e82`.
- The reviewed Canon layout repair and its regression test were committed at
  `d2d5293`. Final full-suite results below include this repair.
- Local `main` is the older `36a0e97`. Review uses the actual starting commit,
  `3594c42`, to distinguish this item from pre-existing integration work. The diff
  against local `main` contains the graph source and tests, but no remote exists
  to verify canonical-main freshness. The controller owns final reconciliation.
- No production box, runtime config, migration, data rewrite, package release,
  new service, credential, or security setting was changed.

## Executed checks

Python 3.13.11; pytest 8.4.2; pytest-playwright 0.10.0; Playwright 1.65.0;
Chromium 158.0.8127.18. The real application, MCP lifespan, sockets, event loop,
ELK layout, DOM, CSS, and canvas all ran without runtime shims.

| Check | Result |
|---|---|
| Full API suite with coverage | **230 passed**, 0 skipped, 47 warnings; 73% coverage |
| Both browser modules | **56 passed**, 0 skipped: 20 inherited and 36 added cases |
| Separate JUnit report checks | Both accepted; no skips, failures, or errors |
| Browser CI shell, executed locally | Passed readiness, all 56 cases, server-log retention, and graceful server shutdown with exit 0 |
| Occupied-port startup failure | Second launcher exited 1 and completed application shutdown; the original test server stayed usable |
| Graph JavaScript syntax | `node --check folio_api/static/js/entity_graph.js` passed |
| Added/changed browser Python | Black checks and Ruff 0.6.3 checks passed |
| Workflow shell and YAML | Parsed successfully; `bash -n` passed |
| Whitespace/conflict check | `git diff --check` passed |

Reproduction (after installing the locked development/browser dependencies and
Chromium; the launcher must run in another terminal for the browser command):

```sh
uv run --no-sync python -m browser_tests.app
uv run --no-sync pytest tests -ra --output=test-results/api-playwright --junitxml=test-results/pytest.xml
uv run --no-sync python scripts/check_pytest_results.py test-results/pytest.xml
uv run --no-sync pytest -o addopts='' browser_tests/entity_graph_controls.py browser_tests/test_entity_graph_accessibility.py --browser chromium --base-url http://127.0.0.1:9616 --output=test-results/playwright --junitxml=test-results/graph-browser.xml --fa6-evidence-dir docs/plans/evidence
uv run --no-sync python scripts/check_pytest_results.py test-results/graph-browser.xml
```

Stop the launcher with SIGTERM and require exit 0. The workflow implements bounded
readiness and cleanup in the same shell as pytest. The output flags above keep
Playwright's automatic directory cleanup away from the reports and server log.
On a machine with a read-only default browser cache, set `PLAYWRIGHT_BROWSERS_PATH`
to a writable cache directory consistently for installation and execution.

## What the added coverage proves

- Every pan/zoom/Fit button accepts Enter and Space in embedded and full-screen
  views, reached by Tab or Shift+Tab. Assertions cover camera movement and real
  node geometry, visible focus, announcements, selection, expanded children, and
  unchanged graph-request counts. Fit starts with the graph offscreen.
- Full screen opens and closes by keyboard, retains the same pane and camera,
  returns focus to its trigger, and permits continued keyboard navigation.
- Keyboard expansion changes three nodes to six and updates the canvas and
  visible-node summary before any later Fit, resize, or pan. Selection, camera,
  and focus remain intact. The passive canvas is absent from accessibility and
  Tab order, while its summary remains available.
- The isolated launcher initializes both FOLIO and Canon using the checked local
  snapshots. Existing unintercepted class/property graph navigation still passes.
- Canon retains its full-width Details tab without graph or full-screen controls.

Two temporary mutations confirmed that this is regression coverage: disabling
Pan left failed the new keyboard test at its camera assertion; suppressing
minimap rendering after expansion failed the new expansion test at its rendered
pixel assertion. Both returned pytest exit 1. Source was restored byte-for-byte,
then the full browser workflow passed again. No mutation is included in the diff.

## Test isolation repairs

The initial combined browser run returned 51 passes and four setup errors because
all fresh browser contexts shared the loopback rate bucket. Each context now has
a distinct reserved benchmark address through the local proxy header; the real
rate limiter and default limits remain enabled. The subsequent 55-case run passed.

The first workflow dry run also showed that pytest-playwright clears its default
`test-results` directory. The workflow and documented commands now assign it a
dedicated subdirectory, and the workflow explicitly requires the server log to
survive. A fresh full API/browser run retained both accepted reports and the log.

## Visual evidence

Fresh Playwright captures of the real `/explore/tree` page, with an expanded
six-node graph and visible keyboard focus, were visually inspected:

- `docs/plans/evidence/fa-6-graph-controls-embedded.png`
- `docs/plans/evidence/fa-6-graph-controls-fullscreen.png`
- `docs/plans/evidence/fa-6-graph-controls-narrow.png`
- `docs/plans/evidence/fa-6-canon-details.png` (corrected Canon tab layout)

The three graph captures show normal page styling, reachable controls, a minimap,
and its readable summary. The Canon capture shows the preserved single-tab layout.
Inherited checks also cover the stacked mobile layout, enlarged text,
reduced motion, offscreen recovery, resizing, node dragging, and disposal.
Historical fa-2 screenshots and receipts remain intact.

## Review and resolution

Local review run: `fa6-review-20261111`, reviewing the implementation snapshot at
`6767765`. Final checks ran after the resulting repair at `d2d5293`.

Five independent simplification reviewers completed their passes. No changes
were warranted; test proof, accessibility safeguards, and inherited source
provenance were preserved.

The code review covered correctness, testing, maintainability, frontend races,
launcher/CI reliability, and applicable repository learnings. Two reviewers
identified one introduced defect: the unqualified `#detail-tabs` three-column
rule also applied to Canon, which renders only a Details tab. Independent
validation confirmed it. The new browser regression first failed with a
479.40625-pixel Details button in a 958.8125-pixel tab bar.

Commit `d2d5293` limits that rule to the existing FOLIO `grid-cols-2` element. The
same regression passed, and the final complete API and browser suites passed.
All actionable review findings were resolved. The existing out-of-order entity
selection fetch race was identified as pre-existing and outside this item.

## Limits and controller checks

These results establish local verification, not a GitHub-hosted CI run or manual
screen-reader certification. The chief repository was absent during build as it
was during planning; the controller must compare its campaign Goal Capsule and
cited rules. Readiness timeout and shutdown isolation violations were reviewed
but not separately fault-injected. No Damien-only decision or held change was
identified.
