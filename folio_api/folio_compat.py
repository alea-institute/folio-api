"""folio-python integration helpers: compatibility fixes and startup warm-up.

folio-api now pins folio-python 0.4.1, which includes
alea-institute/folio-python@1b4fb34 ("bound query result caches"), so the
patch below is a no-op (tests/test_folio_compat.py asserts that). It is kept
as a guard while folio-python is installed from a GitHub archive pin that may
be swapped for another build; remove it once a bounded release is the floor
on PyPI.
"""

import logging
import time
from functools import lru_cache

from folio import FOLIO

LOGGER = logging.getLogger("folio_api")

# Same bound folio-python adopted upstream (DEFAULT_SEARCH_CACHE_SIZE).
SEARCH_CACHE_SIZE = 128

# Any real word works; it only has to reach the index build.
_WARMUP_QUERY = "contract"


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


def warm_search_indices(folio: FOLIO, logger: logging.Logger | None = None) -> float:
    """Run one throwaway label and one definition search before serving traffic.

    With folio-python's optional ``kaos`` extra installed, ``search_by_label``
    and ``search_by_definition`` build their BM25 indices lazily on first use
    (~1 s, holding the GIL). Doing that here, during app startup, keeps the
    build off the first user request and off the event loop while it serves.
    On the RapidFuzz path this is just one cheap cached search of each kind.
    Never raises: a failed warm-up only means the first real search pays the
    build cost. Returns the elapsed seconds.
    """
    log = logger or LOGGER
    start = time.perf_counter()
    try:
        folio.search_by_label(_WARMUP_QUERY)
        folio.search_by_definition(_WARMUP_QUERY)
    except Exception:  # pylint: disable=broad-except
        log.warning("FOLIO search index warm-up failed", exc_info=True)
    elapsed = time.perf_counter() - start
    log.info("FOLIO search indices warmed in %.2fs", elapsed)
    return elapsed
