"""
Root API routes for IRI resolution.
"""

# imports
import json

# packages
from fastapi import APIRouter, Request, status
from folio import FOLIO, OWLClass, OWLObjectProperty
from starlette.responses import JSONResponse, Response

# project
from folio_api.rendering import get_node_neighbors, get_property_neighbors, strip_folio_prefix

# API router
router = APIRouter(prefix="", tags=["ontology"])

# The OWL top-level property IRI
OWL_TOP_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#topObjectProperty"


def _resolve_iri(folio: FOLIO, iri: str):
    """Resolve an IRI to either a class or property.

    Returns:
        tuple: (entity, entity_type) where entity_type is "class", "property", or None
    """
    # Try class first
    owl_class = folio[iri]
    if owl_class:
        return owl_class, "class"

    # Try property
    prop = folio.get_property(iri)
    if prop:
        return prop, "property"

    # Strategy 2: Extract ID from full IRI
    if iri.startswith("http"):
        parts = iri.rstrip("/").split("/")
        if parts:
            id_part = parts[-1]
            owl_class = folio[id_part]
            if owl_class:
                return owl_class, "class"
            prop = folio.get_property(id_part)
            if prop:
                return prop, "property"

    # Strategy 3: Prepend FOLIO prefix
    if not iri.startswith("http"):
        full_iri = f"https://folio.openlegalstandard.org/{iri}"
        owl_class = folio[full_iri]
        if owl_class:
            return owl_class, "class"
        prop = folio.get_property(full_iri)
        if prop:
            return prop, "property"

    # Strategy 4: Scan all for suffix match
    for cls in folio.classes:
        if hasattr(cls, "iri") and (cls.iri.endswith(iri) or iri.endswith(cls.iri)):
            return cls, "class"
    for p in folio.object_properties:
        if p.iri.endswith(iri) or iri.endswith(p.iri):
            return p, "property"

    return None, None


# redirect GET / to /docs
@router.get(
    "/",
    tags=["documentation"],
    summary="API Documentation",
    description="Redirects to the Swagger UI documentation",
    status_code=status.HTTP_301_MOVED_PERMANENTLY,
    responses={
        status.HTTP_301_MOVED_PERMANENTLY: {
            "description": "Redirect to API documentation",
            "headers": {
                "Location": {
                    "description": "URL to the API documentation",
                    "schema": {"type": "string", "example": "/docs"},
                }
            },
        }
    },
)
async def root_redirect() -> Response:
    """
    Redirects the user to the API documentation (Swagger UI).

    This endpoint performs a 301 (permanent) redirect to the /docs endpoint,
    which serves the interactive API documentation.

    Use this endpoint when accessing the API root to quickly navigate to the
    documentation interface.

    HTTP Status Codes:
    - 301 Moved Permanently: Redirect to the API documentation
    """
    return Response(
        status_code=status.HTTP_301_MOVED_PERMANENTLY, headers={"Location": "/docs"}
    )


@router.get(
    "/{iri}",
    tags=["ontology"],
    response_model=OWLClass,
    summary="Get Class by IRI (JSON)",
    description="Retrieves ontology class information by its IRI identifier in JSON format",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Successfully retrieved class information",
            "content": {
                "application/json": {
                    "example": {
                        "iri": "R8pNPutX0TN6DlEqkyZuxSw",
                        "label": "Lessor",
                        "definition": "A party that grants a right to use something in return for payment.",
                        "subClassOf": ["oS5FqyVBbOYQbhqb0G28oZR"],
                        "superClassOfIris": ["tBwJ5Vv1FxWdYC7hb3rCJcG"],
                    }
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Class not found",
            "content": {
                "application/json": {"example": {"message": "Class not found."}}
            },
        },
    },
)
async def get_class(request: Request, iri: str) -> OWLClass:
    """
    Retrieve detailed information about a FOLIO ontology class or property by its IRI in JSON format.

    This endpoint returns comprehensive information about the requested entity, including:
    - Label and definition
    - Parent and child relationships
    - Additional metadata

    The IRI parameter is typically the unique identifier, such as `R8pNPutX0TN6DlEqkyZuxSw`.

    HTTP Status Codes:
    - 200 OK: Successfully retrieved entity information
    - 404 Not Found: The requested IRI does not exist in the ontology
    """
    folio: FOLIO = request.app.state.folio
    entity, entity_type = _resolve_iri(folio, iri)
    if not entity:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Entity not found."},
        )

    return entity


@router.get(
    "/{iri}/markdown",
    tags=["ontology"],
    response_model=None,
    summary="Get Class by IRI (Markdown)",
    description="Retrieves ontology class information by its IRI identifier in Markdown format",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Successfully retrieved class information in Markdown format",
            "content": {
                "text/markdown": {
                    "example": "# Lessor\n\nA party that grants a right to use something in return for payment.\n\n## Taxonomy\n\n* Parent class: Party\n* Child classes: None\n\n## Properties\n\n* grants_rights"
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Class not found",
            "content": {"text/plain": {"example": "Class not found."}},
        },
    },
)
async def get_class_markdown(request: Request, iri: str) -> Response:
    """
    Retrieve information about a FOLIO ontology entity by its IRI in Markdown format.

    HTTP Status Codes:
    - 200 OK: Successfully retrieved entity information in Markdown format
    - 404 Not Found: The requested IRI does not exist in the ontology
    """
    folio: FOLIO = request.app.state.folio
    entity, entity_type = _resolve_iri(folio, iri)
    if not entity:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content="Entity not found.",
            media_type="text/plain",
        )

    if entity_type == "class":
        return Response(content=entity.to_markdown(), media_type="text/markdown")

    # Inline markdown for properties (OWLObjectProperty lacks to_markdown())
    prop = entity
    # INTERIM: strip_folio_prefix calls below can be removed once FOLIO PR #5 is merged
    lines = [f"# {strip_folio_prefix(prop.label or 'Unnamed Property')}", ""]
    lines.append(f"**Type:** OWL Object Property  ")
    lines.append(f"**IRI:** `{prop.iri}`  ")
    lines.append("")
    if prop.definition:
        lines.append(f"{prop.definition}")
        lines.append("")
    if prop.examples:
        lines.append("## Examples")
        lines.append("")
        for ex in prop.examples:
            lines.append(f"- {ex}")
        lines.append("")
    if prop.sub_property_of:
        lines.append("## Parent Properties")
        lines.append("")
        for p_iri in prop.sub_property_of:
            if p_iri == OWL_TOP_OBJECT_PROPERTY:
                continue
            p = folio.get_property(p_iri)
            # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
            lines.append(f"- {strip_folio_prefix(p.label) if p else p_iri}")
        lines.append("")
    if prop.domain:
        lines.append("## Domain")
        lines.append("")
        for d_iri in prop.domain:
            cls = folio[d_iri]
            lines.append(f"- {cls.label if cls else d_iri}")
        lines.append("")
    if prop.range:
        lines.append("## Range")
        lines.append("")
        for r_iri in prop.range:
            cls = folio[r_iri]
            lines.append(f"- {cls.label if cls else r_iri}")
        lines.append("")
    if prop.inverse_of:
        inv = folio.get_property(prop.inverse_of)
        lines.append(f"## Inverse Of")
        lines.append("")
        # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
        lines.append(f"- {strip_folio_prefix(inv.label) if inv else prop.inverse_of}")
        lines.append("")
    return Response(content="\n".join(lines), media_type="text/markdown")


@router.get(
    "/{iri}/jsonld",
    tags=["ontology"],
    response_model=None,
    summary="Get Class by IRI (JSON-LD)",
    description="Retrieves ontology class information by its IRI identifier in JSON-LD format",
)
async def get_class_jsonld(request: Request, iri: str) -> JSONResponse:
    """
    Retrieve information about a FOLIO ontology class by its IRI in JSON-LD format.

    This endpoint returns the class information in JSON-LD (JSON for Linking Data) format,
    which is designed for representing linked data with support for semantic web concepts.

    JSON-LD is particularly useful for:
    - Semantic web applications
    - Linked data integration
    - Providing context for JSON data
    - Machine-readable semantics

    Example URLs:
    - `/R8pNPutX0TN6DlEqkyZuxSw/jsonld` - Returns the Lessor class in JSON-LD format

    The response includes the '@context' object that maps properties to IRIs, making the
    data semantically meaningful for linked data applications.

    If the IRI does not exist in the ontology, a 404 error is returned.
    """

    folio: FOLIO = request.app.state.folio
    entity, entity_type = _resolve_iri(folio, iri)
    if not entity:
        return JSONResponse(status_code=404, content={"message": "Entity not found."})

    if entity_type == "class":
        return JSONResponse(
            content=entity.to_jsonld(), media_type="application/ld+json"
        )

    # Inline JSON-LD for properties
    prop = entity
    jsonld = {
        "@context": {
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "folio": "https://folio.openlegalstandard.org/",
        },
        "@type": "owl:ObjectProperty",
        "@id": prop.iri,
        "rdfs:label": prop.label,
        "rdfs:comment": prop.definition,
    }
    if prop.sub_property_of:
        jsonld["rdfs:subPropertyOf"] = prop.sub_property_of
    if prop.domain:
        jsonld["rdfs:domain"] = prop.domain
    if prop.range:
        jsonld["rdfs:range"] = prop.range
    if prop.inverse_of:
        jsonld["owl:inverseOf"] = prop.inverse_of
    return JSONResponse(content=jsonld, media_type="application/ld+json")


@router.get(
    "/{iri}/xml",
    tags=["ontology"],
    response_model=None,
    summary="Get Class by IRI (OWL XML)",
    description="Retrieves ontology class information by its IRI identifier in OWL XML format",
)
async def get_class_xml(request: Request, iri: str) -> Response:
    """
    Retrieve information about a FOLIO ontology class by its IRI in OWL XML format.

    This endpoint returns the class information in Web Ontology Language (OWL) XML format,
    which is the standard XML serialization format for OWL ontologies.

    The OWL XML format is particularly useful for:
    - Ontology tools that work with the OWL standard
    - Integration with semantic web frameworks
    - Formal reasoning systems
    - Compatibility with ontology editors like Protégé

    Example URLs:
    - `/R8pNPutX0TN6DlEqkyZuxSw/xml` - Returns the Lessor class in OWL XML format

    If the IRI does not exist in the ontology, a 404 error is returned.
    """

    folio: FOLIO = request.app.state.folio
    entity, entity_type = _resolve_iri(folio, iri)
    if not entity:
        return Response(
            status_code=404, content=json.dumps({"message": "Entity not found."})
        )

    if entity_type == "class":
        return Response(content=entity.to_owl_xml(), media_type="application/xml")

    # Inline OWL XML for properties
    prop = entity
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Ontology xmlns="http://www.w3.org/2002/07/owl#"',
        '         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">',
        f'  <ObjectProperty IRI="{prop.iri}">',
    ]
    if prop.label:
        xml_parts.append(f'    <rdfs:label>{prop.label}</rdfs:label>')
    if prop.definition:
        xml_parts.append(f'    <rdfs:comment>{prop.definition}</rdfs:comment>')
    for p_iri in prop.sub_property_of:
        xml_parts.append(f'    <SubObjectPropertyOf IRI="{p_iri}"/>')
    for d_iri in prop.domain:
        xml_parts.append(f'    <ObjectPropertyDomain IRI="{d_iri}"/>')
    for r_iri in prop.range:
        xml_parts.append(f'    <ObjectPropertyRange IRI="{r_iri}"/>')
    if prop.inverse_of:
        xml_parts.append(f'    <InverseObjectProperties IRI="{prop.inverse_of}"/>')
    xml_parts.append('  </ObjectProperty>')
    xml_parts.append('</Ontology>')
    return Response(content="\n".join(xml_parts), media_type="application/xml")


@router.get(
    "/{iri}/html",
    tags=["ontology"],
    response_model=None,
    summary="Get Class by IRI (HTML)",
    description="Retrieves ontology class information by its IRI identifier in a human-readable HTML format",
)
async def get_class_html(request: Request, iri: str) -> Response:
    """
    Retrieve information about a FOLIO ontology class by its IRI in a rich HTML format.

    This endpoint returns an interactive HTML representation of the requested class, styled with
    Tailwind CSS for a modern, responsive design. The HTML format is ideal for:

    - Human-readable browsing of the ontology
    - Educational purposes and learning about FOLIO
    - Sharing class information with non-technical stakeholders
    - Quick reference of class properties and relationships

    The HTML view includes:
    - Class label and definition
    - Hierarchical view of parent and child classes
    - Properties and relationships
    - Interactive elements for navigation

    Example URLs:
    - `/R8pNPutX0TN6DlEqkyZuxSw/html` - Returns the Lessor class in HTML format

    If the IRI does not exist in the ontology, a 404 error is returned.
    """
    folio: FOLIO = request.app.state.folio
    entity, entity_type = _resolve_iri(folio, iri)
    if not entity:
        return Response(
            status_code=404, content=json.dumps({"message": "Entity not found."})
        )

    # Import JavaScript for typeahead search
    from pathlib import Path

    typeahead_js_path = (
        Path(__file__).parent.parent / "static" / "js" / "typeahead_search.js"
    )
    typeahead_js_source = typeahead_js_path.read_text(encoding="utf-8")

    if entity_type == "class":
        owl_class = entity
        nodes, edges = get_node_neighbors(owl_class, folio)

        # Compute cross-linking: properties with this class as domain or range
        domain_properties = []
        range_properties = []
        for p in folio.object_properties:
            if owl_class.iri in p.domain:
                # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
                domain_properties.append({"iri": p.iri, "label": strip_folio_prefix(p.label or p.iri)})
            if owl_class.iri in p.range:
                # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
                range_properties.append({"iri": p.iri, "label": strip_folio_prefix(p.label or p.iri)})
        domain_properties.sort(key=lambda x: x["label"].lower())
        range_properties.sort(key=lambda x: x["label"].lower())

        return request.app.state.templates.TemplateResponse(
            "taxonomy/class_detail.html",
            {
                "request": request,
                "owl_class": owl_class,
                "folio_graph": folio,
                "nodes": nodes,
                "edges": edges,
                "config": request.app.state.config,
                "typeahead_js_source": typeahead_js_source,
                "domain_properties": domain_properties,
                "range_properties": range_properties,
            },
        )

    # Property HTML rendering
    prop = entity
    property_children = getattr(request.app.state, "property_children", None)
    nodes, edges = get_property_neighbors(prop, folio, property_children)

    # Build parent list
    parents = []
    for parent_iri in prop.sub_property_of:
        if parent_iri == OWL_TOP_OBJECT_PROPERTY:
            continue
        parent = folio.get_property(parent_iri)
        if parent:
            # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
            parents.append({"iri": parent.iri, "label": strip_folio_prefix(parent.label or "Unnamed Property")})
    parents.sort(key=lambda x: x["label"].lower())

    # Build children list
    from folio_api.routes.properties import _get_child_properties
    children_props = _get_child_properties(folio, prop.iri, property_children)
    # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
    children = [{"iri": c.iri, "label": strip_folio_prefix(c.label or "Unnamed Property")} for c in children_props]

    # Domain/range classes
    domain_classes = []
    for d_iri in prop.domain:
        cls = folio[d_iri]
        if cls:
            domain_classes.append({"iri": cls.iri, "label": cls.label or "Unnamed"})
    domain_classes.sort(key=lambda x: x["label"].lower())

    range_classes = []
    for r_iri in prop.range:
        cls = folio[r_iri]
        if cls:
            range_classes.append({"iri": cls.iri, "label": cls.label or "Unnamed"})
    range_classes.sort(key=lambda x: x["label"].lower())

    # Inverse
    inverse_data = None
    if prop.inverse_of:
        inv = folio.get_property(prop.inverse_of)
        if inv:
            # INTERIM: strip_folio_prefix can be removed once FOLIO PR #5 is merged
            inverse_data = {"iri": inv.iri, "label": strip_folio_prefix(inv.label or "Unnamed Property")}

    return request.app.state.templates.TemplateResponse(
        "properties/property_detail.html",
        {
            "request": request,
            "prop": prop,
            "folio_graph": folio,
            "nodes": nodes,
            "edges": edges,
            "config": request.app.state.config,
            "typeahead_js_source": typeahead_js_source,
            "parents": parents,
            "children": children,
            "domain_classes": domain_classes,
            "range_classes": range_classes,
            "inverse_data": inverse_data,
        },
    )
