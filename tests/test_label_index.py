"""The precomputed label index must reproduce the routes' former inline scans exactly."""

import random
import time

import pytest

from folio_api.label_index import field_matches, get_label_index


def _reference_classes(folio, query, exclude):
    """The loop formerly inlined in /search/prefix and /taxonomy/tree/search."""
    seen = set(exclude)
    out = []
    query_lower, query_title = query.lower(), query.title()
    for owl_class in folio.classes:
        if owl_class.iri in seen or not owl_class.label:
            continue
        if field_matches(owl_class, query, query_lower, query_title):
            seen.add(owl_class.iri)
            out.append(owl_class)
    return out


def _reference_properties(folio, query):
    query_lower, query_title = query.lower(), query.title()
    return [
        prop
        for prop in folio.object_properties
        if field_matches(prop, query, query_lower, query_title)
    ]


def _queries(folio):
    rng = random.Random(20261109)
    labels = [
        text
        for cls in folio.classes
        for text in [cls.label, cls.preferred_label, *(cls.alternative_labels or [])]
        if text and len(text) >= 3
    ]
    queries = [
        "la", "co", "Contract", "contract law", "CONTRACT", "tax", "Ab", "eU",
        "of the", " ", "zzzqqq", "ς", "Σ", "ΟΣ", "İ", "straße", "STRASSE",
        "a\x00b", "\x00",
    ]
    for text in rng.sample(labels, 150):
        start = rng.randrange(len(text) - 1)
        piece = text[start : start + rng.randint(2, 8)]
        queries += [piece, piece.upper(), piece.lower(), piece.title(), piece.swapcase()]
    return queries


def test_class_matches_equal_reference(folio):
    index = get_label_index(folio)
    for query in _queries(folio):
        exclude = {cls.iri for cls in folio.search_by_prefix(query)} if len(query) > 1 else set()
        before = set(exclude)
        got = index.classes.matches(query, exclude=exclude)
        assert exclude == before, "exclude must not be mutated"
        want = _reference_classes(folio, query, exclude)
        assert [c.iri for c in got] == [c.iri for c in want], repr(query)


def test_property_matches_equal_reference(folio):
    index = get_label_index(folio)
    for query in _queries(folio):
        got = index.properties.matches(query)
        assert [p.iri for p in got] == [p.iri for p in _reference_properties(folio, query)], repr(query)


def test_index_is_cached_per_instance(folio):
    assert get_label_index(folio) is get_label_index(folio)


def test_short_query_scan_is_fast(folio):
    """Guard against reintroducing a per-request lower()-everything scan."""
    index = get_label_index(folio)
    started = time.perf_counter()
    for _ in range(10):
        index.classes.matches("la", exclude=set())
    per_call = (time.perf_counter() - started) / 10
    assert per_call < 0.05, f"{per_call * 1000:.1f} ms per scan"


@pytest.mark.parametrize("query", ["la", "contract"])
def test_tree_search_marks_exactly_the_matches(client, query):
    body = client.get("/taxonomy/tree/search", params={"query": query}).json()
    match_iris = {m["iri"] for m in body["matches"]}
    assert match_iris
    nodes = body["tree"]["nodes"]
    assert {iri for iri, node in nodes.items() if node["is_match"]} == match_iris
    for iri, node in nodes.items():
        assert (node["match_field"] is None) == (iri not in match_iris)


def test_context_sensitive_lowering_matches_reference():
    """Greek final sigma lowers differently in a query than mid-label; the raw check must remain."""
    from types import SimpleNamespace

    from folio_api.label_index import _Haystacks

    def entity(iri, label, alts=(), pref=None):
        return SimpleNamespace(iri=iri, label=label, alternative_labels=list(alts), preferred_label=pref)

    entities = [
        entity("a", "ΟΣΑ"),
        entity("b", "x", alts=["ΚΟΣΜΟΣ"]),
        entity("c", "Plain", pref="Straße"),
        entity("d", "ab", alts=["cd"]),  # "b\x00c" must not match across fields
    ]
    haystacks = _Haystacks(entities)
    for query in ["ΟΣ", "ος", "Σ", "ΚΟΣ", "straße", "STRASSE", "b\x00c", "Ab", "x"]:
        want = [
            e.iri for e in entities
            if field_matches(e, query, query.lower(), query.title())
        ]
        assert [e.iri for e in haystacks.matches(query)] == want, repr(query)
