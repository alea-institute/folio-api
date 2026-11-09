"""folio-python search backend as wired into folio-api.

folio-api installs folio-python's optional ``kaos`` extra (kaos-nlp-core BM25
label/definition search, Python >= 3.13). The indices are built lazily, so the
app warms them during startup; ``FOLIO_SEARCH_BACKEND=rapidfuzz`` restores the
RapidFuzz path.
"""

import logging

import pytest
from folio import kaos_search

from folio_api.folio_compat import warm_search_indices

DIVORCE_QUERY = "dissolution of a marriage"


def _labels(payload):
    return [cls["label"] for cls, _score in payload["results"]]


def test_kaos_backend_is_installed_and_enabled():
    assert kaos_search.KAOS_AVAILABLE
    assert kaos_search.kaos_enabled()


def test_startup_warms_search_indices(folio):
    indices = folio._kaos_indices
    assert indices._labels.get(True) is not None, "label index not built at startup"
    assert indices._definitions is not None, "definition index not built at startup"


def test_warm_search_indices_never_raises():
    class Broken:
        def search_by_label(self, _query):
            raise RuntimeError("boom")

    class Collect(logging.Handler):
        def __init__(self):
            super().__init__()
            self.messages = []

        def emit(self, record):
            self.messages.append(record.getMessage())

    logger = logging.getLogger("tests.warmup")
    logger.setLevel(logging.INFO)
    handler = Collect()
    logger.addHandler(handler)
    try:
        assert warm_search_indices(Broken(), logger) >= 0
    finally:
        logger.removeHandler(handler)
    assert any("warm-up failed" in m for m in handler.messages), handler.messages


def test_definition_search_finds_divorce_concepts(client):
    response = client.get("/search/definition", params={"query": DIVORCE_QUERY})
    assert response.status_code == 200
    labels = _labels(response.json())[:5]
    assert any("divorce" in label.lower() or "family" in label.lower() for label in labels), labels


@pytest.mark.parametrize("path", ["/search/label", "/search/definition"])
def test_scores_are_0_to_100_best_first(client, path):
    response = client.get(path, params={"query": "contract law"})
    assert response.status_code == 200
    scores = [score for _cls, score in response.json()["results"]]
    assert scores, "no results"
    assert all(0 <= s <= 100 for s in scores), scores
    assert scores == sorted(scores, reverse=True)


def test_rapidfuzz_escape_hatch(client, monkeypatch):
    kaos = _labels(client.get("/search/definition", params={"query": DIVORCE_QUERY}).json())
    monkeypatch.setenv("FOLIO_SEARCH_BACKEND", "rapidfuzz")
    assert not kaos_search.kaos_enabled()
    legacy = client.get("/search/definition", params={"query": DIVORCE_QUERY})
    assert legacy.status_code == 200
    assert _labels(legacy.json()) != kaos
