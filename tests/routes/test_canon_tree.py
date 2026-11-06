"""Tree routes select and resolve within one ontology, including shared IDs."""

from urllib.parse import parse_qs, quote, urlencode, urlsplit

import pytest

from folio_api.ontologies import CANON_IRI_BASE, FOLIO_IRI_BASE
from folio_api.routes.taxonomy import ROOT_CLASS_IRI_IDS


@pytest.fixture
def canon(_booted_app):
    registry = _booted_app.state.ontologies
    assert registry.canon_state == "ready"
    return registry["canon"]


def _get(client, url, **params):
    response = client.get(url, params=params)
    assert response.status_code == 200, response.text
    return response


def _entity_url(kind, endpoint, iri):
    return f"/{kind}/{endpoint}/{quote(iri, safe='')}"


def _assert_class_iris(iris, canon):
    assert iris
    for iri in iris:
        assert iri.startswith(CANON_IRI_BASE)
        assert iri in canon.folio.iri_to_index
        assert not iri.startswith(FOLIO_IRI_BASE)


def test_default_redirect_and_folio_roots(client, folio):
    for kind in ("taxonomy", "properties"):
        response = client.get(f"/{kind}/tree", follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == "/explore/tree"
    expected = sorted(
        [folio[key] for key in ROOT_CLASS_IRI_IDS if folio[key] is not None],
        key=lambda cls: (cls.label or "").lower(),
    )
    nodes = _get(client, "/taxonomy/tree/data").json()
    assert nodes == [
        {
            "id": cls.iri, "text": cls.label or "Unnamed Class",
            "children": bool(cls.parent_class_of),
            "data": {"iri": cls.iri,
                     "definition": cls.definition or "No definition available",
                     "type": "top_level"},
        }
        for cls in expected
    ]
    for selector in ("", "folio", "FOLIO"):
        assert _get(client, "/taxonomy/tree/data", ontology=selector).json() == nodes


@pytest.mark.parametrize("kind, entity_type", [("taxonomy", "class"), ("properties", "property")])
def test_redirect_preserves_encoded_node_and_ontology(client, canon, kind, entity_type):
    iri = canon.root_class_iris[0]
    response = client.get(f"/{kind}/tree", params={"node": iri, "ontology": "canon"},
                          follow_redirects=False)
    assert response.status_code == 301
    location = response.headers["location"]
    assert location == "/explore/tree?" + urlencode({"node": iri, "type": entity_type, "ontology": "canon"})
    assert parse_qs(urlsplit(location).query) == {
        "node": [iri], "type": [entity_type], "ontology": ["canon"],
    }
    response = client.get(f"/{kind}/tree?ontology=canon", follow_redirects=False)
    assert response.headers["location"] == "/explore/tree?ontology=canon"


def test_canon_roots_and_case_insensitive_selector(client, canon):
    nodes = _get(client, "/taxonomy/tree/data", ontology="canon").json()
    assert {node["text"] for node in nodes} == {
        "Actor", "Authority (Source and Scope)", "Document / Artifact", "Event",
        "Normative Concepts (e.g., Ethics, Morals, Laws)", "Operational Concepts", "Place",
    }
    assert len(nodes) == 7
    assert all(not node["text"].startswith("ZZZ") for node in nodes)
    _assert_class_iris([node["id"] for node in nodes], canon)
    assert _get(client, "/taxonomy/tree/data", ontology="CANON").json() == nodes


@pytest.mark.parametrize("endpoint", ["tree/node", "class-details", "tree/path"])
def test_shared_class_id_selects_requested_ontology(client, canon, folio, endpoint):
    shared = next(cls for cls in canon.folio.classes
                  if cls.iri.startswith(CANON_IRI_BASE)
                  and FOLIO_IRI_BASE + cls.iri.rsplit("/", 1)[-1] in folio.iri_to_index)
    bare = shared.iri.rsplit("/", 1)[-1]
    folio_class = folio[FOLIO_IRI_BASE + bare]
    for selector, expected in (({}, folio_class), ({"ontology": "canon"}, shared)):
        response = _get(client, _entity_url("taxonomy", endpoint, bare), **selector)
        if endpoint == "class-details":
            assert response.context["class_data"]["iri"] == expected.iri
        elif endpoint == "tree/path":
            assert response.json()["path"][-1]["iri"] == expected.iri
        else:
            assert response.json()["iri"] == expected.iri


@pytest.mark.parametrize("endpoint", ["tree/node", "class-details", "tree/path"])
def test_canon_full_iri_preserves_namespace_for_shared_class_id(client, canon, folio, endpoint):
    shared = next(cls for cls in canon.folio.classes
                  if cls.iri.startswith(CANON_IRI_BASE)
                  and FOLIO_IRI_BASE + cls.iri.rsplit("/", 1)[-1] in folio.iri_to_index)
    foreign_iri = FOLIO_IRI_BASE + shared.iri.rsplit("/", 1)[-1]
    response = client.get(_entity_url("taxonomy", endpoint, foreign_iri),
                          params={"ontology": "canon"})
    assert response.status_code == 404
    response = _get(client, _entity_url("taxonomy", endpoint, shared.iri), ontology="canon")
    if endpoint == "class-details":
        assert response.context["class_data"]["iri"] == shared.iri
    elif endpoint == "tree/path":
        assert response.json()["path"][-1]["iri"] == shared.iri
    else:
        assert response.json()["iri"] == shared.iri


@pytest.mark.parametrize("endpoint", ["tree/node", "class-details", "tree/path"])
def test_folio_only_class_is_not_found_in_canon(client, canon, folio, endpoint):
    canon_ids = {cls.iri.rsplit("/", 1)[-1] for cls in canon.folio.classes}
    cls = next(cls for cls in folio.classes if cls.iri.rsplit("/", 1)[-1] not in canon_ids)
    url = _entity_url("taxonomy", endpoint, cls.iri.rsplit("/", 1)[-1])
    assert client.get(url, params={"ontology": "canon"}).status_code == 404
    assert client.get(url).status_code == 200


def test_canon_class_search_and_hidden_root_count(client, canon):
    response = _get(client, "/taxonomy/tree/search", ontology="canon", query="Sacrament")
    body = response.json()
    _assert_class_iris([match["iri"] for match in body["matches"]], canon)
    _assert_class_iris(list(body["tree"]["nodes"]), canon)
    assert FOLIO_IRI_BASE not in response.text
    roots = set(canon.root_class_iris)
    assert body["tree"]["hidden_root_count"] == len(roots - set(body["tree"]["root_nodes"]))


def test_canon_class_children_path_and_details_stay_in_canon(client, canon):
    place = next(cls for cls in canon.folio.classes if cls.label == "Place")
    children_response = _get(client, "/taxonomy/tree/data", ontology="canon", node_id=place.iri)
    children = children_response.json()
    assert _get(client, "/taxonomy/tree/data", ontology="canon",
                node_id=place.iri.rsplit("/", 1)[-1]).json() == children
    _assert_class_iris([node["id"] for node in children], canon)
    child = children[0]["id"]
    path = _get(client, _entity_url("taxonomy", "tree/path", child), ontology="canon")
    _assert_class_iris([node["iri"] for node in path.json()["path"]], canon)
    assert path.json()["path"][-1]["iri"] == child
    for endpoint in ("tree/node", "class-details"):
        response = _get(client, _entity_url("taxonomy", endpoint, place.iri), ontology="canon")
        data = response.json() if endpoint == "tree/node" else response.context["class_data"]
        _assert_class_iris([data["iri"]] + [item["iri"] for item in data["parents"] + data["children"]], canon)
        _assert_class_iris([node["id"] for node in data["nodes"]], canon)
        assert FOLIO_IRI_BASE not in response.text


def test_canon_properties_include_external_namespaces(client, canon):
    roots = _get(client, "/properties/tree/data", ontology="canon").json()
    assert roots
    for node in roots:
        assert node["id"] in canon.folio.iri_to_property_index
    external = next(prop for prop in canon.folio.object_properties
                    if prop.iri.startswith(("http://purl.org/dc/", "http://www.w3.org/ns/prov#"))
                    and prop.label and len(prop.label) >= 2)
    assert external.iri in {node["id"] for node in roots}
    search = _get(client, "/properties/tree/search", ontology="canon", query=external.label).json()
    assert external.iri in {match["iri"] for match in search["matches"]}
    for iri in search["tree"]["nodes"]:
        assert iri in canon.folio.iri_to_property_index
    assert all(match["iri"] in canon.folio.iri_to_property_index for match in search["matches"])
    for endpoint in ("tree/node", "tree/path", "property-details"):
        response = _get(client, _entity_url("properties", endpoint, external.iri), ontology="canon")
        if endpoint == "tree/path":
            assert response.json()["path"][-1]["iri"] == external.iri
            assert all(item["iri"] in canon.folio.iri_to_property_index for item in response.json()["path"])
        elif endpoint == "property-details":
            assert response.context["prop_data"]["iri"] == external.iri
        else:
            assert response.json()["iri"] == external.iri
    parent_iri, expected = next((iri, children) for iri, children in canon.property_children.items()
                                if iri in canon.folio.iri_to_property_index and children)
    children = _get(client, "/properties/tree/data", ontology="canon", node_id=parent_iri).json()
    assert {node["id"] for node in children} == {prop.iri for prop in expected}
    assert all(node["id"] in canon.folio.iri_to_property_index for node in children)
    assert _get(client, "/properties/tree/data", ontology="CANON").json() == roots


@pytest.mark.parametrize("kind, endpoint", [
    ("taxonomy", "class-details"), ("properties", "property-details"),
])
@pytest.mark.parametrize("key", ["folio", "canon"])
def test_detail_context_has_selected_key_and_membership(client, _booted_app, kind, endpoint, key):
    entry = _booted_app.state.ontologies[key]
    entity = entry.folio.classes[0] if kind == "taxonomy" else entry.folio.object_properties[0]
    url = _entity_url(kind, endpoint, entity.iri)
    response = _get(client, url, **({"ontology": "canon"} if key == "canon" else {}))
    assert response.context["ontology_key"] == key
    contains = response.context["in_ontology"]
    assert contains.__self__ is entry
    assert contains(entity.iri)
    assert not contains("https://example.invalid/missing")
    missing = client.get(_entity_url(kind, endpoint, "missing-ontology-entity"), params={"ontology": key})
    assert missing.status_code == (404 if key == "canon" else 200)
    assert missing.context["ontology_key"] == key
    assert missing.context["in_ontology"].__self__ is entry


@pytest.mark.parametrize("kind", ["taxonomy", "properties"])
@pytest.mark.parametrize("endpoint", ["tree/data", "tree/search?query=Sacrament", "tree/node/missing", "tree/path/missing", "details"])
def test_unknown_selector_returns_not_found(client, kind, endpoint):
    if endpoint == "details":
        endpoint = "class-details/missing" if kind == "taxonomy" else "property-details/missing"
    separator = "&" if "?" in endpoint else "?"
    assert client.get(f"/{kind}/{endpoint}{separator}ontology=bogus").status_code == 404


def test_loading_canon_does_not_affect_folio(client, _booted_app, canon):
    registry = _booted_app.state.ontologies
    endpoints = ["/taxonomy/tree/data", "/properties/tree/data",
                 "/taxonomy/tree/search?query=Sacrament", "/properties/tree/search?query=has",
                 "/taxonomy/tree/node/missing", "/properties/tree/node/missing",
                 "/taxonomy/tree/path/missing", "/properties/tree/path/missing",
                 "/taxonomy/class-details/missing", "/properties/property-details/missing"]
    baseline = [(client.get(url).status_code, client.get(url).content) for url in endpoints]
    previous_state = registry.canon_state
    previous_entry = registry.entries.pop("canon")
    registry.canon_state = "loading"
    try:
        for url, (status, content) in zip(endpoints, baseline):
            separator = "&" if "?" in url else "?"
            response = client.get(url + separator + "ontology=canon")
            assert response.status_code == 503
            assert response.headers["Retry-After"] == "5"
            folio_response = client.get(url)
            assert folio_response.status_code == status
            assert folio_response.content == content
    finally:
        registry.entries["canon"] = previous_entry
        registry.canon_state = previous_state
