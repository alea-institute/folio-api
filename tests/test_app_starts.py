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


def test_mcp_public_hosts_allowed_and_unlisted_host_rejected(started_client):
    """Public MCP initialization works while unlisted hosts remain blocked."""
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "t", "version": "0"},
        },
    }
    for headers_extra, expected_status in (
        ({"Host": "folio.openlegalstandard.org"}, 200),
        ({"Host": "soli.openlegalstandard.org"}, 200),
        ({"Host": "folio-api.dev.openlegalstandard.org"}, 200),
        ({"Host": "localhost"}, 200),
        ({"Host": "localhost:8000"}, 200),
        (
            {
                "Host": "folio.openlegalstandard.org",
                "Origin": "https://folio.openlegalstandard.org",
            },
            200,
        ),
        (
            {
                "Host": "folio.openlegalstandard.org",
                "Origin": "https://evil.example",
            },
            403,
        ),
        ({"Host": "evil.example"}, 421),
    ):
        response = started_client.post(
            "/mcp",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                **headers_extra,
            },
            json=body,
        )
        assert response.status_code == expected_status, (headers_extra, response.text)


def test_mcp_get_reaches_mcp_server_not_iri_route(started_client):
    """GET /mcp must be answered by the MCP transport, not the /{iri} catch-all.

    Streamable-HTTP clients open a GET SSE stream after initialize. When the
    root router's /{iri} route shadowed it, they got the IRI lookup's 404,
    which the MCP spec defines as "session expired", so clients looped or
    reported the server as down. Without a session ID the SDK answers 400.
    """
    response = started_client.get(
        "/mcp",
        headers={
            "Accept": "text/event-stream",
            "Host": "folio.openlegalstandard.org",
        },
    )
    assert response.status_code == 400, response.text
    assert "session" in response.text.lower(), response.text


def test_iri_route_still_serves_concepts_after_mcp_route(started_client):
    """Registering /mcp ahead of /{iri} must not break ordinary IRI lookups."""
    response = started_client.get("/RCIPwpgRpMs1eVz4vPid0pV")
    assert response.status_code == 200, response.text
    assert response.json()["label"] == "Contract Law"


def _mcp_post(client, body, session_id=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Host": "folio.openlegalstandard.org",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    return client.post("/mcp", headers=headers, json=body)


def _mcp_open_session(client):
    response = _mcp_post(
        client,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "0"},
            },
        },
    )
    assert response.status_code == 200, response.text
    session_id = response.headers["mcp-session-id"]
    _mcp_post(
        client,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        session_id,
    )
    return session_id


def test_mcp_sessions_keep_in_process_graph_after_a_session_ends(
    started_client, _booted_app
):
    """Every MCP session must use folio-api's in-process graph, not just the first.

    folio-mcp <= 0.4.2 cleared the injected backend whenever any session ended,
    so later sessions fell back to an APIBackend calling the public REST API:
    PROD's MCP server called itself through its own rate limiter (429s).
    """
    from folio_mcp import server as mcp_server

    first = _mcp_open_session(started_client)
    response = started_client.delete(
        "/mcp",
        headers={"mcp-session-id": first, "Host": "folio.openlegalstandard.org"},
    )
    assert response.status_code == 200, response.text

    second = _mcp_open_session(started_client)
    response = _mcp_post(
        started_client,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "search_concepts", "arguments": {"query": "contract"}},
        },
        second,
    )
    assert response.status_code == 200, response.text
    assert "Contract" in response.text, response.text[:300]

    backend = mcp_server._current_backend()
    assert backend.folio is _booted_app.state.folio, type(backend).__name__


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


def test_registry_wraps_existing_folio_objects(_booted_app, folio, property_children):
    from folio_mcp import server
    from folio_api.routes.taxonomy import ROOT_CLASS_IRI_IDS
    from folio_api.routes.properties import HIDDEN_ROOT_PROPERTY_IRIS

    entry = _booted_app.state.ontologies["folio"]
    assert entry.folio is folio
    assert entry.property_children is property_children
    assert server._shared_backend.folio is folio
    roots = sorted((folio[iri] for iri in ROOT_CLASS_IRI_IDS), key=lambda cls: (cls.label or "").lower())
    assert entry.root_class_iris == tuple(cls.iri for cls in roots)
    assert entry.hidden_root_property_iris == HIDDEN_ROOT_PROPERTY_IRIS


def test_canon_is_ready_with_all_seven_roots(_booted_app):
    from folio_api.ontologies import CANON_IRI_BASE, OWL_THING, resolve_class

    registry = _booted_app.state.ontologies
    assert registry.canon_state == "ready"
    entry = registry["canon"]
    assert len(entry.folio.classes) == 14_973
    assert [resolve_class(entry, iri).label for iri in entry.root_class_iris] == [
        "Actor", "Authority (Source and Scope)", "Document / Artifact", "Event",
        "Normative Concepts (e.g., Ethics, Morals, Laws)", "Operational Concepts", "Place",
    ]
    assert OWL_THING not in entry.root_class_iris
    assert all(iri.startswith(CANON_IRI_BASE) for iri in entry.root_class_iris)
    assert not entry.hidden_root_property_iris
    expected = {}
    for prop in entry.folio.object_properties:
        for parent in prop.sub_property_of:
            expected.setdefault(parent, []).append(prop)
    assert entry.property_children == expected


def test_mcp_sessions_have_an_idle_timeout(_booted_app):
    """Abandoned MCP sessions must not live forever.

    mcp 1.27 keeps stateful sessions until DELETE by default; clients that
    vanish without one leaked ~47 KiB each for the life of the process.
    """
    from folio_mcp.server import mcp as folio_mcp_server

    timeout = folio_mcp_server.session_manager.session_idle_timeout
    assert timeout == 1800, timeout
