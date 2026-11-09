"""Precomputed label haystacks for the substring scans in the search routes.

``/search/prefix`` and ``/taxonomy/tree/search`` both scan every class (and
``/search/prefix`` every property) for a case-insensitive substring match in
its label, alternative labels and preferred label. Done naively that is
~60k ``str.lower()`` calls per request on the event loop (~20 ms locally,
~100 ms on the production t4g). This module lowers each label once per
ontology instance and joins the fields, so a request costs one to three
``in`` checks per entity.

Matching is exactly the routes' original predicate, evaluated per field::

    query in field or query.lower() in field.lower() or query.title() in field

Fields are joined with ``\\x00`` (and lowered *before* joining, so
context-sensitive lowering such as Greek final sigma is unchanged). A query
containing ``\\x00`` could match across field boundaries, so those fall back
to the per-field check.
"""

from __future__ import annotations

import threading
import weakref
from dataclasses import dataclass
from typing import Generic, Iterable, Optional, TypeVar

from folio import FOLIO

T = TypeVar("T")
_SEP = "\x00"


def _fields(entity) -> list[str]:
    fields = []
    if entity.label:
        fields.append(entity.label)
    for alt in entity.alternative_labels or ():
        if alt:
            fields.append(alt)
    if entity.preferred_label:
        fields.append(entity.preferred_label)
    return fields


def field_matches(entity, query: str, query_lower: str, query_title: str) -> bool:
    """The routes' original per-field predicate (reference implementation)."""
    for field in _fields(entity):
        if query in field or query_lower in field.lower() or query_title in field:
            return True
    return False


@dataclass(frozen=True)
class _Entry(Generic[T]):
    entity: T
    raw: str
    lowered: str


class _Haystacks(Generic[T]):
    def __init__(self, entities: Iterable[T]):
        self.entries = []
        for entity in entities:
            fields = _fields(entity)
            self.entries.append(
                _Entry(
                    entity,
                    _SEP.join(fields),
                    _SEP.join(field.lower() for field in fields),
                )
            )

    def matches(self, query: str, exclude: Optional[set] = None) -> list[T]:
        """Entities whose label fields contain ``query`` (route semantics), in index order.

        With ``exclude`` (the routes' ``seen_iris``), IRIs already in it are
        skipped and each IRI is returned at most once, as the inline loops
        did by adding to ``seen_iris`` as they went. ``exclude`` itself is not
        modified.
        """
        query_lower = query.lower()
        seen = None if exclude is None else set(exclude)
        query_title = query.title()
        if _SEP in query or _SEP in query_lower or _SEP in query_title:
            hits = (
                e.entity
                for e in self.entries
                if field_matches(e.entity, query, query_lower, query_title)
            )
            return _dedupe(hits, seen)
        # A title-cased query identical to the raw one is the same check.
        check_title = query_title != query
        hits = (
            e.entity
            for e in self.entries
            if query_lower in e.lowered
            or query in e.raw
            or (check_title and query_title in e.raw)
        )
        return _dedupe(hits, seen)


def _dedupe(entities: Iterable[T], seen: Optional[set]) -> list[T]:
    if seen is None:
        return list(entities)
    out = []
    for entity in entities:
        if entity.iri not in seen:
            seen.add(entity.iri)
            out.append(entity)
    return out


class LabelIndex:
    """Per-FOLIO-instance haystacks for classes (labelled only) and properties."""

    def __init__(self, folio: FOLIO):
        self._classes_ref = folio.classes
        self._class_count = len(folio.classes)
        self._properties_ref = folio.object_properties
        self._property_count = len(folio.object_properties)
        # The routes skip unlabelled classes before checking any field.
        self.classes = _Haystacks(cls for cls in folio.classes if cls.label)
        self.properties = _Haystacks(folio.object_properties)

    def is_current(self, folio: FOLIO) -> bool:
        return (
            folio.classes is self._classes_ref
            and len(folio.classes) == self._class_count
            and folio.object_properties is self._properties_ref
            and len(folio.object_properties) == self._property_count
        )


_indexes: "weakref.WeakKeyDictionary[FOLIO, LabelIndex]" = weakref.WeakKeyDictionary()
_lock = threading.Lock()


def get_label_index(folio: FOLIO) -> LabelIndex:
    """Return the (lazily built, cached) index for this ontology instance.

    Rebuilt if the instance's class/property lists were replaced or resized
    (e.g. ``FOLIO.refresh()``).
    """
    index = _indexes.get(folio)
    if index is not None and index.is_current(folio):
        return index
    with _lock:
        index = _indexes.get(folio)
        if index is None or not index.is_current(folio):
            index = LabelIndex(folio)
            _indexes[folio] = index
        return index
