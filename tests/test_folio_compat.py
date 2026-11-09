"""folio-python <= 0.4.0 caches every fuzzy search forever.

FOLIO._basic_search is a static method under an unbounded functools.cache
whose key includes a freshly built tuple of ~20k labels (or definitions), so
each distinct query pinned ~600 KiB until restart: about 5,000 distinct
searches would exhaust the 3.7 GB PROD host. folio-python bounded it to 128
entries in 1b4fb34, released in 0.4.1 (pinned here; tagged on GitHub, not on
PyPI as of 2026-11-09). On 0.4.1 folio_compat must therefore be a no-op.
"""

from functools import cache

import folio
from folio import FOLIO
from folio.graph import DEFAULT_SEARCH_CACHE_SIZE

from folio_api.folio_compat import SEARCH_CACHE_SIZE, bound_folio_search_cache


def test_basic_search_cache_is_bounded(_booted_app):
    info = FOLIO._basic_search.cache_info()
    assert info.maxsize is not None and info.maxsize <= 128, info


def test_many_distinct_searches_stay_within_bound(folio, monkeypatch):
    # _basic_search backs the RapidFuzz path; force it even if kaos is installed.
    monkeypatch.setenv("FOLIO_SEARCH_BACKEND", "rapidfuzz")
    FOLIO._basic_search.cache_clear()
    for i in range(300):
        folio.search_by_label(f"distinct query {i}", limit=3)
    assert FOLIO._basic_search.cache_info().currsize <= 128


def test_repeat_search_is_still_cached(folio, monkeypatch):
    monkeypatch.setenv("FOLIO_SEARCH_BACKEND", "rapidfuzz")
    first = folio.search_by_label("contract law", limit=5)
    hits = FOLIO._basic_search.cache_info().hits
    second = folio.search_by_label("contract law", limit=5)
    assert [c.iri for c, _ in second] == [c.iri for c, _ in first]
    assert FOLIO._basic_search.cache_info().hits == hits + 1


def test_pinned_folio_python_bounds_cache_upstream():
    """The pinned release ships the upstream bound folio_compat mirrors."""
    assert tuple(int(p) for p in folio.__version__.split(".")[:2]) >= (0, 4)
    assert DEFAULT_SEARCH_CACHE_SIZE == SEARCH_CACHE_SIZE


def test_compat_patch_is_noop_on_bounded_release(_booted_app):
    """On folio-python >= 0.4.1 the compat shim leaves upstream's cache alone."""
    before = FOLIO.__dict__["_basic_search"]
    assert bound_folio_search_cache() is False
    after = FOLIO.__dict__["_basic_search"]
    assert after is before
    assert after.__func__.cache_info().maxsize == DEFAULT_SEARCH_CACHE_SIZE


def test_compat_patch_still_bounds_unbounded_cache(monkeypatch):
    """Guard path: an unbounded functools.cache (folio-python <= 0.4.0) is re-wrapped."""
    original = FOLIO.__dict__["_basic_search"]
    underlying = original.__func__.__wrapped__
    monkeypatch.setattr(FOLIO, "_basic_search", staticmethod(cache(underlying)))
    assert FOLIO._basic_search.cache_info().maxsize is None
    assert bound_folio_search_cache() is True
    assert FOLIO._basic_search.cache_info().maxsize == SEARCH_CACHE_SIZE
    assert FOLIO.__dict__["_basic_search"].__func__.__wrapped__ is underlying
