"""Search payload contracts, selecting ontology IRIs at runtime."""

import re

import pytest

from folio_api.routes.properties import _get_root_properties, strip_folio_prefix
from folio_api.routes.taxonomy import ROOT_CLASS_IRI_IDS


def _search(client, kind="taxonomy", query="deontic"):
    response = client.get(f"/{kind}/tree/search", params={"query": query})
    assert response.status_code == 200, response.text
    return response.json()


def _curated_roots(folio):
    return {folio[key].iri for key in ROOT_CLASS_IRI_IDS if folio[key] is not None}


def _pick_class(folio, predicate):
    for cls in folio.classes:
        if cls.label and len(cls.label) >= 2 and predicate(cls):
            return cls
    pytest.skip("No class qualifies in the current ontology")


def test_pruned_parent_counts_hidden_children(client, folio):
    tree = _search(client)["tree"]
    for iri, node in tree["nodes"].items():
        full_children = set(folio[iri].parent_class_of)
        shown = set(node["children"])
        if shown and full_children - shown:
            assert node["child_count"] == len(folio[iri].parent_class_of)
            assert node["child_count"] - len(node["children"]) == len(full_children - shown)
            return
    pytest.skip("No pruned parent for deontic in the current ontology")


def test_leaf_hit_has_zero_child_count(client, folio):
    leaf = _pick_class(folio, lambda cls: not cls.parent_class_of and cls.sub_class_of)
    node = _search(client, query=leaf.label)["tree"]["nodes"][leaf.iri]
    assert node["is_match"] is True
    assert node["child_count"] == 0


def test_all_children_matching_has_no_hidden_children(client, folio):
    for parent in folio.classes:
        children = [folio[iri] for iri in parent.parent_class_of]
        if len(children) < 2 or any(child is None or not child.label for child in children):
            continue
        words = re.findall(r"\w{2,}", children[0].label.lower())
        query = next((word for word in words if all(word in child.label.lower() for child in children)), None)
        if query is None:
            continue
        tree = _search(client, query=query)["tree"]
        node = tree["nodes"][parent.iri]
        assert set(node["children"]) == {child.iri for child in children}
        assert all(tree["nodes"][child.iri]["is_match"] for child in children)
        assert node["child_count"] == len(node["children"])
        return
    pytest.skip("No parent whose children share a label substring")


def test_hidden_root_counts_cover_class_and_property_roots(client, folio):
    for kind, roots in (
        ("taxonomy", _curated_roots(folio)),
        ("properties", {prop.iri for prop in _get_root_properties(folio)}),
    ):
        tree = _search(client, kind)["tree"]
        if kind == "properties" and not tree:
            pytest.skip("No property matches for deontic in the current ontology")
        total = len(roots)
        assert tree["hidden_root_count"] + len(roots.intersection(tree["root_nodes"])) == total


def test_noncurated_top_level_hit_does_not_reduce_hidden_root_count(client, folio):
    roots = _curated_roots(folio)
    root = _pick_class(
        folio,
        lambda cls: cls.iri not in roots
        and all(parent.endswith("owl#Thing") for parent in cls.sub_class_of),
    )
    tree = _search(client, query=root.label)["tree"]
    assert root.iri in tree["root_nodes"]
    assert tree["nodes"][root.iri]["is_match"] is True
    assert tree["hidden_root_count"] == len(roots) - len(roots.intersection(tree["root_nodes"]))


def test_property_search_node_fields_match_classes(client, property_children):
    expected = {"id", "label", "preferred_label", "children", "is_match", "match_field", "child_count"}
    for kind in ("taxonomy", "properties"):
        tree = _search(client, kind)["tree"]
        if kind == "properties" and not tree:
            pytest.skip("No property matches for deontic in the current ontology")
        nodes = tree["nodes"]
        assert nodes
        for iri, node in nodes.items():
            assert set(node) == expected
            if kind == "properties":
                assert node["child_count"] == len(property_children.get(iri, []))


def test_property_tree_children_are_sorted_case_insensitively(client, folio, property_children):
    for parent_iri, children in property_children.items():
        if folio.get_property(parent_iri) and len(children) >= 3:
            response = client.get("/properties/tree/data", params={"node_id": parent_iri})
            assert response.status_code == 200, response.text
            nodes = response.json()
            assert {node["id"] for node in nodes} == {child.iri for child in children}
            labels = [node["text"].lower() for node in nodes]
            assert labels == sorted(labels)
            return
    pytest.skip("No property parent with several children")


def test_existing_match_fields_keep_their_contract(client, folio):
    for kind in ("taxonomy", "properties"):
        body = _search(client, kind)
        if kind == "properties" and not body["tree"]:
            pytest.skip("No property matches for deontic in the current ontology")
        assert body["matches"]
        for match in body["matches"]:
            node = body["tree"]["nodes"][match["iri"]]
            assert isinstance(node["children"], list)
            assert all(isinstance(iri, str) for iri in node["children"])
            assert node["is_match"] is True
            assert node["match_field"] in {"label", "alternative_labels", "preferred_label", "definition"}
            entity = folio[match["iri"]] if kind == "taxonomy" else folio.get_property(match["iri"])
            preferred = entity.preferred_label
            if kind == "properties":
                preferred = strip_folio_prefix(preferred) if preferred else None
            assert node["preferred_label"] == preferred
            assert node["preferred_label"] is None or isinstance(node["preferred_label"], str)


def test_short_and_empty_result_queries_keep_response_shape(client):
    for kind in ("taxonomy", "properties"):
        short = _search(client, kind, query="a")
        assert set(short) == {"matches", "tree"}
        if kind == "properties":
            assert short == {"matches": [], "tree": {}}
        else:
            assert isinstance(short["matches"], list)
            assert isinstance(short["tree"], dict)
        empty = _search(client, kind, query="zzzz-no-ontology-match-91f7c2")
        assert empty == {"matches": [], "tree": {}}
