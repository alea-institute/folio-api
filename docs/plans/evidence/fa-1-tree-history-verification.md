# fa-1 browser-history verification

Plan: `docs/plans/2026-10-26-1206-feat-fa-1-browser-history-plan.md`  
Branch: `drawdown/fa-1`  
Implementation reviewed for this receipt: `cf0361f`  
Date: 2026-10-26

## Starting state and authority

The build started at `a1c35e8` with a clean checkout. The supplied plan was
already committed; source inspection confirmed its node-only history and
asynchronous-loading findings. No repository `AGENTS.md` or `CLAUDE.md` was
present. The chief campaign repository and its required excerpt were unavailable
in this clone, as the plan records; campaign rules came from the supplied mandate.
The controller retains the upstream-authority reconciliation responsibility.

Baseline `uv run pytest`: **46 passed**, 16 existing deprecation warnings,
50.01 seconds. No existing tests or assertions were changed.

## Implementation and acceptance evidence

- **U1 / R10-R11:** The isolated unittest harness renders the actual Jinja2 page,
  vendored jQuery, application scripts, CSS, and real ELK. It routes synthetic
  endpoint data without importing the API. Before production edits, two
  characterization checks passed and native Back failed: query stayed `beta`
  when returning to the `alpha` context selection.
- **U2-U3 / R1-R3, R5-R9:** Versioned snapshots contain committed queries,
  occurrence paths, loaded containers, sibling visibility, section visibility,
  and selection. Native Back/Forward, reload, empty/legacy/malformed states,
  hidden selection, duplicated occurrences, query changes, Clear/Escape,
  zero results, retries, missing nodes, and failed history writes are exercised.
  Request barriers verify late root, search, path, reveal, details, and fallback
  responses cannot replace the destination.
- **U3 / R2, R5, R8, R10:** A 60-occurrence view restores all descendants and
  deduplicates repeated parent requests. The test exposed duplicate Expand
  handlers (template onclick plus JS listener); removing the redundant listener
  preserves the intended 50-branch limit. A separate red test reproduced two
  simultaneous full-tree requests; the loader now shares its in-flight promise.
- **U4 / R3-R4, R8:** Ten graph tests cover active/lazy class/property traversal,
  explicit empty selection, graph clicks, failed-search recovery, and late
  fetches, children, real ELK layouts, and queued frames. Before the graph edits,
  tests reproduced retained empty-selection graphs, stale fetch/layout paints,
  and an ELK error from stale children.
- **U5 / R10-R11:** Desktop screenshots show Back restoring `alpha`, revealed
  context, retained descendants and selected details, then Forward restoring
  `beta`. The suite also exercises property selection at 390 × 844 in dark mode.

## Commands and results

Chromium: **156.0.8078.4**, headless through Python Playwright. Ordinary browser
launch worked without socket workarounds. Dependency setup used the `browser`
group; the installer was interrupted after remaining silent, so installation
completion is not claimed. The already available browser ran every check.

Set `FOLIO_BROWSER_TAILWIND` to the pinned cache file as documented in
`tests/browser/README.md` before running browser checks.

| Check | Result |
| --- | --- |
| `uv run --group browser python -m unittest discover -s tests/browser -p '*_browser.py' -v` | 37 passed, 34.935 seconds |
| Same command with `FOLIO_BROWSER_SCREENSHOTS=1` | Both evidence PNGs captured after restored-state assertions |
| `uv run pytest tests/routes/test_tree_search.py tests/routes/test_entity_graph.py tests/test_app_starts.py` | 22 passed, 15 existing warnings, 46.63 seconds |
| `uv run pytest` after implementation | 46 passed, 16 existing warnings, 46.86 seconds; no skips |
| `node --check folio_api/static/js/unified_tree.js` and `node --check folio_api/static/js/entity_graph.js` | Passed |
| `uv run black --check tests/browser` and `git diff --check` | Passed |

## Real-app smoke and visual inspection

A local app started normally with `uv run uvicorn folio_api.api:app --host
127.0.0.1 --port 9616`. Playwright used actual ontology endpoints and searched
`deontic`. For both classes and properties it revealed a sibling, selected that
context and the hit, then traversed Back and Forward while asserting the query,
selected occurrence and details. The active Entity Graph followed both traversal
destinations. No uncaught JavaScript error occurred. This was local integration
verification; no production host or configuration was changed.

Screenshots were captured with animations disabled and visually inspected:

- `docs/plans/evidence/fa-1-tree-history-back.png`
- `docs/plans/evidence/fa-1-tree-history-forward.png`

The fixture uses synthetic/public examples and the existing Tailwind 3.4.17
presentation dependency cached locally. Google Fonts are fulfilled with empty
CSS, so screenshots use the system fallback font. The API payloads, rendered
scripts, native history, and real graph layout execute normally.

## Delivery boundaries

No migration, data rewrite, package release, new outside service, production
change, or credential access was introduced. No owner decision is needed.
This clone has no remote; commits remain local for the controller to publish.
Simplification and code review are the remaining LFG tail at this checkpoint.
