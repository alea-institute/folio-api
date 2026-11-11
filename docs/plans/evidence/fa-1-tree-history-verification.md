# fa-1 browser-history verification

Historical evidence imported from PR #33 (`e377968c`). These results describe
that source branch; current landing verification is recorded separately in
`docs/plans/evidence/fa-5-history-verification.md`.

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
The original checkpoint above preceded the LFG simplification and review tail.

## Prior continuation notes at `508ee77`

The following notes were already present in the working tree when the November
build resumed. Fresh results from that build are recorded separately below.

The build continuation found the implementation and subsequent navigation fixes
already committed on `drawdown/fa-1`. It verified that work rather than rebuilding
it. Two staged planning-file deletions were present at entry and remain excluded
from this continuation's commits.

The first browser invocation failed during fixture setup because the documented
Tailwind cache file was absent. Downloading the pinned presentation script and
verifying its documented SHA-256 resolved that prerequisite. No application or
test behavior changed to make the checks pass.

| Fresh check | Result |
| --- | --- |
| `uv run --group browser python -m unittest discover -s tests/browser -p '*_browser.py' -v` | 51 passed, 46.860 seconds; no skips |
| `uv run pytest` | 46 passed, 16 existing warnings, 50.95 seconds; no skips |
| Both JavaScript files through `node --check` | Passed |
| `uv run black --check tests/browser` | Passed; three files unchanged |
| `uv run --no-project --with ruff==0.6.3 ruff check tests/browser` | Passed |
| `git diff --check` | Passed |

The locally installed environment did not contain Ruff. Running the pinned hook
version through an isolated `uv` environment supplied the tool without changing
project dependencies. No JavaScript lint or typecheck is configured.

An ordinary local app startup also succeeded. Chromium **156.0.8078.4** exercised
`/explore/tree` with actual ontology data and the `deontic` query. For each of
classes and properties, it revealed a sibling, selected that context, selected
the hit, and used native Back and Forward. Assertions checked the query, match
count, selected occurrence, details IRI, and active graph IRI. Both sections
passed with zero uncaught page errors. The app's unavailable LLM integration is
unrelated to these ontology-backed routes; no credential was supplied or changed.

The `ce-simplify-code` pass completed with no applicable changes across reuse,
quality, efficiency, test-value, and comment reviews. All existing API tests and
all added browser proof tests remain intact.

## Build verification on 2026-11-08

Starting revision: `508ee77`; verified implementation revision: `acf3ec1`.
The branch already contained the implementation, browser harness, and earlier
fixes. At entry, the tree script was empty, two additional browser regressions
were uncommitted, and two planning handoff deletions were staged. The starting
changes were backed up before restoring the script from Git. The new tests were
retained, their failures reproduced, and the corresponding fixes committed.
The staged handoff deletions remain excluded from this build's commits.

The new regressions demonstrated two observable defects before the fixes:

- Canceled expansion and sibling requests left a loading indicator in all four
  class/property cases. Navigation now clears obsolete indicators and releases
  their controls immediately. Releasing an older response cannot unlock a newer
  request or overwrite its destination selection.
- Details links selected offscreen targets without scrolling to them. All three
  cases failed: already loaded targets, newly loaded targets, and legacy node
  URLs. Each now reveals the selected target while retaining its history entry
  behavior.

| Fresh check | Result |
| --- | --- |
| Two new browser regressions before the fixes | Failed at the expected assertions: four cancellation cases and three offscreen-selection cases |
| The same two regressions after the fixes | 2 passed, 8.266 seconds |
| `uv run --group browser python -m unittest discover -s tests/browser -p '*_browser.py' -v` with screenshot capture enabled | 53 passed, 84.061 seconds; no skips |
| `uv run pytest` | 46 passed, 16 existing warnings, 89.94 seconds; no skips |
| Both application JavaScript files through `node --check` | Passed |
| `uv run black --check tests/browser` | Passed |
| `uv run --no-project --with ruff==0.6.3 ruff check tests/browser` | Passed |
| `git diff --check` | Passed |

The API run began as the starting-state check and completed during the frontend
fixes; API code, fixtures, and existing tests were unchanged. It includes the
route and app-start tests named in the plan. No configured JavaScript lint or
typecheck exists. No existing test or assertion was removed or weakened.

Chromium **156.0.8078.4** launched normally through the existing Python Playwright
harness. The pinned Tailwind cache was downloaded and its documented SHA-256
verified. Both screenshots were regenerated after their assertions passed and
visually inspected; their bytes match the images already committed on the branch:

- `docs/plans/evidence/fa-1-tree-history-back.png`
- `docs/plans/evidence/fa-1-tree-history-forward.png`

An ordinary local Uvicorn process served the actual ontology. A fresh Playwright
smoke check searched for `deontic`, revealed sibling context, selected that
context and then a search hit, and traversed Back and Forward for both classes
and properties. It checked query, match count, selected occurrence, details IRI,
and active graph IRI at each destination. Both flows passed with zero uncaught
page errors. The app's unavailable LLM integration was not needed by these flows.
No credential or production access was used.

The continuation simplification pass found no worthwhile changes across reuse,
quality, efficiency, and test value. Its two proof tests remained unchanged.
The complete feature review and final local delivery receipt follow below.


## Review fix and final verification

The complete feature review identified a compatibility regression for valid
ontology links whose path begins outside the curated root list. The previous
browser loaded their details even when it could not show a tree occurrence;
the new history implementation initially treated that case as missing.

Commit `a04b303` retains an explicit details-only selection for that valid entity.
The saved selection carries its canonical IRI and type, allowing Back, Forward,
and reload to restore details and notify the graph. Tree selection and Clear
remove it. Ordinary root lists are unchanged, and genuinely missing paths still
use the existing missing-item behavior.

Two additional regression methods failed before the fix (three subcase failures)
and passed afterward in 3.874 seconds. They exercise class/property legacy links,
details links, Back/Forward, reload, the active graph, and Clear.

Final implementation verification at `a04b303`:

- Full browser suite with screenshot capture: **55 passed**, 64.087 seconds,
  no skips. The two images remain byte-identical to the committed screenshots.
- The local real-app smoke was repeated after this fix. Both class and property
  search/reveal/select/Back/Forward flows passed, including details and active
  graph selection, with **zero uncaught page errors**.
- JavaScript syntax, Black, Ruff, and whitespace checks passed. The **46 passing
  API tests** above remain applicable: backend code, API tests, dependencies,
  and runtime configuration did not change during review fixes.


The second review finding concerned new drags on the outgoing graph while tree
navigation was pending. Commit `eb451ec` prevents both pan and node-drag starts
during that interval. The pointer regression failed before the guards for both
gestures, then passed in 1.735 seconds. It checks that the destination transform
stays unchanged and that fresh gestures work once navigation completes.

Final browser verification at `eb451ec`: **56 passed**, 64.929 seconds, no skips,
with screenshot capture enabled. Both screenshots remain identical to the
committed evidence. JavaScript syntax, Black, Ruff, and whitespace checks pass.
No existing test or assertion was deleted or weakened.


The complete review covered correctness, test coverage, maintainability,
reliability, frontend races, and the repository's recorded browser-testing
constraint. Its two findings were fixed in `a04b303` and `eb451ec`. An independent
validator reproduced the original failures and verified both repairs against
`eb451ec`; no unresolved code issue remained. The regression tests carry the
lessons, so no separate learning artifact was needed.

Delivery remains local-only. The controller owns the campaign-authority excerpt
reconciliation, scan, publication, and campaign merge-gate reviews. The chief
repository is absent from this sandbox; no remote or credentials were sought.
No production/configuration change, migration, data rewrite, package release,
new outside service, or owner-only decision is part of this item.
