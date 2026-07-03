"""Regression tests for static-asset cache-busting.

A stale cached ``unified_tree.js`` (served with only ETag/Last-Modified and no
Cache-Control) once left the Entity Graph tab present but non-functional for
returning visitors. The fix: version asset URLs with ``?v=<mtime>`` and send an
explicit ``Cache-Control`` so browsers revalidate. These tests lock that in.
"""

import re


def test_tree_assets_are_version_stamped(client):
    """App JS/CSS in the tree page carry a ``?v=<digits>`` cache-busting token."""
    html = client.get("/explore/tree").text
    for asset in (
        "css/styles.css",
        "js/copy_iri.js",
        "js/split_pane.js",
        "js/unified_tree.js",
        "js/entity_graph.js",
    ):
        assert re.search(
            rf"/static/{re.escape(asset)}\?v=\d+", html
        ), f"{asset} is not version-stamped in /explore/tree"


def test_static_assets_send_cache_control(client):
    """Static responses carry a revalidating Cache-Control header."""
    response = client.get("/static/js/entity_graph.js")
    assert response.status_code == 200
    cache_control = response.headers.get("cache-control", "")
    assert "must-revalidate" in cache_control, (
        f"expected a revalidating Cache-Control, got: {cache_control!r}"
    )


def test_version_stamped_url_still_serves(client):
    """The ``?v=`` query does not break static file resolution."""
    response = client.get("/static/js/unified_tree.js?v=1234567890")
    assert response.status_code == 200
