# Graph browser checks

These tests use the real `/explore/tree` page, vendored ELK and other assets.
The suite lives outside `tests/` so collection never imports the API conftest.
Default API test discovery is unchanged.

```sh
uv sync --locked --dev --group browser
uv run --no-sync playwright install chromium
uv run --no-sync python -m browser_tests.app
# In another terminal:
uv run --no-sync pytest -o addopts='' browser_tests/entity_graph_controls.py browser_tests/test_entity_graph_accessibility.py --browser chromium --base-url http://127.0.0.1:9616 --output=test-results/playwright --junitxml=test-results/graph-browser.xml
uv run --no-sync python scripts/check_pytest_results.py test-results/graph-browser.xml
```

The launcher enters `tests.support.isolated_environment()` before application
imports and keeps it active through shutdown. It uses the checked local FOLIO and
Canon snapshots and nonsecret test config; it needs no runtime credentials or
ontology downloads. Startup waits for both ontologies, and failed startup or
shutdown isolation checks produce a failed process exit. Stop it with SIGTERM
after testing and check the exit status.

Each browser test context supplies a distinct reserved benchmark client address
through the local proxy header. This isolates users' rate buckets while keeping
the real rate limiter and its default limits enabled.

The class/property smoke uses the running ontology without interception. Other
cases intercept only graph API responses with synthetic public data. Neither
ELK nor graph DOM, transforms, controls, geometry, or canvas rendering is mocked.
The application and its normal Tailwind CDN styling must be available.

To capture current visual evidence, add
`--fa6-evidence-dir docs/plans/evidence`. This writes three `fa-6-graph-controls-*.png`
images and preserves the historical fa-2 captures. The inherited
`--graph-evidence-dir` option writes fa-2 filenames; use a scratch directory when
reproducing those. Screenshots are captured after a graph has expanded, with
keyboard focus visible. Missing app,
browser, or styling is a failure, not a skip. Coverage remains enabled for
the API suite; it is disabled only in this separate browser process.

Playwright clears its `--output` directory at session start. Keep that directory
separate from JUnit reports and server logs. When the browser group is installed,
run API tests with `uv run --no-sync pytest tests --output=test-results/api-playwright
--junitxml=test-results/pytest.xml` for the same reason. The API-only CI install
does not load Playwright and needs no output override.

`.github/workflows/graph-browser-tests.yml` explicitly runs both modules (the
inherited filename does not match default discovery), checks the separate JUnit
report, checks server shutdown, and uploads the server log and fresh screenshots.
The existing API workflow remains unchanged. On a restricted workstation, set
`PLAYWRIGHT_BROWSERS_PATH` to a writable cache directory for both installation and
execution; do not patch sockets or event loops to manufacture a passing run.
