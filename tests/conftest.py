"""Shared pytest fixtures for folio-api tests.

Two fixtures:
  - `client`: a `TestClient(app)` instance that runs the FastAPI lifespan
    on entry, so `app.state.folio` and `app.state.property_children` are
    populated for every test that uses it. Function-scoped so each test
    gets a fresh client (the underlying app + ontology are session-scoped
    through Python module caching, so this is cheap).
  - `folio`: a session-scoped reference to `app.state.folio` (the in-memory
    ontology). Tests use this directly when they don't need an HTTP round
    trip.
"""

import pytest
from fastapi.testclient import TestClient

from folio_api.api import app


@pytest.fixture(scope="session")
def _booted_app():
    """Start the FastAPI app once per test session so the lifespan
    loads the FOLIO ontology and builds the property_children reverse
    index. Returns the live app instance.
    """
    # Using TestClient as a context manager triggers the lifespan
    # startup and shutdown events. We only need startup here, so we
    # enter the context and hold it open for the whole session.
    with TestClient(app) as _:
        yield app


@pytest.fixture
def client(_booted_app):
    """Function-scoped TestClient bound to the already-booted app."""
    return TestClient(_booted_app)


@pytest.fixture(scope="session")
def folio(_booted_app):
    """Real FOLIO ontology instance (loaded by the app's lifespan)."""
    return _booted_app.state.folio


@pytest.fixture(scope="session")
def property_children(_booted_app):
    """Reverse index `{parent_iri: [child_property, ...]}` built at startup."""
    return _booted_app.state.property_children
