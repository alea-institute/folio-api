"""
HTML rendering utilities for FOLIO API.

This package contains utilities for generating HTML representations of FOLIO
ontology classes and related data structures.
"""

from folio_api.rendering.html_formatter import (
    format_label,
    format_description,
    get_node_neighbors,
    format_property_label,
    format_property_description,
    get_property_neighbors,
    render_tailwind_html,
    strip_folio_prefix,
)

__all__ = [
    "format_label",
    "format_description",
    "get_node_neighbors",
    "format_property_label",
    "format_property_description",
    "get_property_neighbors",
    "render_tailwind_html",
    "strip_folio_prefix",
]
