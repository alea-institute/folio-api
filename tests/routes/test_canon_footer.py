"""Ontology-specific footer content on the tree explorer."""

import re


def test_tree_footer_matches_selected_ontology(client):
    for query, canon in [("?ontology=canon", True), ("", False)]:
        response = client.get("/explore/tree" + query)
        assert response.status_code == 200
        footer = re.search(r"<footer\b[^>]*>(.*?)</footer>", response.text, re.S)[1]
        assert "ALEA Institute" in footer
        assert "API (MIT)" in footer
        if canon:
            assert "FOLIO" not in footer
            assert "Version:" not in footer
            assert "openlegalstandard.org" not in footer
            assert "CC-BY" not in footer
        else:
            assert "FOLIO is an open standard" in footer
