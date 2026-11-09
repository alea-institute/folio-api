import asyncio
import hashlib
import logging
import os
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args
from urllib.parse import urlencode

from fastapi import HTTPException, Request
from folio import FOLIO, OWLClass, OWLObjectProperty
from folio.graph import DEFAULT_CACHE_DIR

from folio_api.label_index import get_label_index

CANON_SOURCE_URL = "https://raw.githubusercontent.com/CatholicOS/ontology-semantic-canon/main/sources/ontology-semantic-canon.owl"
CANON_IRI_BASE = "https://ontology.catholicos.catholic/"
FOLIO_IRI_BASE = "https://folio.openlegalstandard.org/"
OWL_THING = "http://www.w3.org/2002/07/owl#Thing"
OntologyKey = Literal["folio", "canon"]
CanonState = Literal["loading", "ready", "failed", "disabled"]


# Curated list of root-level class IRI IDs (direct subclasses of owl:Thing,
# excluding sandbox/draft classes not ready for public display).
ROOT_CLASS_IRI_IDS = [
    "R8CdMpOM0RmyrgCCvbpiLS0",  # Actor / Player
    "RSYBzf149Mi5KE0YtmpUmr",  # Area of Law
    "RCIwc6WJi6IT7xePURxsi4T",  # Asset Type
    "R8qItBwG2pRMFhUq1HQEMnb",  # Communication Modality
    "R767niCLQVC5zIcO5WDQMSl",  # Currency
    "R79aItNTJQwHgR002wuX3iC",  # Data Format
    "RDt4vQCYDfY0R9fZ5FNnTbj",  # Document / Artifact
    "R9kmGZf5FSmFdouXWQ1Nndm",  # Engagement Attributes
    "R73hoH1RXYjBTYiGfolpsAF",  # Event
    "RhBgnef56iLBXYfPqWQE41",  # Financial Concepts and Metrics
    "RBjHwNNG2ASVmasLFU42otk",  # Forums and Venues
    "RBQGborh1CfXanGZipDL0Qo",  # Governmental Body
    "R8f4qGdjxuiQary8OBpq8W9",  # Industry and Market
    "RDOvAHsvY8TKJ1O1orXPM9o",  # Language
    "RC1CZydjfH8oiM4W3rCkma3",  # Legal Authorities
    "R7L5eLIzH0CpOUE74uJvSjL",  # Legal Entity
    "R9B8sRCK209t5Y8LlU4f62a",  # Legal Use Cases
    "R9aSzp9cEiBCzObnP92jYFX",  # Location
    "R7ReDY2v13rer1U8AyOj55L",  # Matter Narrative
    "RlNFgB3TQfMzV26V4V7u4E",  # Objectives
    "RDK1QEdQg1T8B5HQqMK2pZN",  # Service
    "RB4cFSLB4xvycDlKv73dOg6",  # Standards Compatibility
    "Rx69EnEj3H3TpcgTfUSoYx",  # Status
    "R8EoZh39tWmXCkmP2Xzjl6E",  # System Identifiers
]

# Root properties to hide from the tree
HIDDEN_ROOT_PROPERTY_IRIS = {
    "https://folio.openlegalstandard.org/RBD1G5FjdaXj6UM26EWBxJc",  # utbms:activities
    "https://folio.openlegalstandard.org/RDc1B2GDj6ckfXBkRRSJXfH",  # TR:SALI
    "https://folio.openlegalstandard.org/RDNZZOyU2yb5Q9xbxIWXd62",  # ZZZ:DEPRECATED PROPERTIES
}


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
        cache_cleanup = "cache cleanup not attempted"
        try:
            # Let ASGI startup finish before submitting any heavy work.
            await asyncio.sleep(0)
            loop = asyncio.get_running_loop()
            future = loop.create_future()

            def deliver(entry, error):
                # Cancellation propagates to the future. Only the loop touches it.
                if future.done():
                    return
                if error is not None:
                    future.set_exception(error)
                else:
                    future.set_result(entry)

            def build():
                nonlocal cache_cleanup
                entry, error = None, None
                try:
                    entry = build_canon_entry()
                except Exception as exc:
                    error = exc
                    cache_cleanup = remove_canon_cache()
                try:
                    loop.call_soon_threadsafe(deliver, entry, error)
                except RuntimeError:
                    # Shutdown may have closed the loop while the build ran.
                    pass

            # Daemon workers do not participate in concurrent.futures' exit join.
            threading.Thread(target=build, name="canon-load", daemon=True).start()
            entry = await future
            self.entries["canon"] = entry
            self.canon_state = "ready"
        except Exception:
            logging.getLogger("folio_api").warning(
                "Canon unavailable; %s", cache_cleanup, exc_info=True
            )
            self.canon_state = "failed"
        self._settled.set()


def parse_ontology_param(value: str | None) -> OntologyKey | None:
    if not value:
        return "folio"
    key = value.lower()
    return key if key in get_args(OntologyKey) else None


def requested_ontology(request: Request) -> tuple[OntologyKey | None, CanonState]:
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
            503, canon_status_message(state),
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
    roots = [folio[iri] for iri in ROOT_CLASS_IRI_IDS if folio[iri] is not None]
    roots.sort(key=lambda cls: (cls.label or "").lower())
    return OntologyEntry(
        "folio", folio, FOLIO_IRI_BASE, tuple(cls.iri for cls in roots),
        frozenset(HIDDEN_ROOT_PROPERTY_IRIS), property_children,
    )


def canon_cache_path() -> Path:
    # Match folio.graph.FOLIO.load_cache/save_cache for source_type="http".
    digest = hashlib.blake2b(CANON_SOURCE_URL.encode()).hexdigest()
    return Path(DEFAULT_CACHE_DIR) / "http" / f"{digest}.owl"


def remove_canon_cache() -> str:
    path = canon_cache_path()
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return f"could not remove Canon cache {path}: {exc}"
    return f"removed Canon cache if present: {path}"


def build_canon_entry() -> OntologyEntry:
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
    children = build_property_children(canon)
    get_label_index(canon)  # warm the search index off the event loop
    return OntologyEntry(
        "canon", canon, CANON_IRI_BASE, tuple(cls.iri for cls in roots),
        frozenset(), children,
    )


def build_property_children(folio: FOLIO) -> dict[str, list[OWLObjectProperty]]:
    children = defaultdict(list)
    for prop in folio.object_properties:
        for parent_iri in prop.sub_property_of:
            children[parent_iri].append(prop)
    return dict(children)


def canon_status_message(state: CanonState) -> str | None:
    if state == "ready":
        return None
    return "Canon loading" if state == "loading" else "Canon unavailable"


def tree_redirect_url(request: Request, node_type: Literal["class", "property"]) -> str:
    target = "/explore/tree"
    node = request.query_params.get("node")
    params = {}
    if node:
        params.update(node=node, type=node_type)
    if "ontology" in request.query_params:
        params["ontology"] = request.query_params["ontology"]
    if params:
        target += "?" + urlencode(params)
    return target
