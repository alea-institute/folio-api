"""Compatibility fixes for the pinned folio-python release.

Remove this module once folio-api depends on a folio-python release that
includes alea-institute/folio-python@1b4fb34 ("bound query result caches").
"""

from functools import lru_cache

from folio import FOLIO

# Same bound folio-python adopted upstream (DEFAULT_SEARCH_CACHE_SIZE).
SEARCH_CACHE_SIZE = 128


def bound_folio_search_cache(maxsize: int = SEARCH_CACHE_SIZE) -> bool:
    """Bound FOLIO._basic_search's result cache if it is unbounded.

    folio-python <= 0.4.0 wraps the static method in functools.cache, keyed
    on the query plus a freshly built tuple of ~20k labels or definitions.
    Every distinct query therefore pinned ~600 KiB for the life of the
    process. Re-wrap the same underlying function in an LRU cache; a no-op
    on releases that already bound it. Returns True if it patched.
    """
    wrapper = FOLIO.__dict__["_basic_search"].__func__
    if wrapper.cache_info().maxsize is not None:
        return False
    FOLIO._basic_search = staticmethod(lru_cache(maxsize=maxsize)(wrapper.__wrapped__))
    return True
