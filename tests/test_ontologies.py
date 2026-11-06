"""Selection, instance-scoped resolution, and background loading contracts."""

import asyncio
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import copy
from unittest.mock import Mock

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from folio_api import api, ontologies
from folio_api.ontologies import (
    CANON_IRI_BASE, FOLIO_IRI_BASE, OntologyRegistry, get_ontology,
    parse_ontology_param, requested_ontology, resolve_class, resolve_property,
)
from tests.support import make_test_config


@pytest.mark.parametrize("value, expected", [
    (None, "folio"), ("", "folio"), ("folio", "folio"), ("FOLIO", "folio"),
    ("canon", "canon"), ("CANON", "canon"), ("bogus", None),
])
def test_parse_selector(value, expected):
    assert parse_ontology_param(value) == expected


def test_resolvers_keep_shared_bare_ids_in_the_selected_instance(_booted_app):
    registry = _booted_app.state.ontologies
    canon, folio = registry["canon"], registry["folio"]
    shared = next(cls for cls in canon.folio.classes
                  if cls.iri.startswith(CANON_IRI_BASE)
                  and resolve_class(folio, cls.iri.rsplit("/", 1)[-1]) is not None)
    bare = shared.iri.rsplit("/", 1)[-1]
    assert resolve_class(canon, bare) is shared
    assert resolve_class(folio, bare).iri == FOLIO_IRI_BASE + bare
    only_folio = next(cls for cls in folio.folio.classes
                      if resolve_class(canon, cls.iri.rsplit("/", 1)[-1]) is None)
    assert resolve_class(canon, only_folio.iri.rsplit("/", 1)[-1]) is None
    assert canon.contains(shared.iri)
    assert not folio.contains(shared.iri)


def test_property_resolution_and_membership(_booted_app):
    for key in ("folio", "canon"):
        entry = _booted_app.state.ontologies[key]
        prop = next(prop for prop in entry.folio.object_properties if prop.iri.startswith(entry.iri_base))
        assert resolve_property(entry, prop.iri) is prop
        assert resolve_property(entry, prop.iri.rsplit("/", 1)[-1]) is prop
        assert entry.contains(prop.iri)
        assert resolve_property(entry, "nonexistent-property-id") is None


def test_folio_resolvers_preserve_legacy_results(_booted_app):
    from folio_api.routes.properties import _find_property

    entry = _booted_app.state.ontologies["folio"]
    cls = entry.folio.classes[0]
    for value in (cls.iri, cls.iri.rsplit("/", 1)[-1], "https://example.invalid/" + cls.iri.rsplit("/", 1)[-1], "missing"):
        found = entry.folio[value]
        if not found and value.startswith("http"):
            found = entry.folio[value.rstrip("/").split("/")[-1]]
        if not found and not value.startswith("http"):
            found = entry.folio[FOLIO_IRI_BASE + value]
        if not found:
            found = next((obj for obj in entry.folio.classes if obj.iri.endswith(value) or value.endswith(obj.iri)), None)
        assert resolve_class(entry, value) is found
    prop = entry.folio.object_properties[0]
    for value in (prop.iri, prop.iri.rsplit("/", 1)[-1], "missing"):
        assert resolve_property(entry, value) is _find_property(entry.folio, value)


@pytest.mark.parametrize("state, status, retry", [
    ("loading", 503, "5"), ("failed", 503, None), ("disabled", 503, None), ("ready", 200, None),
])
def test_selector_dependency_and_page_helper(_booted_app, state, status, retry):
    registry = OntologyRegistry(_booted_app.state.ontologies["folio"])
    registry.canon_state = state
    if state == "ready":
        registry.entries["canon"] = _booted_app.state.ontologies["canon"]
    app = FastAPI()
    app.state.ontologies = registry

    @app.get("/")
    def selected(entry=Depends(get_ontology)):
        return {"key": entry.key}

    client = TestClient(app)
    response = client.get("/?ontology=CANON")
    assert response.status_code == status
    assert response.headers.get("Retry-After") == retry
    assert client.get("/").json() == {"key": "folio"}
    assert client.get("/?ontology=bogus").status_code == 404
    request = Request({"type": "http", "app": app, "query_string": b"ontology=canon"})
    assert requested_ontology(request) == ("canon", state)


@contextmanager
def own_app(monkeypatch, folio, enabled=True):
    # Keep real application lifespans and routes; reuse the already parsed FOLIO.
    config = make_test_config()
    config["canon"] = {"enabled": enabled}
    from folio_mcp import server

    with monkeypatch.context() as patches:
        patches.setattr(api, "load_config", lambda: config)
        patches.setattr(api, "initialize_folio", lambda *args: folio)
        # FastMCP caches a single-use session manager. Preserve the registered
        # handlers/settings, but let this copy create its own transport manager.
        session_mcp = server.mcp
        mcp = copy(session_mcp)
        mcp._session_manager = None
        patches.setattr(server, "mcp", mcp)
        # The real lifespan replaces/clears this global; restore the session's
        # exact backend once the independent application has shut down.
        patches.setattr(server, "_shared_backend", server._shared_backend)
        app = api.get_app()
        assert mcp.session_manager is not session_mcp.session_manager
        yield app


def test_folio_serves_while_canon_load_is_blocked(monkeypatch, _booted_app, folio):
    gate, entered = threading.Event(), threading.Event()
    entry = _booted_app.state.ontologies["canon"]

    def held():
        entered.set()
        assert gate.wait(10)
        return entry

    monkeypatch.setattr(ontologies, "build_canon_entry", held)
    with own_app(monkeypatch, folio) as app:
        with TestClient(app) as client:
            try:
                assert entered.wait(5)
                assert app.state.ontologies.canon_state == "loading"
                assert app.state.ontologies.get("canon") is None
                assert client.get("/info/health").status_code == 200
            finally:
                gate.set()
            assert client.portal.call(app.state.ontologies.wait_until_settled) == "ready"


def test_canon_failure_logs_once_and_folio_serves(monkeypatch, folio):
    loader = Mock(side_effect=ValueError("broken Canon"))
    monkeypatch.setattr(ontologies, "build_canon_entry", loader)
    warning = Mock()
    monkeypatch.setattr(logging.getLogger("folio_api"), "warning", warning)
    with own_app(monkeypatch, folio) as app:
        with TestClient(app) as client:
            assert client.portal.call(app.state.ontologies.wait_until_settled) == "failed"
            assert app.state.ontologies.get("canon") is None
            assert client.get("/info/health").status_code == 200
            warning.assert_called_once()


def test_disabled_canon_never_calls_loader(monkeypatch, folio):
    loader = Mock()
    monkeypatch.setattr(ontologies, "build_canon_entry", loader)
    with own_app(monkeypatch, folio, enabled=False) as app:
        with TestClient(app) as client:
            assert client.portal.call(app.state.ontologies.wait_until_settled) == "disabled"
            assert app.state.ontologies.get("canon") is None
            assert client.get("/info/health").status_code == 200
        loader.assert_not_called()


@pytest.mark.asyncio
async def test_shutdown_during_load_cancels_without_publishing(monkeypatch, _booted_app, folio):
    gate, entered, finished = threading.Event(), threading.Event(), threading.Event()

    def held():
        entered.set()
        try:
            assert gate.wait(10)
            return _booted_app.state.ontologies["canon"]
        finally:
            finished.set()

    monkeypatch.setattr(ontologies, "build_canon_entry", held)
    with own_app(monkeypatch, folio) as app:
        try:
            async with app.router.lifespan_context(app):
                assert await asyncio.to_thread(entered.wait, 5)
                assert app.state.ontologies.canon_state == "loading"
            assert app.state.ontologies.get("canon") is None
        finally:
            gate.set()
            assert await asyncio.to_thread(finished.wait, 5)
        assert app.state.ontologies.get("canon") is None


@pytest.mark.asyncio
async def test_wait_helper_times_out_while_loading(_booted_app):
    registry = OntologyRegistry(_booted_app.state.ontologies["folio"])
    with pytest.raises(TimeoutError):
        await registry.wait_until_settled(timeout=0.01)


def test_canon_priority_does_not_leak_to_default_executor(monkeypatch, _booted_app):
    def priority():
        return os.getpriority(os.PRIO_PROCESS, threading.get_native_id())

    try:
        normal_priority = os.getpriority(os.PRIO_PROCESS, threading.main_thread().native_id)
        # Some platforms expose getpriority but do not accept native thread IDs.
        priority()
    except (AttributeError, OSError):
        pytest.skip("getpriority with native thread IDs is unsupported")

    # Exercise the real priority change and index construction with parsed data.
    canon = _booted_app.state.ontologies["canon"].folio
    monkeypatch.setattr(ontologies, "FOLIO", lambda **kwargs: canon)

    async def load_and_check():
        loop = asyncio.get_running_loop()
        # Force reuse so the old shared-executor implementation fails reliably.
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        try:
            before = await asyncio.to_thread(priority)
        except (AttributeError, OSError):
            pytest.skip("getpriority with native thread IDs is unsupported")
        assert before == normal_priority
        registry = OntologyRegistry(_booted_app.state.ontologies["folio"])
        await registry.load_canon()
        assert await registry.wait_until_settled() == "ready"
        assert registry["canon"].folio is canon
        assert await asyncio.to_thread(priority) == normal_priority

    asyncio.run(load_and_check())
