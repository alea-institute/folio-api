"""Ontology selection and an isolated, background Canon load."""

import asyncio
import logging
import os
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, Request
from folio import FOLIO, OWLClass, OWLObjectProperty

CANON_SOURCE_URL = "https://raw.githubusercontent.com/CatholicOS/ontology-semantic-canon/main/sources/ontology-semantic-canon.owl"
CANON_IRI_BASE = "https://ontology.catholicos.catholic/"
FOLIO_IRI_BASE = "https://folio.openlegalstandard.org/"
OWL_THING = "http://www.w3.org/2002/07/owl#Thing"
OntologyKey = Literal["folio", "canon"]
CanonState = Literal["loading", "ready", "failed", "disabled"]


@dataclass(frozen=True)
class OntologyEntry:
    key: OntologyKey
    folio: FOLIO
    iri_base: str
    root_class_iris: tuple[str, ...]
    hidden_root_property_iris: frozenset[str]
    property_children: dict[str, list[OWLObjectProperty]]

    def contains(self, iri: str) -> bool:
        return iri in self.folio.iri_to_index or iri in self.folio.iri_to_property_index


class OntologyRegistry:
    def __init__(self, folio: OntologyEntry, *, enabled: bool = True):
        self.entries = {"folio": folio}
        self.canon_state: CanonState = "loading" if enabled else "disabled"
        self._settled = asyncio.Event()
        if not enabled:
            self._settled.set()

    def __getitem__(self, key: str) -> OntologyEntry:
        return self.entries[key]

    def get(self, key: str) -> OntologyEntry | None:
        return self.entries.get(key)

    async def wait_until_settled(self, timeout: float = 30) -> CanonState:
        await asyncio.wait_for(self._settled.wait(), timeout)
        return self.canon_state

    async def load_canon(self) -> None:
        try:
            # Let ASGI startup finish before submitting any heavy work.
            await asyncio.sleep(0)
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="canon-load")
            try:
                entry = await asyncio.get_running_loop().run_in_executor(
                    executor, build_canon_entry
                )
            finally:
                # A running build cannot be interrupted. Retire its dedicated
                # thread without blocking ASGI shutdown or reusing its priority.
                executor.shutdown(wait=False, cancel_futures=True)
            self.entries["canon"] = entry
            self.canon_state = "ready"
        except Exception:
            logging.getLogger("folio_api").warning("Canon unavailable", exc_info=True)
            self.canon_state = "failed"
        self._settled.set()


def parse_ontology_param(value: str | None) -> OntologyKey | None:
    if not value:
        return "folio"
    key = value.lower()
    return key if key in ("folio", "canon") else None


def requested_ontology(request: Request) -> tuple[OntologyKey | None, CanonState]:
    """Page selection without raising for loading, unavailable, or invalid input."""
    return (
        parse_ontology_param(request.query_params.get("ontology")),
        request.app.state.ontologies.canon_state,
    )


def get_ontology(request: Request) -> OntologyEntry:
    key, state = requested_ontology(request)
    if key is None:
        raise HTTPException(404, "Unknown ontology")
    if key == "canon" and state != "ready":
        raise HTTPException(
            503, "Canon loading" if state == "loading" else "Canon unavailable",
            headers={"Retry-After": "5"} if state == "loading" else None,
        )
    return request.app.state.ontologies[key]


def _resolve(entry: OntologyEntry, value: str, *, property_: bool):
    ontology = entry.folio
    # Canon bare IDs must bypass the library's FOLIO normalization.
    index = ontology.iri_to_property_index if property_ else ontology.iri_to_index
    objects = ontology.object_properties if property_ else ontology.classes

    def lookup(iri):
        if entry.key == "folio":
            return ontology.get_property(iri) if property_ else ontology[iri]
        position = index.get(iri)
        return objects[position] if position is not None else None

    result = lookup(value)
    if result is not None:
        return result
    if entry.key == "folio" and value.startswith("http"):
        result = lookup(entry.iri_base + value.rstrip("/").split("/")[-1])
    if result is None and ("/" not in value or (entry.key == "folio" and not value.startswith("http"))):
        result = lookup(entry.iri_base + value)
    if result is not None:
        return result
    return next((obj for obj in objects if obj.iri.endswith(value) or value.endswith(obj.iri)), None)


def resolve_class(entry: OntologyEntry, iri_or_id: str) -> OWLClass | None:
    return _resolve(entry, iri_or_id, property_=False)


def resolve_property(entry: OntologyEntry, iri_or_id: str) -> OWLObjectProperty | None:
    return _resolve(entry, iri_or_id, property_=True)


def make_folio_entry(folio: FOLIO, property_children: dict) -> OntologyEntry:
    from folio_api.routes.taxonomy import ROOT_CLASS_IRI_IDS
    from folio_api.routes.properties import HIDDEN_ROOT_PROPERTY_IRIS

    roots = [folio[iri] for iri in ROOT_CLASS_IRI_IDS if folio[iri] is not None]
    roots.sort(key=lambda cls: (cls.label or "").lower())
    return OntologyEntry(
        "folio", folio, FOLIO_IRI_BASE, tuple(cls.iri for cls in roots),
        frozenset(HIDDEN_ROOT_PROPERTY_IRIS), property_children,
    )


def build_canon_entry() -> OntologyEntry:
    """Run acquisition, parsing, then indexes sequentially on a low-priority thread."""
    try:
        os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), 10)
    except (AttributeError, OSError):
        pass
    canon = FOLIO(source_type="http", http_url=CANON_SOURCE_URL, use_cache=True, llm=None)
    roots = [
        cls for cls in canon.classes
        if cls.iri != OWL_THING and not (cls.label or "").startswith("ZZZ")
        and (not cls.sub_class_of or all(parent == OWL_THING for parent in cls.sub_class_of))
    ]
    roots.sort(key=lambda cls: (cls.label or "").lower())
    children = defaultdict(list)
    for prop in canon.object_properties:
        for parent in prop.sub_property_of:
            children[parent].append(prop)
    return OntologyEntry(
        "canon", canon, CANON_IRI_BASE, tuple(cls.iri for cls in roots),
        frozenset(), dict(children),
    )
