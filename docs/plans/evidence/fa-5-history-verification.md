# Browser history landing verification

Plan: `docs/plans/2026-11-11-0153-feat-fa-5-land-history-plan.md`

Branch: `drawdown/fa-5`

Final source/test candidate: `0d5e4ed`

Source PR head: `e377968c0c1a4aa4bd4fa55ba8efd2876e18242a`

Date: 2026-11-11

## Landing and preservation

Replayed all twelve source commits onto the supplied baseline `53a615e`, after
the committed plan `e3846ab`. Local `main` (`36a0e97`) is older than that baseline;
it was not substituted for the supplied current code. The successor PR
supersedes **#33**.

Conflict resolution retains occurrence-based history, cancellation of stale
tree/details/graph work, ontology-scoped requests, full Canon identifiers, and
the blocked-page guard. Restoring a snapshot now normalizes the ontology URL
while preserving the complete destination state and history length. No server
code or template changed. The current Python and package requirements remain;
the only manifest addition is the imported test-only browser group.

All 45 imported tree tests and 11 graph tests remain. The primary class journey
now asserts distinct expanded branches in both directions; a property journey
and seven ontology integration tests were added. The other 55 imported test
methods are unchanged, confirmed by AST comparison. No existing pytest test was
edited. Canon fixtures reject requests routed to the wrong ontology and use
different namespaces with matching local names.

The final review added a graph regression, bringing the browser suite to 65.
It also moved 21 recovery tests into `tree_history_recovery_browser.py` and four
common helpers into `support.py`. AST comparison confirmed all 64 pre-review
test methods remain identical after that move, with no duplicate test names.

The imported recovery notes were removed only after byte-for-byte comparison
against their recoverable copies in the source commit. Historical source plans,
screenshots, and verification remain identified as provenance, not current
acceptance evidence.

## Verification

| Check | Result |
|---|---|
| `uv sync --locked --dev --group browser --python 3.13` | Passed; Python 3.13.11, Playwright 1.64.1, current dependency requirements retained |
| Existing pytest baseline | 230 passed, 47 warnings, 86.41 seconds; report gate accepted |
| Imported browser suite before new integration tests | 56 passed, 55.850 seconds |
| New URL-normalization regression before fix | Failed for both redundant `FOLIO` and uppercase `CANON` selectors; saved snapshots otherwise restored |
| Final `uv run --no-sync pytest tests -ra --junitxml=test-results/pytest.xml` | 230 passed, 47 warnings, 92.11 seconds |
| `uv run --no-sync python scripts/check_pytest_results.py test-results/pytest.xml` | Accepted 230 test cases, no skips, failures, or errors |
| Final `uv run --no-sync python -m unittest discover -s tests/browser -p '*_browser.py' -v` with screenshot capture enabled | 65 passed, 69.776 seconds; no skips, unexpected requests, or uncaught JavaScript errors |
| Hidden graph fit regression before/after fix | Failed before the fix because the selected node was outside the viewport; passed after the fix, including preservation of subsequent user zoom |
| Class Back/Forward journey at 390 × 844 | Passed with the same assertions; screenshots inspected |
| `uv run --no-sync black --check tests/browser` | Passed |
| `node --check` for both changed scripts; `git diff --check` | Passed |

Repository-wide `uv run --no-sync pylint folio_api` remains nonzero with a
9.43/10 score. Its findings are in unchanged backend Python files; they are not
part of this frontend landing. The required test and report gates pass.

The browser harness runs the actual template, scripts, native browser history,
and graph layout against synthetic endpoint responses. The full pytest suite
covers real route and application-start contracts. No socket or application
monkeypatch was needed for these commands.

The new integration tests cover class/property links with distinct full Canon
IRIs, legacy path loading and JSON details fallback, switching documents and
restoring their ontology/graph context, Clear and Collapse URL preservation,
blocked Canon states, delayed details across traversal, and normalization on
Back and reload without overwriting snapshots. Collapse intentionally retains
the hidden selection in the snapshot, matching existing behavior and its
regression test.

## Visual evidence

Fresh screenshots captured after assertions passed, at 1440 × 1000:

- `docs/plans/evidence/fa-5-tree-history-back.png`: restored `alpha` query,
  expanded context, selected Retained Concept, and matching details.
- `docs/plans/evidence/fa-5-tree-history-forward.png`: restored `beta` query,
  expanded Shared Concept branch, selected Beta Concept, and matching details.
- `docs/plans/evidence/fa-5-graph-history-refit.png`: a graph mounted while
  hidden, then reselected and reopened with its focus node in view.

Both desktop captures and the mobile journey were visually inspected. The
pinned local Tailwind 3.4.17 script matches SHA-256
`afcd5f979c919a39cdfafefe983bde4f5bd41caab98cb2eb0efd2cf56b8d1355`.
Google Fonts are served empty local CSS; screenshots use the fallback font.

## Review and browser close-out

The local review covered correctness, testing, maintainability, reliability,
frontend races, and repository learnings. An independent validator confirmed
both findings: the oversized tree test module and a canceled initial graph fit.
Both are resolved in `0d5e4ed`; no actionable finding or settlement conflict
remains. Controller campaign reviews are still required.

The graph now tracks whether its initial fit completed. Reopening a cached graph
reschedules only an unfinished fit, so a completed view retains user zoom.
Simplification also consolidated Search and Clear failure recovery and removed
redundant fallbacks after validated search responses. The full final suites
cover these changes.

The graph regression itself holds the durable lesson. The `ce-compound`
assessment found no additional reasoning or new domain vocabulary requiring a
separate learning document: **Documentation skipped**.

The `ce-test-browser` pipeline used the plan-mandated existing Playwright
harness, with local route fulfillment at `https://explorer.test`; no additional
browser stack or live server was introduced. This follows the user's explicit
Playwright and isolated-suite requirements. The browser route scope is:

| Route/context | Status | Coverage |
|---|---|---|
| `/explore/tree` | Pass | Class/property Back and Forward, branch context, selection/details, graph cancellation and refit, desktop and mobile |
| `/explore/tree?ontology=canon` | Pass | Full identifiers, ontology-scoped requests, document traversal, URL normalization, delayed details, blocked states |

The browser harness reported no uncaught JavaScript errors or unexpected
requests. Six final clean-flow smoke cases additionally captured console errors
and reported none. No route was skipped and no external human verification was
needed.

The pre-compaction hook persisted reviewed fixes and simplification in
`0d5e4ed`. Its generated recovery notes were removed only after exact comparison
with their Git-backed copies in that commit; this receipt is the current
handoff record.

## Delivery boundaries

The chief campaign repository and required excerpt are unavailable in this
clone. The supplied mandate governs this build; the controller retains excerpt
reconciliation and publication-base checks. There is no remote, and no push,
PR creation, production access, credential access, migration, data rewrite,
release, or new outside service was attempted. The controller publishes the
local branch and completes campaign reviews and merging.
