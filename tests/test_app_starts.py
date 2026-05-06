"""Smoke test: confirms the FastAPI app boots, the FOLIO ontology loads
via the lifespan handler, and the property_children reverse index is
populated. Run via `uv run pytest tests/test_app_starts.py -x`.

These tests must pass before any other tests are added — they verify
the conftest.py fixtures actually do what the docstring claims.
"""


def test_app_boots(client):
    """The FastAPI app responds to /openapi.json after the lifespan runs."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert "openapi" in body, "OpenAPI schema missing 'openapi' key"
    assert "paths" in body and len(body["paths"]) > 0, "no routes registered"


def test_folio_loaded(folio):
    """folio fixture returns a populated FOLIO ontology."""
    assert folio is not None
    # FOLIO exposes classes via its `.classes` attribute (list-like).
    # Per folio-python API: at least one class must exist after load.
    assert hasattr(folio, "classes"), "FOLIO instance missing .classes"
    assert len(list(folio.classes)) > 0, "FOLIO loaded with zero classes"


def test_property_children_built(property_children):
    """The reverse index `{parent_iri: [child, ...]}` is populated."""
    assert isinstance(property_children, dict)
    # FOLIO ships with multiple properties that have children; the index
    # should have at least 1 key after startup. Strict-zero would mean the
    # api.py:89-93 build loop didn't run.
    assert len(property_children) > 0, (
        "property_children reverse index is empty — "
        "api.py lifespan did not build it"
    )
