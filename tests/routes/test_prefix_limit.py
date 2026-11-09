"""/search/prefix `limit`: an additive cap that keeps the ranked order."""

from pathlib import Path


def _iris(items):
    return [item["iri"] for item in items]


def test_limit_keeps_the_first_classes_and_properties(client):
    full = client.get("/search/prefix", params={"query": "co"}).json()
    assert len(full["classes"]) > 20 and full["properties"]
    capped = client.get("/search/prefix", params={"query": "co", "limit": 20}).json()
    assert _iris(capped["classes"]) == _iris(full["classes"])[:20]
    assert _iris(capped["properties"]) == _iris(full["properties"])[:20]
    assert capped["classes"] == full["classes"][:20]


def test_limit_above_match_count_returns_everything(client):
    full = client.get("/search/prefix", params={"query": "deontic"}).json()
    capped = client.get("/search/prefix", params={"query": "deontic", "limit": 10_000}).json()
    assert capped == full


def test_no_limit_is_unchanged_default(client):
    body = client.get("/search/prefix", params={"query": "co"}).json()
    assert len(body["classes"]) > 1000  # existing clients still get every match


def test_limit_must_be_positive(client):
    assert client.get("/search/prefix", params={"query": "co", "limit": 0}).status_code == 422


def test_typeahead_requests_a_limited_payload():
    source = (
        Path(__file__).parents[2] / "folio_api" / "static" / "js" / "typeahead_search.js"
    ).read_text(encoding="utf-8")
    assert "url: '/search/prefix?query=%QUERY&limit=' + SUGGESTION_LIMIT" in source
