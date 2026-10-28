"""Controlled inputs at collection; real API/MCP startup once per session."""

import pytest
from fastapi.testclient import TestClient

from tests.support import isolated_environment


def pytest_configure(config):
    """Fixtures run too late to protect application imports during collection."""
    isolation = isolated_environment()
    config._folio_test_environment = isolation.__enter__()
    config.add_cleanup(lambda: isolation.__exit__(None, None, None))


@pytest.fixture(scope="session", autouse=True)
def _test_environment(request):
    environment = request.config._folio_test_environment
    yield environment
    # The app fixture depends on this one, so its lifespan has already exited.
    # Report late attempts as a pytest teardown error, as well as at cleanup.
    environment.assert_clean()


@pytest.fixture(scope="session")
def _booted_app(_test_environment):
    """Start the FastAPI app once per test session so the lifespan
    loads the FOLIO ontology and builds the property_children reverse
    index. Returns the live app instance.
    """
    from folio_api.api import app

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
