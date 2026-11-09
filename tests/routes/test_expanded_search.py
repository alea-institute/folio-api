"""GET /search/llm/expanded: LLM query expansion + rank fusion, with a fake LLM.

The isolated test environment rejects real providers and external HTTP, so the
LLM is a local object implementing the same ``json_async`` interface as
alea_llm_client models. Keep the request count under the default
``/search/llm/`` rate-limit tier (10/minute per client).
"""

import asyncio
from types import SimpleNamespace

import pytest

expansion = pytest.importorskip("folio.expansion")

ROUTE = "/search/llm/expanded"


class FakeLLM:
    def __init__(self, response=None, error=None, delay=0.0):
        self.response = response
        self.error = error
        self.delay = delay
        self.calls = []

    async def json_async(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(data=self.response, metadata={})


@pytest.fixture
def fresh_folio(folio, monkeypatch):
    """The shared FOLIO graph with a clean expansion cache and a restorable llm."""
    expansion.get_expander(folio).clear()
    monkeypatch.setattr(folio, "llm", None)
    monkeypatch.setattr(folio, "llm_kwargs", {})
    yield folio
    expansion.get_expander(folio).clear()


def _labels(payload):
    return [hit["owl_class"]["label"] for hit in payload["results"]]


def test_expanded_search_fuses_llm_expansions(client, fresh_folio, monkeypatch):
    llm = FakeLLM(
        {"expansions": ["Landlord-Tenant Claims", "Lessor", "lessor."]}
    )
    monkeypatch.setattr(fresh_folio, "llm", llm)
    monkeypatch.setattr(fresh_folio, "llm_kwargs", {"reasoning_effort": "low"})

    response = client.get(ROUTE, params={"query": "my landlord won't fix the heat", "limit": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "my landlord won't fix the heat"
    assert payload["expansions"] == ["Landlord-Tenant Claims", "Lessor"]
    assert payload["expansion_source"] == "llm"
    assert 0 < len(payload["results"]) <= 5
    scores = [hit["score"] for hit in payload["results"]]
    assert scores == sorted(scores, reverse=True)
    assert "Lessor" in _labels(payload)
    assert any("Lessor" in hit["matched_via"] for hit in payload["results"])
    for hit in payload["results"]:
        assert hit["owl_class"]["iri"]
        assert hit["matched_via"]
        assert set(hit["matched_via"]) <= {payload["query"], *payload["expansions"]}
    assert llm.calls[0][1]["reasoning_effort"] == "low"

    # repeat query (different case/spacing) is served from the expansion cache
    again = client.get(ROUTE, params={"query": "My landlord won't  fix the heat", "limit": 5})
    assert again.status_code == 200
    assert again.json()["expansion_source"] == "cache"
    assert len(llm.calls) == 1


@pytest.mark.parametrize(
    "llm",
    [
        None,
        FakeLLM(error=RuntimeError("provider down")),
        FakeLLM(response="not json at all"),
    ],
    ids=["disabled", "error", "garbage"],
)
def test_expanded_search_degrades_to_label_search(client, fresh_folio, monkeypatch, llm):
    monkeypatch.setattr(fresh_folio, "llm", llm)
    response = client.get(
        ROUTE, params={"query": "Landlord", "limit": 3, "include_definitions": "false"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["expansions"] == []
    assert payload["expansion_source"] == "none"
    plain = [owl_class.iri for owl_class, _ in fresh_folio.search_by_label("Landlord", limit=10)][:3]
    assert [hit["owl_class"]["iri"] for hit in payload["results"]] == plain


def test_expanded_search_times_out(client, fresh_folio, monkeypatch):
    from folio_api.routes import search

    monkeypatch.setattr(search, "EXPANDED_SEARCH_LLM_TIMEOUT", 0.05)
    monkeypatch.setattr(fresh_folio, "llm", FakeLLM({"expansions": ["Lessor"]}, delay=2.0))
    response = client.get(ROUTE, params={"query": "Landlord", "limit": 2})
    assert response.status_code == 200
    assert response.json()["expansion_source"] == "none"
    assert response.json()["results"]


def test_expanded_search_validates_input(client, fresh_folio):
    assert client.get(ROUTE, params={"query": " x "}).status_code == 400
    assert client.get(ROUTE, params={"query": "landlord", "limit": 0}).status_code == 422
    assert client.get(ROUTE, params={"query": "landlord", "max_expansions": 11}).status_code == 422
