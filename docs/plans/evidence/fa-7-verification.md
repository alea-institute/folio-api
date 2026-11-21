# fa-7 integration verification

Status: implementation committed locally; browser acceptance and fresh screenshots
remain pending on the supported host. This is not a passing browser receipt.
The replacement PR supersedes #49 and #24 (and the intervening #34).

## Starting point and restored source

- Work stayed on `drawdown/fa-7`, starting at plan commit `3f5a9c1`, above supplied
  baseline `d91a8cb`. That baseline includes #48 history and #50 telemetry.
- Local `main` (`36a0e97`) is older than the supplied baseline. The controller
  must check canonical-main freshness and clean application before publishing.
- Source head `f6fa3f7eed87d71b44436b8a2d80b6698cc68781` was present. The complete
  nine-commit range after common base `53a615e` was cherry-picked. Conflicts in
  `entity_graph.js`, `pyproject.toml`, and `uv.lock` were reconciled by hunk.
- The combined browser group retains `playwright>=1.55,<2` and adds
  `pytest-playwright>=0.10.0`. The lock uses incoming Playwright 1.65.0 and keeps
  the supplied production dependencies, Python constraint, and MCP telemetry.
- No repository or ancestor instruction file or chief repository was available
  in the clone. The supplied mandate and committed item plan governed this run;
  the chief plan's Goal Capsule and cited campaign rules were not independently
  read. The controller still owns that comparison.
- No remote was added, credentials sought, push attempted, production host
  touched, or outside service introduced. No migration, rewrite, or release is
  included.

## Implementation and regression coverage

`641aac4` integrates mounted graph resources with accepted Explorer navigation.
Pending navigation cancels frames and focus requests, suspends controls, wheel,
pan, and observer updates, and retains the old mount for possible reuse. An
accepted cached selection refreshes ownership and measurement without resetting
completed user zoom. Initial fitting remains pending until measurable, and a
successful Fit clears both fit flags.

`e3065f5` addresses two review findings. Detached viewport events must target the
active mount. Expansion data is committed only after the latest valid layout
succeeds; a current layout failure leaves the accepted graph and expansion state
available for keyboard control and retry. Concurrent expansion responses retain
their accumulated candidate data, while stale results cannot publish.

All 65 original history methods and all 25 original graph test functions remain.
The resulting suites contain 69 history methods and 27 graph functions,
parametrized into 58 pytest cases. Added coverage includes:

- Pending navigation, wheel/Fit/keyboard controls, retained camera and minimap,
  same-selection recovery, and queued observer callbacks.
- Back/Forward replacement, detached old viewport and button events, unchanged
  history length for camera controls, and stale expansion focus restoration.
- Class/property query, independent branches, occurrence, selection, and details
  assertions retained, with keyboard/minimap checks after restoration.
- Empty graph UI disposal and Canon history with full-width Details and no graph
  requests or controls.
- Rejected ELK expansion followed by keyboard pan and expansion retry.
- Opt-in, navigation-aware embedded/fullscreen/narrow graph screenshots. Narrow
  capture verifies that the divider actually reduced the pane width.

The graph workflow explicitly invokes both the history unittest harness and the
isolated real-app pytest harness. API CI remains unchanged. Historical fa-2 and
fa-6 screenshots retain their original names and are not evidence for fa-7.

## Checks in this lane

| Check | Result |
|---|---|
| Locked dependency installation, Python 3.13 | Passed |
| `uv lock --check` | Passed; 105 packages |
| JavaScript `node --check` | Passed |
| Python `compileall` for both browser harnesses | Passed |
| Black check of modified browser Python files | Passed |
| Graph CI YAML and `bash -n` on every shell block | Passed |
| Browser pytest collection | 58 cases collected; no browser started |
| AST comparison of inherited test method names | No original methods removed |
| `git diff --check` | Passed |
| API suite and JUnit no-skip checker | `e3065f5`: 237 passed, 74% coverage; all records accepted |
| History and graph browser execution | Pending; not run in this lane |
| Fresh fa-7 screenshots and visual inspection | Pending; none generated or committed |

An initial API run reported all tests passing but exceeded a 90-second process
limit during cleanup. A subsequent run with the CI-sized 480-second limit exited
successfully, reporting 237 passed in 84.71 seconds; the no-skip checker accepted
all 237 records. That successful run occurred during integration. Browser red/green
proof was not attempted: lane instructions expressly prohibit Chromium launch.
Static checks and collection do not establish browser behavior.

The final rerun at source revision `e3065f5` exited zero: 237 passed, 47 existing
deprecation warnings, 84.95 seconds, 74% coverage. The JUnit no-skip checker again
accepted all 237 records. Subsequent changes only update documentation and this
receipt.

## Review

The simplification pass used separate reuse, quality, efficiency, test-value,
and comment reviews. It consolidated repeated zoom values and render ownership
checks, reused the minimap's position snapshot, and removed redundant comments.
Defensive mount guards and all proof tests were retained. Test findings led to
explicit frame draining/capture checks and a narrow-pane width assertion.

Code review identified the detached viewport and failed expansion issues fixed
in `e3065f5`. Static follow-up confirmed those corrections; behavioral validation
remains pending. Required campaign review and publication gates belong to the
controller; a local review does not substitute for its Fable review.

Review run `20261121-142942-kDal3AtM` completed with verdict **Not ready**. It
reviewed the frozen integration at `641aac4` and separately checked the fixes at
`e3065f5`. Correctness, testing, maintainability, reliability, and frontend-race
lenses ran. The remaining actionable gate is to execute both browser suites,
inspect and commit the seven fresh screenshots, and finish controller acceptance.
No independent adversarial peer was selected. The browser-test stage stopped at
the explicit lane prohibition before opening a browser; both `/explore/tree`
and `/explore/tree?ontology=canon` remain unverified in a browser here.

The `ce-compound` capture was skipped: the browser fixes have not yet received
behavioral verification, and the new regressions already encode the discovered
failure cases. No unverified solution document was added.

## Supported-host acceptance commands

Run from the repository root. Do not run browser commands in the restricted lane.

```bash
uv sync --locked --dev --group browser --python 3.13
uv run --no-sync playwright install chromium
mkdir -p test-results
uv run --no-sync pytest tests -ra --output=test-results/api-playwright --junitxml=test-results/pytest.xml
uv run --no-sync python scripts/check_pytest_results.py test-results/pytest.xml

curl --fail --location --max-time 45 'https://cdn.tailwindcss.com/3.4.17?plugins=forms,typography,aspect-ratio' --output test-results/tailwind-3.4.17.js
printf '%s\n' 'afcd5f979c919a39cdfafefe983bde4f5bd41caab98cb2eb0efd2cf56b8d1355  test-results/tailwind-3.4.17.js' | sha256sum --check
FOLIO_BROWSER_TAILWIND=test-results/tailwind-3.4.17.js FOLIO_BROWSER_SCREENSHOTS=1 FOLIO_BROWSER_EVIDENCE_PREFIX=fa-7 uv run --no-sync python -m unittest discover -s tests/browser -p '*_browser.py' -v
```

Run the graph suite with managed server cleanup, bounded readiness, and separate
artifact directories:

```bash
set -e
.venv/bin/python -u -m browser_tests.app > test-results/graph-server.log 2>&1 &
server_pid=$!
trap 'kill -TERM "$server_pid" 2>/dev/null || true; wait "$server_pid" || true' EXIT
ready=false
for attempt in $(seq 1 90); do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    cat test-results/graph-server.log
    exit 1
  fi
  if curl --fail --silent --max-time 2 http://127.0.0.1:9616/info/health > /dev/null; then
    ready=true
    break
  fi
  sleep 1
done
if [ "$ready" != true ]; then
  cat test-results/graph-server.log
  exit 1
fi
uv run --no-sync pytest -o addopts='' browser_tests/entity_graph_controls.py browser_tests/test_entity_graph_accessibility.py --browser chromium --base-url http://127.0.0.1:9616 --output=test-results/playwright --junitxml=test-results/graph-browser.xml --fa7-evidence-dir docs/plans/evidence
uv run --no-sync python scripts/check_pytest_results.py test-results/graph-browser.xml
test -s test-results/graph-server.log
kill -TERM "$server_pid"
wait "$server_pid"
trap - EXIT
```

Inspect and commit these expected images after the assertions pass:

- `docs/plans/evidence/fa-7-graph-controls-embedded.png`
- `docs/plans/evidence/fa-7-graph-controls-fullscreen.png`
- `docs/plans/evidence/fa-7-graph-controls-narrow.png`
- `docs/plans/evidence/fa-7-tree-history-back.png`
- `docs/plans/evidence/fa-7-tree-history-forward.png`
- `docs/plans/evidence/fa-7-graph-history-refit.png`
- `docs/plans/evidence/fa-7-canon-details.png`

The routed history fixtures use synthetic ontology data, real page assets, pinned
Tailwind, and fallback fonts. The graph harness uses the isolated real app and
checked ontology snapshots, with synthetic graph responses for focused cases.
Neither scope proves production reachability or manual screen-reader behavior.
