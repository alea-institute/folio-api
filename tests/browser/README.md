# Explorer browser regressions

These `unittest` tests render the real Explorer Jinja2 template and run the real
vendored jQuery, tree, split-pane, and Entity Graph scripts in Chromium. Playwright
routing serves synthetic ontology responses and local static files at
`https://explorer.test`; it never starts or imports the API, reads runtime
configuration, or loads the live ontology. Existing pytest discovery is unchanged.

Install the test-only dependencies and browser:

```bash
uv sync --locked --dev --group browser --python 3.13
uv run --group browser playwright install chromium
```

Cache the page's existing Tailwind presentation dependency once. This is a pinned
copy of the CDN script already used by the template, not an application dependency
or a new service. Browser tests serve the cached bytes locally. Google Fonts are
fulfilled with empty local CSS, so screenshots use the system fallback font.

```bash
mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/folio-api-browser"
curl --fail --location --max-time 45 \
  'https://cdn.tailwindcss.com/3.4.17?plugins=forms,typography,aspect-ratio' \
  --output "${XDG_CACHE_HOME:-$HOME/.cache}/folio-api-browser/tailwind-3.4.17.js"
export FOLIO_BROWSER_TAILWIND="${XDG_CACHE_HOME:-$HOME/.cache}/folio-api-browser/tailwind-3.4.17.js"
sha256sum "$FOLIO_BROWSER_TAILWIND"
```

The reviewed script SHA-256 is
`afcd5f979c919a39cdfafefe983bde4f5bd41caab98cb2eb0efd2cf56b8d1355`.
Use the cached presentation script for verification and screenshots:

```bash
uv run --group browser python -m unittest discover -s tests/browser -p '*_browser.py' -v
```

Missing Playwright or Chromium prerequisites fail the command; they are never
silently skipped. If a restricted runtime rejects browser startup, record the
actual error and rerun in the controller's supported environment without changing
application or socket behavior. No login or external API is required.

Screenshots are opt-in so ordinary verification does not change tracked files:

```bash
FOLIO_BROWSER_SCREENSHOTS=1 uv run --group browser python -m unittest discover -s tests/browser -p '*_browser.py' -v
```

After Back/Forward assertions pass, that command writes
`docs/plans/evidence/fa-5-tree-history-back.png` and
`docs/plans/evidence/fa-5-tree-history-forward.png`. The hidden-tab graph
regression also writes `docs/plans/evidence/fa-5-graph-history-refit.png` after
asserting that the restored graph fits. Screenshot capture requires
`FOLIO_BROWSER_TAILWIND`; a behavioral-only run may omit it, but then utility CSS
is absent and that run does not constitute visual verification.

The ontology suite renders separate FOLIO and Canon documents with explicit
template context. Canon fixtures use full IRIs with matching local names in
different namespaces. Requests must match the rendered document's ontology;
cross-ontology requests and Canon graph requests fail the suite. Coverage includes
document switching, legacy links, details fallback, Clear/Collapse, blocked Canon,
delayed responses, and URL normalization without replacing the saved view.

Both class and property journeys assert independently expanded branches, query,
selection, and details after Back and Forward. The older `fa-1` screenshots and
verification receipt remain historical provenance from PR #33.

Normal tree journeys live in `tree_history_browser.py`; failure, retry, and
stale-response cases live in `tree_history_recovery_browser.py`, using the same
shared helpers and discovery command. Graph tests also verify that a canceled
initial fit resumes when its cached render is reopened, while completed user
zoom remains intact.

The fixtures contain equivalent class/property trees (`c-` / `p-` identifiers),
`alpha`, `beta`, and `shared` searches, context siblings with retained children,
and a shared node under two parents. Any other query returns zero matches. The
fixture details include a cross-type navigation link; graph endpoints support
ancestor and child expansion requests using the same synthetic nodes.

`ExplorerFixtures.hold(fragment)` holds the next matching response. Await the
returned barrier's `wait()` before navigating, and call `release()` after the
new destination settles. `fail_next(fragment, status=503)` injects one HTTP
failure. `requests` counts decoded paths plus raw query strings; `nodes` and
`roots` may be edited to simulate changed ontology data. Tests must release their
barriers; teardown also releases them for failure cleanup. No sleeps are needed.
Unexpected requests and uncaught JavaScript errors fail teardown, with the URLs
or errors reported. Requests for the explicit Tailwind/font presentation resources
are handled locally; every other unrecognized resource is rejected.
