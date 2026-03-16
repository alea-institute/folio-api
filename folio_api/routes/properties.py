"""
Property routes for the FOLIO API — browse, tree, and detail views for OWL Object Properties.
"""

# imports
from pathlib import Path

# packages
from fastapi import APIRouter, Request, status
from folio import FOLIO, OWLObjectProperty
from starlette.responses import Response, JSONResponse, RedirectResponse

# project
from folio_api.rendering import get_property_neighbors, strip_folio_prefix

# API router
router = APIRouter(prefix="/properties", tags=["properties"])

# The OWL top-level property IRI
OWL_TOP_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#topObjectProperty"

# Root properties to hide from the tree
HIDDEN_ROOT_PROPERTY_IRIS = {
    "https://folio.openlegalstandard.org/RBD1G5FjdaXj6UM26EWBxJc",  # utbms:activities
    "https://folio.openlegalstandard.org/RDc1B2GDj6ckfXBkRRSJXfH",  # TR:SALI
    "https://folio.openlegalstandard.org/RDNZZOyU2yb5Q9xbxIWXd62",  # ZZZ:DEPRECATED PROPERTIES
}


def _find_property(folio: FOLIO, iri: str) -> OWLObjectProperty | None:
    """4-step IRI resolution for properties (mirrors class resolution pattern)."""
    # Strategy 1: Direct lookup
    prop = folio.get_property(iri)
    if prop:
        return prop

    # Strategy 2: Full IRI → extract ID part
    if iri.startswith("http"):
        parts = iri.rstrip("/").split("/")
        if parts:
            prop = folio.get_property(parts[-1])
            if prop:
                return prop

    # Strategy 3: Short ID → prepend FOLIO prefix
    if not iri.startswith("http"):
        full_iri = f"https://folio.openlegalstandard.org/{iri}"
        prop = folio.get_property(full_iri)
        if prop:
            return prop

    # Strategy 4: Scan all properties for suffix match
    for p in folio.object_properties:
        if p.iri.endswith(iri) or iri.endswith(p.iri):
            return p

    return None


def _is_root_property(prop: OWLObjectProperty) -> bool:
    """Check if a property is a root (top-level) property."""
    if not prop.sub_property_of:
        return True
    if len(prop.sub_property_of) == 1 and prop.sub_property_of[0] == OWL_TOP_OBJECT_PROPERTY:
        return True
    return False


def _get_root_properties(folio: FOLIO) -> list[OWLObjectProperty]:
    """Get all root-level object properties."""
    roots = [p for p in folio.object_properties if _is_root_property(p) and p.iri not in HIDDEN_ROOT_PROPERTY_IRIS]
    roots.sort(key=lambda p: (p.label or p.iri).lower())
    return roots


def _is_in_hidden_branch(folio: FOLIO, prop: OWLObjectProperty) -> bool:
    """Check if a property is itself hidden or is a descendant of a hidden root."""
    if prop.iri in HIDDEN_ROOT_PROPERTY_IRIS:
        return True
    visited = set()
    current = prop
    while current and current.sub_property_of:
        for parent_iri in current.sub_property_of:
            if parent_iri == OWL_TOP_OBJECT_PROPERTY or parent_iri in visited:
                continue
            if parent_iri in HIDDEN_ROOT_PROPERTY_IRIS:
                return True
            visited.add(parent_iri)
            parent = folio.get_property(parent_iri)
            if parent:
                current = parent
                break
        else:
            break
    return False


def _get_child_properties(folio: FOLIO, parent_iri: str, property_children: dict = None) -> list[OWLObjectProperty]:
    """Get child properties of a given parent IRI."""
    if property_children is not None:
        children = property_children.get(parent_iri, [])
    else:
        children = [p for p in folio.object_properties if parent_iri in p.sub_property_of]
    return sorted(children, key=lambda p: (p.label or p.iri).lower())


@router.get(
    "/all",
    tags=["properties"],
    response_model=None,
    summary="Get All Object Properties",
    description="Retrieve all OWL object properties from the FOLIO ontology",
    status_code=status.HTTP_200_OK,
)
async def get_all_properties(request: Request) -> JSONResponse:
    """Get all OWL object properties defined in the FOLIO ontology.

    Returns a JSON object with a 'properties' array, each containing
    iri, label, definition, domain, range, inverse_of, and sub_property_of.
    """
    folio: FOLIO = request.app.state.folio
    props = folio.get_all_properties()
    result = []
    for prop in props:
        d = {"iri": prop.iri, "label": prop.label}
        if prop.definition:
            d["definition"] = prop.definition
        if prop.domain:
            d["domain"] = prop.domain
        if prop.range:
            d["range"] = prop.range
        if prop.inverse_of:
            d["inverse_of"] = prop.inverse_of
        if prop.sub_property_of:
            d["sub_property_of"] = prop.sub_property_of
        result.append(d)
    return JSONResponse(content={"properties": result})


@router.get(
    "/browse",
    tags=["properties"],
    response_model=None,
    summary="Browse Root Object Properties",
    description="Browse all root-level OWL object properties in a human-readable HTML format",
    status_code=status.HTTP_200_OK,
)
async def browse_properties(request: Request) -> Response:
    """Browse all root-level object properties from the FOLIO ontology."""
    folio: FOLIO = request.app.state.folio
    property_children = getattr(request.app.state, "property_children", None)

    root_properties = _get_root_properties(folio)

    # Count children for each root property
    root_data = []
    for prop in root_properties:
        children = _get_child_properties(folio, prop.iri, property_children)
        # Build domain/range summary
        domain_labels = []
        for d_iri in prop.domain:
            cls = folio[d_iri]
            if cls:
                domain_labels.append(cls.label or d_iri.split("/")[-1])
        range_labels = []
        for r_iri in prop.range:
            cls = folio[r_iri]
            if cls:
                range_labels.append(cls.label or r_iri.split("/")[-1])

        root_data.append({
            "prop": prop,
            "child_count": len(children),
            "domain_summary": ", ".join(domain_labels[:3]) + ("..." if len(domain_labels) > 3 else "") if domain_labels else "",
            "range_summary": ", ".join(range_labels[:3]) + ("..." if len(range_labels) > 3 else "") if range_labels else "",
        })

    typeahead_js_path = Path(__file__).parent.parent / "static" / "js" / "typeahead_search.js"
    typeahead_js_source = typeahead_js_path.read_text(encoding="utf-8")

    return request.app.state.templates.TemplateResponse(
        "properties/browse.html",
        {
            "request": request,
            "root_data": root_data,
            "typeahead_js_source": typeahead_js_source,
            "config": request.app.state.config,
        },
    )


@router.get(
    "/tree",
    tags=["properties"],
    response_model=None,
    summary="Interactive Property Tree Explorer",
    description="Explore FOLIO object properties using an interactive tree view",
    status_code=status.HTTP_200_OK,
)
async def explore_property_tree(request: Request) -> Response:
    """Redirect to the unified explore tree view."""
    target = "/explore/tree"
    node = request.query_params.get("node")
    if node:
        target += f"?node={node}&type=property"
    return RedirectResponse(url=target, status_code=301)


@router.get(
    "/tree/data",
    tags=["properties"],
    response_model=None,
    summary="Get Property Tree Data",
    description="Get hierarchical data for the property tree view",
    status_code=status.HTTP_200_OK,
)
async def get_property_tree_data(request: Request, node_id: str = "#") -> JSONResponse:
    """Get hierarchical data for the property tree (lazy-load compatible)."""
    folio: FOLIO = request.app.state.folio
    property_children = getattr(request.app.state, "property_children", None)

    # INTERIM: strip_folio_prefix calls below can be removed once FOLIO PR #5 is merged
    if node_id == "#":
        # Return root properties
        roots = _get_root_properties(folio)
        result = []
        for prop in roots:
            children = _get_child_properties(folio, prop.iri, property_children)
            result.append({
                "id": prop.iri,
                "text": strip_folio_prefix(prop.label or "Unnamed Property"),
                "children": len(children) > 0,
                "data": {
                    "iri": prop.iri,
                    "definition": prop.definition or "No definition available",
                    "type": "root_property",
                },
            })
        return JSONResponse(content=result)
    else:
        # Return children of a specific property
        children = _get_child_properties(folio, node_id, property_children)
        result = []
        for child in children:
            grandchildren = _get_child_properties(folio, child.iri, property_children)
            result.append({
                "id": child.iri,
                "text": strip_folio_prefix(child.label or "Unnamed Property"),
                "children": len(grandchildren) > 0,
                "data": {
                    "iri": child.iri,
                    "definition": child.definition or "No definition available",
                    "type": "sub_property",
                },
            })
        return JSONResponse(content=result)


@router.get(
    "/tree/node/{iri:path}",
    tags=["properties"],
    response_model=None,
    summary="Get Single Property Node Data",
    description="Get detailed data for a single property node",
    status_code=status.HTTP_200_OK,
)
async def get_property_node_data(request: Request, iri: str) -> JSONResponse:
    """Get detailed data for a single property node by IRI."""
    folio: FOLIO = request.app.state.folio
    property_children = getattr(request.app.state, "property_children", None)

    prop = _find_property(folio, iri)
    if not prop:
        return JSONResponse(
            content={"error": f"Property not found for identifier: {iri}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    nodes, edges = get_property_neighbors(prop, folio, property_children)

    # INTERIM: strip_folio_prefix calls below can be removed once FOLIO PR #5 is merged
    # Build parent list
    parents = []
    for parent_iri in prop.sub_property_of:
        if parent_iri == OWL_TOP_OBJECT_PROPERTY:
            continue
        parent = folio.get_property(parent_iri)
        if parent:
            parents.append({
                "iri": parent.iri,
                "label": strip_folio_prefix(parent.label or "Unnamed Property"),
                "definition": parent.definition or "No definition available",
            })
    parents.sort(key=lambda x: x["label"].lower())

    # Build children list
    children_props = _get_child_properties(folio, prop.iri, property_children)
    children = [
        {
            "iri": c.iri,
            "label": strip_folio_prefix(c.label or "Unnamed Property"),
            "definition": c.definition or "No definition available",
        }
        for c in children_props
    ]

    # Build domain classes
    domain_classes = []
    for d_iri in prop.domain:
        cls = folio[d_iri]
        if cls:
            domain_classes.append({
                "iri": cls.iri,
                "label": cls.label or "Unnamed Class",
                "definition": cls.definition or "No definition available",
            })
    domain_classes.sort(key=lambda x: x["label"].lower())

    # Build range classes
    range_classes = []
    for r_iri in prop.range:
        cls = folio[r_iri]
        if cls:
            range_classes.append({
                "iri": cls.iri,
                "label": cls.label or "Unnamed Class",
                "definition": cls.definition or "No definition available",
            })
    range_classes.sort(key=lambda x: x["label"].lower())

    # Inverse property
    inverse_data = None
    if prop.inverse_of:
        inv = folio.get_property(prop.inverse_of)
        if inv:
            inverse_data = {
                "iri": inv.iri,
                "label": strip_folio_prefix(inv.label or "Unnamed Property"),
                "definition": inv.definition or "No definition available",
            }

    result = {
        "iri": prop.iri,
        "label": strip_folio_prefix(prop.label or "Unnamed Property"),
        "definition": prop.definition or "No definition available",
        # INTERIM: strip_folio_prefix on preferred_label and alternative_labels can be removed once FOLIO PR #5 is merged
        "preferred_label": strip_folio_prefix(prop.preferred_label) if prop.preferred_label else None,
        "alternative_labels": [strip_folio_prefix(al) for al in prop.alternative_labels] if prop.alternative_labels else [],
        "examples": prop.examples,
        "parents": parents,
        "children": children,
        "domain_classes": domain_classes,
        "range_classes": range_classes,
        "inverse": inverse_data,
        "entity_type": "property",
        "nodes": nodes,
        "edges": edges,
    }

    return JSONResponse(content=result)


@router.get(
    "/tree/path/{iri:path}",
    tags=["properties"],
    response_model=None,
    summary="Get Path to Property Node",
    description="Get the complete path from root to a specific property in the tree",
    status_code=status.HTTP_200_OK,
)
async def get_property_path(request: Request, iri: str) -> JSONResponse:
    """Get the complete path from root to a specific property."""
    folio: FOLIO = request.app.state.folio

    prop = _find_property(folio, iri)
    if not prop:
        return JSONResponse(
            content={"error": f"Property not found for identifier: {iri}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    path = []
    current = prop

    path.insert(0, {
        "iri": current.iri,
        "label": current.label or "Unnamed Property",
        "id": current.iri.split("/")[-1] if current.iri.startswith("http") else current.iri,
    })

    while current and current.sub_property_of:
        parent_iri = current.sub_property_of[0]
        if parent_iri == OWL_TOP_OBJECT_PROPERTY:
            break
        parent = folio.get_property(parent_iri)
        if parent:
            path.insert(0, {
                "iri": parent.iri,
                "label": parent.label or "Unnamed Property",
                "id": parent.iri.split("/")[-1] if parent.iri.startswith("http") else parent.iri,
            })
            current = parent
        else:
            break

    return JSONResponse(content={"path": path})


@router.get(
    "/tree/search",
    tags=["properties"],
    response_model=None,
    summary="Search Property Tree",
    description="Search for properties and return a filtered tree structure",
    status_code=status.HTTP_200_OK,
)
async def search_property_tree(request: Request, query: str) -> JSONResponse:
    """Search for properties and return a filtered tree structure."""
    folio: FOLIO = request.app.state.folio

    if not query or len(query) < 2:
        return JSONResponse(content={"matches": [], "tree": {}})

    def _get_match_field(prop, q_lower):
        """Determine which field matched the search query."""
        if prop.label and q_lower in prop.label.lower():
            return "label"
        if prop.alternative_labels:
            for alt in prop.alternative_labels:
                if alt and q_lower in alt.lower():
                    return "alternative_labels"
        if prop.preferred_label and q_lower in prop.preferred_label.lower():
            return "preferred_label"
        if prop.definition and q_lower in prop.definition.lower():
            return "definition"
        return "label"  # fallback

    # Search properties
    search_results = []
    seen_iris = set()
    query_lower = query.lower()

    for prop in folio.object_properties:
        if prop.iri in seen_iris or _is_in_hidden_branch(folio, prop):
            continue

        label_match = False
        if prop.label and query_lower in prop.label.lower():
            label_match = True

        if not label_match and prop.alternative_labels:
            for alt in prop.alternative_labels:
                if alt and query_lower in alt.lower():
                    label_match = True
                    break

        # Check preferred label (skos:prefLabel)
        if not label_match and prop.preferred_label:
            if query_lower in prop.preferred_label.lower():
                label_match = True

        if not label_match and prop.definition and query_lower in prop.definition.lower():
            label_match = True

        if label_match:
            seen_iris.add(prop.iri)
            search_results.append(prop)

    if not search_results:
        return JSONResponse(content={"matches": [], "tree": {}})

    # Build filtered tree
    included_nodes = set()
    matches = []

    for prop in search_results:
        matches.append({
            "iri": prop.iri,
            "label": strip_folio_prefix(prop.label or "Unnamed Property"),
            "definition": prop.definition or "No definition available",
            "is_match": True,
        })
        included_nodes.add(prop.iri)

        # Trace ancestors
        current = prop
        while current and current.sub_property_of:
            for parent_iri in current.sub_property_of:
                if parent_iri == OWL_TOP_OBJECT_PROPERTY:
                    continue
                parent = folio.get_property(parent_iri)
                if parent:
                    included_nodes.add(parent_iri)
                    current = parent
                    break
            else:
                break

    # Build tree structure
    tree = {"nodes": {}, "root_nodes": []}

    for node_iri in included_nodes:
        prop = folio.get_property(node_iri)
        if prop:
            is_match = any(m["iri"] == node_iri for m in matches)
            tree["nodes"][node_iri] = {
                "id": node_iri,
                "label": strip_folio_prefix(prop.label or "Unnamed Property"),
                "preferred_label": strip_folio_prefix(prop.preferred_label) if prop.preferred_label else None,
                "children": [],
                "is_match": is_match,
                "match_field": _get_match_field(prop, query_lower) if is_match else None,
            }

    # Build parent-child relationships
    for node_iri in tree["nodes"]:
        prop = folio.get_property(node_iri)
        is_top_level = True

        if prop and prop.sub_property_of:
            for parent_iri in prop.sub_property_of:
                if parent_iri == OWL_TOP_OBJECT_PROPERTY:
                    continue
                if parent_iri in tree["nodes"]:
                    tree["nodes"][parent_iri]["children"].append(node_iri)
                    is_top_level = False

        if is_top_level:
            tree["root_nodes"].append(node_iri)

    matches.sort(key=lambda x: x["label"].lower())

    # Sort children and root_nodes
    for node_iri in tree["nodes"]:
        children = tree["nodes"][node_iri]["children"]
        if children:
            children_sorted = sorted(
                children,
                key=lambda c: tree["nodes"].get(c, {}).get("label", "").lower()
            )
            tree["nodes"][node_iri]["children"] = children_sorted

    tree["root_nodes"] = sorted(
        tree["root_nodes"],
        key=lambda n: tree["nodes"].get(n, {}).get("label", "").lower()
    )

    return JSONResponse(content={"matches": matches, "tree": tree})


@router.get(
    "/property-details/{iri:path}",
    tags=["properties"],
    response_model=None,
    summary="Get Rendered Property Details",
    description="Get rendered HTML for a property's details using Jinja2 templates",
    include_in_schema=False,
)
async def get_property_details_html(request: Request, iri: str) -> Response:
    """Get rendered HTML for a specific property's details."""
    folio: FOLIO = request.app.state.folio
    property_children = getattr(request.app.state, "property_children", None)

    prop = _find_property(folio, iri)
    if not prop:
        return request.app.state.templates.TemplateResponse(
            "components/property_details.html", {"request": request, "prop_data": None}
        )

    nodes, edges = get_property_neighbors(prop, folio, property_children)

    # Build parent list
    parents = []
    for parent_iri in prop.sub_property_of:
        if parent_iri == OWL_TOP_OBJECT_PROPERTY:
            continue
        parent = folio.get_property(parent_iri)
        if parent:
            parents.append({
                "iri": parent.iri,
                # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
                "label": strip_folio_prefix(parent.label or "Unnamed Property"),
                "definition": parent.definition or "No definition available",
            })
    parents.sort(key=lambda x: x["label"].lower())

    # Build children
    children_props = _get_child_properties(folio, prop.iri, property_children)
    children = [
        # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
        {"iri": c.iri, "label": strip_folio_prefix(c.label or "Unnamed Property"), "definition": c.definition or "No definition available"}
        for c in children_props
    ]

    # Domain classes
    domain_classes = []
    for d_iri in prop.domain:
        cls = folio[d_iri]
        if cls:
            domain_classes.append({"iri": cls.iri, "label": cls.label or "Unnamed", "definition": cls.definition or ""})
    domain_classes.sort(key=lambda x: x["label"].lower())

    # Range classes
    range_classes = []
    for r_iri in prop.range:
        cls = folio[r_iri]
        if cls:
            range_classes.append({"iri": cls.iri, "label": cls.label or "Unnamed", "definition": cls.definition or ""})
    range_classes.sort(key=lambda x: x["label"].lower())

    # Inverse
    inverse_data = None
    if prop.inverse_of:
        inv = folio.get_property(prop.inverse_of)
        if inv:
            # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
            inverse_data = {"iri": inv.iri, "label": strip_folio_prefix(inv.label or "Unnamed Property")}

    # INTERIM: strip_folio_prefix calls below can be removed once FOLIO PR #5 is merged
    prop_data = {
        "iri": prop.iri,
        "label": strip_folio_prefix(prop.label or "Unnamed Property"),
        "definition": prop.definition or "No definition available",
        "preferred_label": strip_folio_prefix(prop.preferred_label) if prop.preferred_label else None,
        # INTERIM: strip_folio_prefix on alternative_labels can be removed once FOLIO PR #5 is merged
        "alternative_labels": [strip_folio_prefix(al) for al in prop.alternative_labels] if prop.alternative_labels else [],
        "examples": prop.examples,
        "parents": parents,
        "children": children,
        "domain_classes": domain_classes,
        "range_classes": range_classes,
        "inverse": inverse_data,
        "nodes": nodes,
        "edges": edges,
    }

    return request.app.state.templates.TemplateResponse(
        "components/property_details.html",
        {"request": request, "prop_data": prop_data},
    )
