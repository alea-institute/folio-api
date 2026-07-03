"""
Unified explore routes for the FOLIO API — combined class + property tree view.
"""

# imports
from pathlib import Path

# packages
from fastapi import APIRouter, Query, Request, status
from folio import FOLIO, OWLClass, OWLObjectProperty
from starlette.responses import JSONResponse, Response

# API router
router = APIRouter(prefix="/explore", tags=["explore"])

# ============================================================
# Entity Graph endpoint (Phase 1, milestone v1.1)
# See .planning/phases/01-entity-graph/01-RESEARCH.md for the full design.
# ============================================================

OWL_THING = "http://www.w3.org/2002/07/owl#Thing"
OWL_TOP_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#topObjectProperty"
_FOLIO_IRI_PREFIX = "https://folio.openlegalstandard.org/"


def _resolve_entity(folio: FOLIO, iri: str):
    """4-strategy IRI resolver — mirrors properties.py:_find_property and
    taxonomy.py:1190-1216. Returns (entity, type) tuple or (None, None).

    Strategies:
      1. Direct lookup as class, then as property.
      2. If iri starts with http: try the last URL segment as both.
      3. If iri is segment-only: try with the FOLIO prefix prepended.
      (Suffix-match fallback is omitted — strategies 1-3 cover every observed
       user link form; suffix-match in properties.py is a legacy fallback for
       malformed inputs we don't need to support here.)
    """
    cls = folio[iri]
    if cls:
        return cls, "class"
    prop = folio.get_property(iri)
    if prop:
        return prop, "property"
    if iri.startswith("http"):
        seg = iri.rstrip("/").split("/")[-1]
        cls = folio[seg]
        if cls:
            return cls, "class"
        prop = folio.get_property(seg)
        if prop:
            return prop, "property"
    else:
        full = f"{_FOLIO_IRI_PREFIX}{iri}"
        cls = folio[full]
        if cls:
            return cls, "class"
        prop = folio.get_property(full)
        if prop:
            return prop, "property"
    return None, None


def _walk_class_ancestors(folio: FOLIO, cls: OWLClass) -> list:
    """Root-first ancestor chain, EXCLUDING the cls itself, EXCLUDING owl:Thing."""
    chain: list = []
    current = cls
    visited = {current.iri}
    while current and getattr(current, "sub_class_of", None):
        parent_iri = current.sub_class_of[0]  # single-inheritance per donor pattern
        if parent_iri == OWL_THING or parent_iri in visited:
            break
        parent = folio[parent_iri]
        if not parent:
            break
        chain.insert(0, parent)
        visited.add(parent_iri)
        current = parent
    return chain


def _walk_property_ancestors(folio: FOLIO, prop: OWLObjectProperty) -> list:
    """Root-first property chain, EXCLUDING the prop itself, EXCLUDING owl:topObjectProperty."""
    chain: list = []
    current = prop
    visited = {current.iri}
    while current and getattr(current, "sub_property_of", None):
        parent_iri = current.sub_property_of[0]
        if parent_iri == OWL_TOP_OBJECT_PROPERTY or parent_iri in visited:
            break
        parent = folio.get_property(parent_iri)
        if not parent:
            break
        chain.insert(0, parent)
        visited.add(parent_iri)
        current = parent
    return chain


def _children_of_class(cls: OWLClass, folio: FOLIO) -> list:
    """parent_class_of attribute on the class is the canonical child list.
    Defensively handles None."""
    iris = getattr(cls, "parent_class_of", None) or []
    return [folio[iri] for iri in iris if folio[iri]]


def _children_of_property(prop: OWLObjectProperty, property_children: dict) -> list:
    """Reverse index built at app startup (api.py:89-93). O(1) lookup."""
    return list(property_children.get(prop.iri, []))


def _child_count(entity, etype: str, folio: FOLIO, property_children: dict) -> int:
    if etype == "class":
        return len(_children_of_class(entity, folio))
    return len(_children_of_property(entity, property_children))


def _label_of(entity) -> str:
    return entity.label or "Unnamed"


# Multi-path entity graph walker — replaces the v1.1 linear ancestor chain.
# Walks ALL sub_class_of parents (multi-inheritance — 832 FOLIO classes have
# multiple parents), AND expands rdfs:seeAlso links by walking up from those
# targets too. This matches folio-mapper's and folio-enrich's graph view:
# users see related branches converge on the selected entity, not just one
# straight-line lineage.
_GRAPH_MAX_NODES = 50  # hard cap so a densely-linked entity can't blow up


def _walk_entity_graph(folio: FOLIO, entity, etype: str):
    """BFS upward via subClassOf (or subPropertyOf), expanding seeAlso along
    the way. Returns (nodes_dict_by_iri, edges_list).

    Each edge: {source, target, relationship: "subClassOf" | "seeAlso"}.
    Caps at _GRAPH_MAX_NODES; edges whose endpoints didn't make the cut are
    filtered out so the rendered graph is always self-consistent.
    """
    if etype == "class":
        get = lambda iri: folio[iri]
        parent_attr = "sub_class_of"
        terminator = OWL_THING
    else:
        get = folio.get_property
        parent_attr = "sub_property_of"
        terminator = OWL_TOP_OBJECT_PROPERTY

    nodes = {entity.iri: entity}
    edges = []
    queue = [entity]
    seen_edges = set()  # dedupe (src, tgt, rel) triples

    while queue and len(nodes) < _GRAPH_MAX_NODES:
        current = queue.pop(0)
        # Walk all parents (multi-inheritance per folio-mapper image)
        for parent_iri in (getattr(current, parent_attr, None) or []):
            if parent_iri == terminator:
                continue
            key = (parent_iri, current.iri, "subClassOf")
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append({
                "source": parent_iri,
                "target": current.iri,
                "relationship": "subClassOf",
            })
            if parent_iri not in nodes and len(nodes) < _GRAPH_MAX_NODES:
                parent = get(parent_iri)
                if parent:
                    nodes[parent_iri] = parent
                    queue.append(parent)
        # rdfs:seeAlso (classes only — OWL object properties don't carry it)
        if etype == "class":
            for related_iri in (getattr(current, "see_also", None) or []):
                key = (current.iri, related_iri, "seeAlso")
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges.append({
                    "source": current.iri,
                    "target": related_iri,
                    "relationship": "seeAlso",
                })
                if related_iri not in nodes and len(nodes) < _GRAPH_MAX_NODES:
                    related = get(related_iri)
                    if related:
                        nodes[related_iri] = related
                        queue.append(related)

    # Drop edges whose endpoints were dropped due to the node cap.
    in_set = set(nodes.keys())
    edges = [e for e in edges if e["source"] in in_set and e["target"] in in_set]
    return nodes, edges


def _is_folio_root(node, etype: str) -> bool:
    """True if this node is at the top of the FOLIO hierarchy — its only
    parents are owl:Thing / owl:topObjectProperty (i.e., no FOLIO parent)."""
    if etype == "class":
        parents = getattr(node, "sub_class_of", None) or []
        terminator = OWL_THING
    else:
        parents = getattr(node, "sub_property_of", None) or []
        terminator = OWL_TOP_OBJECT_PROPERTY
    real_parents = [p for p in parents if p != terminator]
    return len(real_parents) == 0


def _build_ancestors_payload(folio, entity, etype, property_children):
    """Returns the legacy single-parent chain (`ancestors[]`) AND the new
    multi-path graph (`nodes[]` + `edges[]`). Frontend prefers nodes/edges
    if present; older clients fall back to ancestors. Tests for both shapes."""
    # Legacy single-parent chain (kept for backward compat — existing tests
    # and any client code that hasn't migrated).
    if etype == "class":
        chain = _walk_class_ancestors(folio, entity)
    else:
        chain = _walk_property_ancestors(folio, entity)

    # New multi-path graph (subClassOf + seeAlso, BFS up).
    nodes_dict, edges = _walk_entity_graph(folio, entity, etype)

    return {
        "selected": {
            "iri": entity.iri,
            "label": _label_of(entity),
            "type": etype,
            "child_count": _child_count(entity, etype, folio, property_children),
        },
        # Legacy linear chain — first item is the topmost ancestor (D-21
        # ultimate marker). This still exists so tests asserting the old
        # shape keep passing and old cached frontends keep working.
        "ancestors": [
            {
                "iri": a.iri,
                "label": _label_of(a),
                "type": etype,
                "branch_root_type": ("ultimate" if i == 0 else None),
            }
            for i, a in enumerate(chain)
        ],
        # New richer graph. Nodes carry branch_root_type="ultimate" iff the
        # node is a true FOLIO root (no parents except owl:Thing). Multiple
        # ultimate roots are possible when seeAlso pulls in cross-branch
        # ancestry. The selected entity itself is NEVER marked ultimate.
        "nodes": [
            {
                "iri": iri,
                "label": _label_of(n),
                "type": etype,
                "branch_root_type": (
                    "ultimate"
                    if iri != entity.iri and _is_folio_root(n, etype)
                    else None
                ),
            }
            for iri, n in nodes_dict.items()
        ],
        "edges": edges,
    }


def _build_children_payload(folio, entity, etype, property_children):
    if etype == "class":
        kids = _children_of_class(entity, folio)
    else:
        kids = _children_of_property(entity, property_children)
    return {
        "parent_iri": entity.iri,
        "children": [
            {
                "iri": c.iri,
                "label": _label_of(c),
                "type": etype,
                "child_count": _child_count(c, etype, folio, property_children),
            }
            for c in sorted(kids, key=lambda x: (x.label or x.iri).lower())
        ],
    }


@router.get(
    "/api/entity-graph/{iri:path}",
    response_model=None,
    summary="Get Ancestor-Rooted Entity Graph",
    description=(
        "Returns the selected entity plus its ancestor chain (mode=ancestors, "
        "default) or its direct children (mode=children) for the entity-graph "
        "visualization on /explore/tree. The path parameter accepts either a "
        "full FOLIO IRI or its last URL segment."
    ),
    status_code=status.HTTP_200_OK,
)
async def get_entity_graph(
    request: Request,
    iri: str,
    mode: str = Query("ancestors", regex="^(ancestors|children)$"),
) -> JSONResponse:
    folio: FOLIO = request.app.state.folio
    property_children = getattr(request.app.state, "property_children", {})
    entity, etype = _resolve_entity(folio, iri)
    if entity is None:
        return JSONResponse(
            content={"error": f"Entity not found: {iri}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if mode == "ancestors":
        return JSONResponse(
            content=_build_ancestors_payload(folio, entity, etype, property_children)
        )
    return JSONResponse(
        content=_build_children_payload(folio, entity, etype, property_children)
    )


@router.get(
    "/tree",
    tags=["explore"],
    response_model=None,
    summary="Unified Ontology Explorer",
    description="Explore both FOLIO classes and properties in a single interactive tree view",
    include_in_schema=False,
)
async def explore_tree(request: Request) -> Response:
    """Unified tree explorer combining classes (nouns) and properties (verbs)."""
    typeahead_js_path = Path(__file__).parent.parent / "static" / "js" / "typeahead_search.js"
    typeahead_js_source = typeahead_js_path.read_text(encoding="utf-8")

    return request.app.state.templates.TemplateResponse(
        "explore/tree.html",
        {
            "request": request,
            "typeahead_js_source": typeahead_js_source,
            "config": request.app.state.config,
        },
    )
