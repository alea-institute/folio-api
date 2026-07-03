"""Unit tests for GET /explore/api/entity-graph/{iri:path}.

Tests use the session-scoped `folio` and `property_children` fixtures from
tests/conftest.py (Plan 01) and the function-scoped `client` fixture.

IRI selection strategy: rather than hard-code IRIs (FOLIO is a living
ontology), each test picks a runtime-stable target — e.g. "the first class
whose chain has depth >= 2", "the first property with at least one child" —
so the suite remains green across ontology updates.
"""

from urllib.parse import quote

import pytest

OWL_THING = "http://www.w3.org/2002/07/owl#Thing"
OWL_TOP_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#topObjectProperty"


# ---------- helpers ----------


def _pick_class_with_ancestors(folio, min_depth: int = 2):
    """Return an OWLClass whose ancestor chain length is >= min_depth.

    Walks sub_class_of upward stopping at owl:Thing or None.
    """
    for cls in folio.classes:
        depth = 0
        cur = cls
        visited = {cur.iri} if getattr(cur, "iri", None) else set()
        while cur and getattr(cur, "sub_class_of", None):
            pid = cur.sub_class_of[0]
            if pid == OWL_THING or pid in visited:
                break
            visited.add(pid)
            cur = folio[pid]
            if not cur:
                break
            depth += 1
            if depth >= min_depth:
                return cls
    pytest.skip(f"No class with ancestor depth >= {min_depth} in FOLIO ontology")


def _pick_property_with_ancestors(folio, min_depth: int = 1):
    for prop in folio.object_properties:
        depth = 0
        cur = prop
        visited = {cur.iri} if getattr(cur, "iri", None) else set()
        while cur and getattr(cur, "sub_property_of", None):
            pid = cur.sub_property_of[0]
            if pid == OWL_TOP_OBJECT_PROPERTY or pid in visited:
                break
            visited.add(pid)
            cur = folio.get_property(pid)
            if not cur:
                break
            depth += 1
            if depth >= min_depth:
                return prop
    pytest.skip(f"No property with ancestor depth >= {min_depth}")


def _pick_class_with_children(folio, min_children: int = 1):
    for cls in folio.classes:
        kids = getattr(cls, "parent_class_of", None) or []
        if len(kids) >= min_children:
            return cls
    pytest.skip(f"No class with >= {min_children} children")


def _last_segment(iri: str) -> str:
    return iri.rstrip("/").split("/")[-1]


# ---------- 1. happy path: class ----------


def test_returns_class_ancestors(client, folio):
    """GRAPH-10 + GRAPH-07: full-IRI request returns selected + ancestors[]."""
    cls = _pick_class_with_ancestors(folio, min_depth=2)
    url = f"/explore/api/entity-graph/{quote(cls.iri, safe='')}"
    resp = client.get(url)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "selected" in body
    assert body["selected"]["iri"] == cls.iri
    assert body["selected"]["type"] == "class"
    assert isinstance(body["selected"].get("label"), str)
    assert "ancestors" in body
    assert isinstance(body["ancestors"], list)
    assert len(body["ancestors"]) >= 2


# ---------- 2. IRI resolution strategies ----------


def test_iri_resolution_strategies(client, folio):
    """GRAPH-10: endpoint resolves full IRI, last-segment, and prefix-prepend forms."""
    cls = _pick_class_with_ancestors(folio, min_depth=1)
    seg = _last_segment(cls.iri)

    # Strategy 1: full IRI (URL-encoded)
    r1 = client.get(f"/explore/api/entity-graph/{quote(cls.iri, safe='')}")
    assert r1.status_code == 200, f"full IRI failed: {r1.text}"

    # Strategy 2: last segment alone
    r2 = client.get(f"/explore/api/entity-graph/{seg}")
    assert r2.status_code == 200, f"segment-only failed: {r2.text}"

    # Both must resolve to the same entity
    assert r1.json()["selected"]["iri"] == r2.json()["selected"]["iri"]


# ---------- 3. happy path: property ----------


def test_returns_property_ancestors(client, folio):
    """GRAPH-10 + GRAPH-07: properties traverse sub_property_of."""
    prop = _pick_property_with_ancestors(folio, min_depth=1)
    url = f"/explore/api/entity-graph/{quote(prop.iri, safe='')}"
    resp = client.get(url)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["selected"]["type"] == "property"
    assert body["selected"]["iri"] == prop.iri
    assert len(body["ancestors"]) >= 1


# ---------- 4. error path: unknown IRI ----------


def test_unknown_iri_returns_404(client):
    """GRAPH-10: bogus IRI returns 404 with JSON error body."""
    resp = client.get("/explore/api/entity-graph/this-iri-does-not-exist-xyz")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert "this-iri-does-not-exist-xyz" in body["error"]


# ---------- 5. children mode ----------


def test_children_mode(client, folio):
    """GRAPH-10 + GRAPH-09b: ?mode=children returns parent_iri + children[]
    with child_count on each child."""
    parent = _pick_class_with_children(folio, min_children=1)
    url = f"/explore/api/entity-graph/{quote(parent.iri, safe='')}?mode=children"
    resp = client.get(url)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["parent_iri"] == parent.iri
    assert "children" in body
    assert isinstance(body["children"], list)
    assert len(body["children"]) >= 1
    for c in body["children"]:
        assert "iri" in c
        assert "label" in c
        assert "type" in c
        assert c["type"] == "class"
        assert "child_count" in c
        assert isinstance(c["child_count"], int)
        assert c["child_count"] >= 0


# ---------- 6. root marker (branch_root_type) ----------


def test_root_marker(client, folio):
    """GRAPH-07 + D-21: topmost ancestor has branch_root_type=='ultimate';
    intermediate ancestors have null/missing or non-ultimate marker."""
    cls = _pick_class_with_ancestors(folio, min_depth=2)
    resp = client.get(f"/explore/api/entity-graph/{quote(cls.iri, safe='')}")
    body = resp.json()
    ancestors = body["ancestors"]
    assert ancestors[0]["branch_root_type"] == "ultimate"
    for inner in ancestors[1:]:
        assert inner.get("branch_root_type") in (None, "")


# ---------- 7. owl:Thing exclusion ----------


def test_owl_thing_excluded(client, folio):
    """GRAPH-07: owl:Thing must never appear in a class ancestor chain."""
    cls = _pick_class_with_ancestors(folio, min_depth=1)
    resp = client.get(f"/explore/api/entity-graph/{quote(cls.iri, safe='')}")
    body = resp.json()
    all_iris = [a["iri"] for a in body["ancestors"]] + [body["selected"]["iri"]]
    assert OWL_THING not in all_iris


# ---------- 8. owl:topObjectProperty exclusion ----------


def test_owl_top_obj_prop_excluded(client, folio):
    """GRAPH-07: owl:topObjectProperty must never appear in a property ancestor chain."""
    prop = _pick_property_with_ancestors(folio, min_depth=1)
    resp = client.get(f"/explore/api/entity-graph/{quote(prop.iri, safe='')}")
    body = resp.json()
    all_iris = [a["iri"] for a in body["ancestors"]] + [body["selected"]["iri"]]
    assert OWL_TOP_OBJECT_PROPERTY not in all_iris


# ---------- 9. selected.child_count ----------


def test_selected_has_child_count(client, folio):
    """GRAPH-09: selected node payload includes child_count (int >= 0)."""
    cls = _pick_class_with_children(folio, min_children=1)
    resp = client.get(f"/explore/api/entity-graph/{quote(cls.iri, safe='')}")
    body = resp.json()
    assert "child_count" in body["selected"]
    assert isinstance(body["selected"]["child_count"], int)
    assert body["selected"]["child_count"] >= 1  # we picked one with >= 1 child


# ---------- 10. invalid mode ----------


def test_invalid_mode_rejected(client, folio):
    """GRAPH-10 + Threat T-1-02: ?mode=foobar returns 422 (FastAPI Query regex)."""
    cls = _pick_class_with_ancestors(folio, min_depth=1)
    resp = client.get(f"/explore/api/entity-graph/{quote(cls.iri, safe='')}?mode=foobar")
    assert resp.status_code == 422
