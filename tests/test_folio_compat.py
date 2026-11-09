"""folio-python <= 0.4.0 caches every fuzzy search forever.

FOLIO._basic_search is a static method under an unbounded functools.cache
whose key includes a freshly built tuple of ~20k labels (or definitions), so
each distinct query pinned ~600 KiB until restart: about 5,000 distinct
searches would exhaust the 3.7 GB PROD host. folio-python bounded it to 128
entries in 1b4fb34 (released after 0.4.0, unpublished as of 2026-11-09).
"""

from folio import FOLIO


def test_basic_search_cache_is_bounded(_booted_app):
    info = FOLIO._basic_search.cache_info()
    assert info.maxsize is not None and info.maxsize <= 128, info


def test_many_distinct_searches_stay_within_bound(folio):
    FOLIO._basic_search.cache_clear()
    for i in range(300):
        folio.search_by_label(f"distinct query {i}", limit=3)
    assert FOLIO._basic_search.cache_info().currsize <= 128


def test_repeat_search_is_still_cached(folio):
    first = folio.search_by_label("contract law", limit=5)
    hits = FOLIO._basic_search.cache_info().hits
    second = folio.search_by_label("contract law", limit=5)
    assert [c.iri for c, _ in second] == [c.iri for c, _ in first]
    assert FOLIO._basic_search.cache_info().hits == hits + 1
