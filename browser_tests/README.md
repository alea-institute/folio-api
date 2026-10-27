# Graph browser checks

These opt-in tests use the real `/explore/tree` page, vendored ELK and other assets.
The suite lives outside `tests/` so collection never imports the API conftest.
Default API test discovery is unchanged.

```sh
uv sync --group browser
uv run --group browser playwright install chromium
uv run uvicorn folio_api.api:app --host 127.0.0.1 --port 9616
# In another terminal:
uv run --group browser pytest -o addopts='' browser_tests/entity_graph_controls.py --browser chromium --base-url http://127.0.0.1:9616
```

The class/property smoke uses the running ontology without interception. Other
cases intercept only graph API responses with synthetic public data. Neither
ELK nor graph DOM, transforms, controls, geometry, or canvas rendering is mocked.
The application and its normal Tailwind CDN styling must be available.

To reproduce the visual evidence, add
`--graph-evidence-dir docs/plans/evidence`. Screenshots are captured by the visual
check after a graph has expanded, with keyboard focus visible. Missing app,
browser, or styling is a failure, not a skip. Coverage remains enabled for
`uv run pytest tests`; it is disabled only in this separate browser process.
