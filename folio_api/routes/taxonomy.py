"""
Taxonomy routes for the FOLIO API.
"""

# imports
from pathlib import Path

# packages
from fastapi import APIRouter, Request, status
from folio import FOLIO, FOLIO_TYPE_IRIS
from starlette.responses import Response, JSONResponse

# project
from folio_api.models import OWLClassList
from folio_api.rendering import get_node_neighbors

# API router
router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


@router.get(
    "/actor_player",
    tags=["taxonomy"],
    response_model=OWLClassList,
    summary="Get Actor Player Classes",
    description="Retrieve all Actor Player classes from the FOLIO ontology with optional traversal depth",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Successfully retrieved actor player classes",
            "content": {
                "application/json": {
                    "example": {
                        "classes": [
                            {
                                "iri": "kL8jH4gF2dS5aP9oI6uY3tR",
                                "label": "Legal Person",
                                "definition": "An entity recognized by the legal system as having legal rights and obligations.",
                            },
                            {
                                "iri": "7bN3mK6jH5gF1dS4aP8oI7u",
                                "label": "Natural Person",
                                "definition": "A human being, as distinguished from a legal entity created by law.",
                            },
                        ]
                    }
                }
            },
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error (e.g., invalid max_depth parameter)",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "max_depth"],
                                "msg": "value is not a valid integer",
                                "type": "type_error.integer",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def get_actor_player(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Retrieve all classes of type 'Actor Player' from the FOLIO ontology.

    Actor Players in FOLIO represent entities that can participate in legal relationships,
    such as individuals, organizations, or other legal entities that can act within legal contexts.

    This endpoint returns the entire hierarchy of Actor Player classes, allowing you to explore:
    - Types of legal entities
    - Roles that individuals or organizations can play in legal contexts
    - Relationships between different actor types

    Parameters:
    - max_depth: Controls how many levels of subclasses to include (default: 1)
      - Set to 1 for direct subclasses only
      - Set to higher values to retrieve deeper hierarchies
      - Higher values will return more classes but may increase response time

    HTTP Status Codes:
    - 200 OK: Successfully retrieved actor player classes
    - 422 Unprocessable Entity: Validation error (e.g., invalid max_depth parameter)

    Example response:
    ```json
    {
      "classes": [
        {
          "iri": "kL8jH4gF2dS5aP9oI6uY3tR",
          "label": "Legal Person",
          "definition": "An entity recognized by the legal system as having legal rights and obligations.",
          ...
        },
        {
          "iri": "7bN3mK6jH5gF1dS4aP8oI7u",
          "label": "Natural Person",
          "definition": "A human being, as distinguished from a legal entity created by law.",
          ...
        },
        ...
      ]
    }
    ```

    Use this endpoint to explore the taxonomy of actors in the legal domain and understand
    the different types of entities that can participate in legal relationships.
    """
    # Parameter validation is handled by FastAPI via the type annotation (int)
    # If max_depth is not an integer, FastAPI will return a 422 Unprocessable Entity error

    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_player_actors(max_depth=max_depth))


@router.get(
    "/area_of_law",
    tags=["taxonomy"],
    response_model=OWLClassList,
    summary="Get Area of Law Classes",
    description="Retrieve all Area of Law classes from the FOLIO ontology with optional traversal depth",
)
async def get_area_of_law(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Area of Law.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_areas_of_law(max_depth=max_depth))


@router.get("/asset_type", tags=["taxonomy"], response_model=OWLClassList)
async def get_asset_type(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Asset Type.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_asset_types(max_depth=max_depth))


@router.get("/communication_modality", tags=["taxonomy"], response_model=OWLClassList)
async def get_communication_modality(
    request: Request, max_depth: int = 1
) -> OWLClassList:
    """
    Get all classes of type Communication Modality.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_communication_modalities(max_depth=max_depth))


@router.get("/currency", tags=["taxonomy"], response_model=OWLClassList)
async def get_currency(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Currency.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_currencies(max_depth=max_depth))


@router.get("/data_format", tags=["taxonomy"], response_model=OWLClassList)
async def get_data_format(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Data Format.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_data_formats(max_depth=max_depth))


@router.get("/document_artifact", tags=["taxonomy"], response_model=OWLClassList)
async def get_document_artifact(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Document Artifact.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_document_artifacts(max_depth=max_depth))


@router.get("/engagement_terms", tags=["taxonomy"], response_model=OWLClassList)
async def get_engagement_terms(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Engagement Terms.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_engagement_terms(max_depth=max_depth))


@router.get("/event", tags=["taxonomy"], response_model=OWLClassList)
async def get_event(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Event.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_events(max_depth=max_depth))


@router.get("/forums_venues", tags=["taxonomy"], response_model=OWLClassList)
async def get_forums_venues(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Forums Venues.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_forum_venues(max_depth=max_depth))


@router.get("/governmental_body", tags=["taxonomy"], response_model=OWLClassList)
async def get_governmental_body(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Governmental Body.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_governmental_bodies(max_depth=max_depth))


@router.get("/industry", tags=["taxonomy"], response_model=OWLClassList)
async def get_industry(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Industry.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_industries(max_depth=max_depth))


@router.get("/language", tags=["taxonomy"], response_model=OWLClassList)
async def get_language(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Language.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_languages(max_depth=max_depth))


@router.get("/legal_authorities", tags=["taxonomy"], response_model=OWLClassList)
async def get_legal_authorities(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Legal Authorities.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_legal_authorities(max_depth=max_depth))


@router.get("/legal_entity", tags=["taxonomy"], response_model=OWLClassList)
async def get_legal_entity(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Legal Entity.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_legal_entities(max_depth=max_depth))


@router.get("/location", tags=["taxonomy"], response_model=OWLClassList)
async def get_location(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Location.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_locations(max_depth=max_depth))


@router.get("/matter_narrative", tags=["taxonomy"], response_model=OWLClassList)
async def get_matter_narrative(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Matter Narrative.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_matter_narratives(max_depth=max_depth))


@router.get("/matter_narrative_format", tags=["taxonomy"], response_model=OWLClassList)
async def get_matter_narrative_format(
    request: Request, max_depth: int = 1
) -> OWLClassList:
    """
    Get all classes of type Matter Narrative Format.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_matter_narrative_formats(max_depth=max_depth))


@router.get("/objectives", tags=["taxonomy"], response_model=OWLClassList)
async def get_objectives(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Objectives.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_objectives(max_depth=max_depth))


@router.get("/service", tags=["taxonomy"], response_model=OWLClassList)
async def get_service(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Service.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_services(max_depth=max_depth))


@router.get("/standards_compatibility", tags=["taxonomy"], response_model=OWLClassList)
async def get_standards_compatibility(
    request: Request, max_depth: int = 1
) -> OWLClassList:
    """
    Get all classes of type Standards Compatibility.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(
        classes=folio.get_standards_compatibilities(max_depth=max_depth)
    )


@router.get("/status", tags=["taxonomy"], response_model=OWLClassList)
async def get_status(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Status.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_statuses(max_depth=max_depth))


@router.get("/system_identifiers", tags=["taxonomy"], response_model=OWLClassList)
async def get_system_identifiers(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type System Identifiers.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_system_identifiers(max_depth=max_depth))


@router.get(
    "/tree/data",
    tags=["taxonomy"],
    response_model=None,
    summary="Get Taxonomy Tree Data",
    description="Get hierarchical data for the taxonomy tree view in jsTree format",
    status_code=status.HTTP_200_OK,
)
async def get_tree_data(
    request: Request, node_id: str = "#", max_depth: int = 1
) -> JSONResponse:
    """
    Get hierarchical data for the taxonomy tree in a format compatible with jsTree.

    This endpoint supports lazy loading of tree nodes by providing the node_id parameter.
    - For the root level (node_id = "#"), it returns top-level classes
    - For specific nodes, it returns their children

    Args:
        request (Request): FastAPI request object
        node_id (str): The ID of the node to get children for (default: "#" for root)
        max_depth (int): Maximum depth to traverse when getting children

    Returns:
        JSONResponse: A list of nodes in jsTree format
    """
    folio: FOLIO = request.app.state.folio

    # If requesting root nodes
    if node_id == "#":
        # OWL_THING URI from the FOLIO library
        OWL_THING = "http://www.w3.org/2002/07/owl#Thing"

        # Filter for classes that are direct subclasses of owl:Thing
        root_classes = []

        # Get all IRIs from the FOLIO instance
        for iri in FOLIO_TYPE_IRIS.values():
            owl_class = folio[iri]

            # Check if this class directly inherits from owl:Thing
            if hasattr(owl_class, "sub_class_of") and isinstance(
                owl_class.sub_class_of, list
            ):
                if (
                    len(owl_class.sub_class_of) == 1
                    and owl_class.sub_class_of[0] == OWL_THING
                ):
                    root_classes.append(owl_class)

        # Format for jsTree
        result = []
        for owl_class in root_classes:
            # Check if this class has children
            has_children = bool(owl_class.parent_class_of)

            result.append(
                {
                    "id": owl_class.iri,
                    "text": owl_class.label or "Unnamed Class",
                    "children": has_children,
                    "data": {
                        "iri": owl_class.iri,
                        "definition": owl_class.definition or "No definition available",
                        "type": "top_level",
                    },
                }
            )

        return JSONResponse(content=result)

    # If requesting children of a specific node
    else:
        owl_class = folio[node_id]
        if not owl_class:
            return JSONResponse(content=[])

        # Get children of this class
        children = []
        for child_iri in owl_class.parent_class_of:
            child = folio[child_iri]
            if child:
                # Check if this child has its own children
                has_grandchildren = bool(child.parent_class_of)

                children.append(
                    {
                        "id": child.iri,
                        "text": child.label or "Unnamed Class",
                        "children": has_grandchildren,
                        "data": {
                            "iri": child.iri,
                            "definition": child.definition or "No definition available",
                            "type": "subclass",
                        },
                    }
                )

        return JSONResponse(content=children)


@router.get(
    "/tree/node/{iri}",
    tags=["taxonomy"],
    response_model=None,
    summary="Get Single Node Data",
    description="Get detailed data for a single taxonomy node",
    status_code=status.HTTP_200_OK,
)
async def get_node_data(request: Request, iri: str) -> JSONResponse:
    """
    Get detailed data for a single taxonomy node by IRI.

    Args:
        request (Request): FastAPI request object
        iri (str): The IRI of the node to get data for

    Returns:
        JSONResponse: Detailed information about the node
    """
    folio: FOLIO = request.app.state.folio

    # Try multiple strategies to find the class
    owl_class = None

    # Strategy 1: Use the IRI directly as given
    owl_class = folio[iri]

    # Strategy 2: If not found and this is a full IRI, try extracting just the ID part
    if not owl_class and iri.startswith("http"):
        # Extract the ID from the full IRI - get the last part after the last '/'
        parts = iri.rstrip("/").split("/")
        if parts:
            id_part = parts[-1]
            owl_class = folio[id_part]

    # Strategy 3: If not found and this is just an ID, try with the FOLIO IRI prefix
    if not owl_class and not iri.startswith("http"):
        full_iri = f"https://folio.openlegalstandard.org/{iri}"
        owl_class = folio[full_iri]

    # Strategy 4: Try with just the ID part in the FOLIO dictionary directly
    if not owl_class:
        # One last attempt by checking all classes
        for cls in folio.classes:
            if hasattr(cls, "iri") and (cls.iri.endswith(iri) or iri.endswith(cls.iri)):
                owl_class = cls
                break

    if not owl_class:
        return JSONResponse(
            content={"error": f"Class not found for identifier: {iri}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Prepare node data
    nodes, edges = get_node_neighbors(owl_class, folio)

    # Build parent list
    parents = []
    if hasattr(owl_class, "sub_class_of") and owl_class.sub_class_of:
        for parent_iri in owl_class.sub_class_of:
            parent = folio[parent_iri]
            if parent:
                parents.append(
                    {
                        "iri": parent.iri,
                        "label": parent.label or "Unnamed Class",
                        "definition": parent.definition or "No definition available",
                    }
                )

    # Build children list
    children = []
    if hasattr(owl_class, "parent_class_of") and owl_class.parent_class_of:
        for child_iri in owl_class.parent_class_of:
            child = folio[child_iri]
            if child:
                children.append(
                    {
                        "iri": child.iri,
                        "label": child.label or "Unnamed Class",
                        "definition": child.definition or "No definition available",
                    }
                )

    # Check if translations are available
    translations = {}
    if hasattr(owl_class, "translations") and owl_class.translations:
        translations = owl_class.translations

    # Build see_also list with resolved labels
    see_also_items = []
    if hasattr(owl_class, "see_also") and owl_class.see_also:
        for see_also_iri in owl_class.see_also:
            if see_also_iri.startswith("http"):
                # Try to find the label for this IRI
                see_also_class = folio[see_also_iri]
                if see_also_class:
                    see_also_items.append(
                        {
                            "iri": see_also_iri,
                            "label": see_also_class.label or see_also_iri,
                            "is_external": False,
                        }
                    )
                else:
                    # External link or IRI not found in our ontology
                    see_also_items.append(
                        {
                            "iri": see_also_iri,
                            "label": see_also_iri,
                            "is_external": True,
                        }
                    )
            else:
                # Not a URL, just a string
                see_also_items.append(
                    {"iri": see_also_iri, "label": see_also_iri, "is_external": False}
                )

    result = {
        "iri": owl_class.iri,
        "label": owl_class.label or "Unnamed Class",
        "definition": owl_class.definition or "No definition available",
        "preferred_label": owl_class.preferred_label,
        "alternative_labels": owl_class.alternative_labels,
        "identifier": owl_class.identifier,
        "description": owl_class.description,
        "comment": owl_class.comment,
        "examples": owl_class.examples,
        "notes": owl_class.notes,
        "parents": parents,
        "children": children,
        "see_also": owl_class.see_also,  # Keep original for backward compatibility
        "see_also_items": see_also_items,  # Add the new detailed list
        "is_defined_by": owl_class.is_defined_by,
        "deprecated": owl_class.deprecated,
        "translations": translations,
        # Add the new fields
        "history_note": owl_class.history_note
        if hasattr(owl_class, "history_note")
        else None,
        "editorial_note": owl_class.editorial_note
        if hasattr(owl_class, "editorial_note")
        else None,
        "in_scheme": owl_class.in_scheme if hasattr(owl_class, "in_scheme") else None,
        "source": owl_class.source if hasattr(owl_class, "source") else None,
        "country": owl_class.country if hasattr(owl_class, "country") else None,
        "nodes": nodes,
        "edges": edges,
    }

    return JSONResponse(content=result)


@router.get(
    "/tree/path/{iri}",
    tags=["taxonomy"],
    response_model=None,
    summary="Get Path to Node",
    description="Get the complete path from root to a specific node in the taxonomy tree",
    status_code=status.HTTP_200_OK,
)
async def get_path_to_node(request: Request, iri: str) -> JSONResponse:
    """
    Get the complete path from root to a specific node in the taxonomy tree.

    This endpoint is useful for expanding the tree to show a specific node that
    may be deep in the hierarchy. It returns an ordered array of nodes representing
    the full path from a root node to the requested node.

    Args:
        request (Request): FastAPI request object
        iri (str): The IRI of the node to find the path for

    Returns:
        JSONResponse: An array of nodes representing the path from root to the target node
    """
    folio: FOLIO = request.app.state.folio

    # Try multiple strategies to find the class
    owl_class = None

    # Strategy 1: Use the IRI directly as given
    owl_class = folio[iri]

    # Strategy 2: If not found and this is a full IRI, try extracting just the ID part
    if not owl_class and iri.startswith("http"):
        # Extract the ID from the full IRI - get the last part after the last '/'
        parts = iri.rstrip("/").split("/")
        if parts:
            id_part = parts[-1]
            owl_class = folio[id_part]

    # Strategy 3: If not found and this is just an ID, try with the FOLIO IRI prefix
    if not owl_class and not iri.startswith("http"):
        full_iri = f"https://folio.openlegalstandard.org/{iri}"
        owl_class = folio[full_iri]

    # Strategy 4: Try with just the ID part in the FOLIO dictionary directly
    if not owl_class:
        # One last attempt by checking all classes
        for cls in folio.classes:
            if hasattr(cls, "iri") and (cls.iri.endswith(iri) or iri.endswith(cls.iri)):
                owl_class = cls
                break

    if not owl_class:
        return JSONResponse(
            content={"error": f"Class not found for identifier: {iri}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Start building the path from the current node
    path = []
    current = owl_class

    # Add current node to path
    path.insert(
        0,
        {
            "iri": current.iri,
            "label": current.label or "Unnamed Class",
            "id": current.iri.split("/")[-1]
            if current.iri.startswith("http")
            else current.iri,
        },
    )

    # Traverse up the parent hierarchy to build the path
    while current and hasattr(current, "sub_class_of") and current.sub_class_of:
        # Get the first parent - assuming a tree structure
        # In a multi-inheritance scenario, we would need to choose which path to follow
        parent_iri = current.sub_class_of[0]

        # Skip owl:Thing as it's not part of our visible tree
        if parent_iri == "http://www.w3.org/2002/07/owl#Thing":
            break

        parent = folio[parent_iri]
        if parent:
            # Add parent to the beginning of the path
            path.insert(
                0,
                {
                    "iri": parent.iri,
                    "label": parent.label or "Unnamed Class",
                    "id": parent.iri.split("/")[-1]
                    if parent.iri.startswith("http")
                    else parent.iri,
                },
            )
            current = parent
        else:
            # If parent not found, stop traversal
            break

    return JSONResponse(content={"path": path})


@router.get(
    "/tree/search",
    tags=["taxonomy"],
    response_model=None,
    summary="Search Taxonomy Tree",
    description="Search for classes and return a filtered tree structure containing only matches and their ancestors",
    status_code=status.HTTP_200_OK,
)
async def search_taxonomy_tree(request: Request, query: str) -> JSONResponse:
    """
    Search for classes in the taxonomy and return a filtered tree structure.

    This endpoint combines search functionality with tree structure building:
    1. It searches for all classes matching the query
    2. For each match, it finds all ancestors up to the root
    3. It returns a complete tree structure containing only matches and their ancestry

    This allows the client to display a filtered tree view without multiple API calls.

    Args:
        request (Request): FastAPI request object
        query (str): The search query string

    Returns:
        JSONResponse: A filtered tree structure containing only matching classes and their ancestors
    """
    folio: FOLIO = request.app.state.folio

    # First, search for matching classes
    # Reusing exactly the same logic from search endpoint
    search_results = []
    seen_iris = set()

    # First, try to get results with original case
    prefix_results_original = folio.search_by_prefix(query)

    # Then try with lowercase
    query_lower = query.lower()
    prefix_results_lower = (
        [] if query == query_lower else folio.search_by_prefix(query_lower)
    )

    # Then try with uppercase first letter
    query_title = query.title()
    prefix_results_title = (
        [] if query == query_title else folio.search_by_prefix(query_title)
    )

    # Add results in order of priority but avoid duplicates
    for result_list in [
        prefix_results_original,
        prefix_results_lower,
        prefix_results_title,
    ]:
        for owl_class in result_list:
            if owl_class.iri not in seen_iris:
                seen_iris.add(owl_class.iri)
                search_results.append(owl_class)

    # Check all classes for substring matches in labels and alternative labels
    for owl_class in folio.classes:
        # Skip if we've already seen this IRI in prefix results
        if owl_class.iri in seen_iris:
            continue

        # Skip if class has no label
        if not owl_class.label:
            continue

        # Check if query is in the label (case-insensitive)
        # Also check alternative labels for matches
        label_match = False

        # Check main label
        if owl_class.label:
            if (
                query in owl_class.label
                or query_lower in owl_class.label.lower()
                or query_title in owl_class.label
            ):
                label_match = True

        # Check alternative labels
        if not label_match and owl_class.alternative_labels:
            for alt_label in owl_class.alternative_labels:
                if alt_label and (
                    query in alt_label
                    or query_lower in alt_label.lower()
                    or query_title in alt_label
                ):
                    label_match = True
                    break

        if label_match:
            seen_iris.add(owl_class.iri)
            search_results.append(owl_class)

    # Process search results
    if not search_results:
        return JSONResponse(content={"matches": [], "tree": {}})

    # Now build the filtered tree structure
    # We'll keep track of all nodes (classes) that should be in the tree
    included_nodes = set()
    matches = []

    # Process each match
    for cls in search_results:
        # Add this match to our results
        match_data = {
            "iri": cls.iri,
            "label": cls.label or "Unnamed Class",
            "definition": cls.definition or "No definition available",
            "is_match": True,  # Flag to identify this as a direct search match
        }
        matches.append(match_data)

        # Add this node to our included set
        included_nodes.add(cls.iri)

        # Now trace all ancestors and add them to included_nodes
        current = cls
        while current and hasattr(current, "sub_class_of") and current.sub_class_of:
            for parent_iri in current.sub_class_of:
                # Skip owl:Thing as it's the ultimate root
                if parent_iri == "http://www.w3.org/2002/07/owl#Thing":
                    continue

                # Get the parent class using the standard lookup pattern
                parent = folio[parent_iri]
                if parent:
                    included_nodes.add(parent_iri)
                    current = parent
                    # We only follow the first parent for simplicity
                    break
            else:
                # No valid parent found, break the loop
                break

    # Now build the actual tree structure
    tree = {
        "nodes": {},  # All nodes by IRI
        "root_nodes": [],  # Top-level nodes
    }

    # Step 1: Add all included nodes to the tree
    for node_iri in included_nodes:
        # Get the class using the standard lookup pattern
        cls = folio[node_iri]
        if cls:
            # Basic node data
            tree["nodes"][node_iri] = {
                "id": node_iri,
                "label": cls.label or "Unnamed Class",
                "children": [],
                "is_match": any(match["iri"] == node_iri for match in matches),
            }

    # Step 2: Build parent-child relationships
    for node_iri in tree["nodes"]:
        # Get the class using the standard lookup pattern
        cls = folio[node_iri]

        # Check if this is a top-level node (has no parents or parent is owl:Thing)
        is_top_level = True

        if hasattr(cls, "sub_class_of") and cls.sub_class_of:
            for parent_iri in cls.sub_class_of:
                # Skip owl:Thing
                if parent_iri == "http://www.w3.org/2002/07/owl#Thing":
                    continue

                # If the parent is in our included set, add this as a child
                if parent_iri in tree["nodes"]:
                    tree["nodes"][parent_iri]["children"].append(node_iri)
                    is_top_level = False

        # If this is a top-level node, add to root_nodes
        if is_top_level:
            tree["root_nodes"].append(node_iri)

    # Return the search matches and filtered tree structure
    return JSONResponse(content={"matches": matches, "tree": tree})


@router.get(
    "/class-details/{iri}",
    tags=["taxonomy"],
    response_model=None,
    summary="Get Rendered Class Details",
    description="Get rendered HTML for a class's details using Jinja2 templates",
    include_in_schema=False,  # Hide from API docs
)
async def get_class_details_html(request: Request, iri: str) -> Response:
    """
    Get rendered HTML for a specific class's details using Jinja2 templates.

    Args:
        request (Request): FastAPI request object
        iri (str): The IRI of the class to get details for

    Returns:
        Response: HTML content for the class details
    """
    folio: FOLIO = request.app.state.folio

    # Try multiple strategies to find the class
    owl_class = None

    # Strategy 1: Use the IRI directly as given
    owl_class = folio[iri]

    # Strategy 2: If not found and this is a full IRI, try extracting just the ID part
    if not owl_class and iri.startswith("http"):
        # Extract the ID from the full IRI - get the last part after the last '/'
        parts = iri.rstrip("/").split("/")
        if parts:
            id_part = parts[-1]
            owl_class = folio[id_part]

    # Strategy 3: If not found and this is just an ID, try with the FOLIO IRI prefix
    if not owl_class and not iri.startswith("http"):
        full_iri = f"https://folio.openlegalstandard.org/{iri}"
        owl_class = folio[full_iri]

    # Strategy 4: Try with just the ID part in the FOLIO dictionary directly
    if not owl_class:
        # One last attempt by checking all classes
        for cls in folio.classes:
            if hasattr(cls, "iri") and (cls.iri.endswith(iri) or iri.endswith(cls.iri)):
                owl_class = cls
                break

    if not owl_class:
        # Return empty template if class not found
        return request.app.state.templates.TemplateResponse(
            "components/class_details.html", {"request": request, "class_data": None}
        )

    # Prepare node data
    nodes, edges = get_node_neighbors(owl_class, folio)

    # Build parent list
    parents = []
    if hasattr(owl_class, "sub_class_of") and owl_class.sub_class_of:
        for parent_iri in owl_class.sub_class_of:
            parent = folio[parent_iri]
            if parent:
                parents.append(
                    {
                        "iri": parent.iri,
                        "label": parent.label or "Unnamed Class",
                        "definition": parent.definition or "No definition available",
                    }
                )

    # Build children list
    children = []
    if hasattr(owl_class, "parent_class_of") and owl_class.parent_class_of:
        for child_iri in owl_class.parent_class_of:
            child = folio[child_iri]
            if child:
                children.append(
                    {
                        "iri": child.iri,
                        "label": child.label or "Unnamed Class",
                        "definition": child.definition or "No definition available",
                    }
                )

    # Check if translations are available
    translations = {}
    if hasattr(owl_class, "translations") and owl_class.translations:
        translations = owl_class.translations

    class_data = {
        "iri": owl_class.iri,
        "label": owl_class.label or "Unnamed Class",
        "definition": owl_class.definition or "No definition available",
        "preferred_label": owl_class.preferred_label,
        "alternative_labels": owl_class.alternative_labels,
        "identifier": owl_class.identifier,
        "description": owl_class.description,
        "comment": owl_class.comment,
        "examples": owl_class.examples,
        "notes": owl_class.notes,
        "parents": parents,
        "children": children,
        "see_also": owl_class.see_also,
        "is_defined_by": owl_class.is_defined_by,
        "deprecated": owl_class.deprecated,
        "translations": translations,
        # Add the new fields
        "history_note": owl_class.history_note
        if hasattr(owl_class, "history_note")
        else None,
        "editorial_note": owl_class.editorial_note
        if hasattr(owl_class, "editorial_note")
        else None,
        "in_scheme": owl_class.in_scheme if hasattr(owl_class, "in_scheme") else None,
        "source": owl_class.source if hasattr(owl_class, "source") else None,
        "country": owl_class.country if hasattr(owl_class, "country") else None,
        "nodes": nodes,
        "edges": edges,
    }

    # Create a simplified version of folio_graph to pass to the template
    # This will allow the template to look up labels for "see also" IRIs
    simplified_folio_graph = {}

    # For each see_also item, try to get its label from the folio graph
    if hasattr(owl_class, "see_also") and owl_class.see_also:
        for see_also_iri in owl_class.see_also:
            if see_also_iri.startswith("http"):
                see_also_class = folio[see_also_iri]
                if see_also_class:
                    simplified_folio_graph[see_also_iri] = {
                        "label": see_also_class.label or see_also_iri,
                        "iri": see_also_iri,
                    }

    return request.app.state.templates.TemplateResponse(
        "components/class_details.html",
        {
            "request": request,
            "class_data": class_data,
            "folio_graph": simplified_folio_graph,
        },
    )


@router.get(
    "/tree",
    tags=["taxonomy"],
    response_model=None,
    summary="Interactive Taxonomy Tree Explorer",
    description="Explore the FOLIO taxonomy using an interactive tree view",
    status_code=status.HTTP_200_OK,
)
async def explore_taxonomy_tree(request: Request) -> Response:
    """
    Interactive taxonomic explorer using jsTree for navigation.

    This endpoint provides an interactive UI for exploring the FOLIO taxonomy hierarchy.
    The left panel shows a navigable tree view of all classes, while the right panel
    displays detailed information about the selected class.

    Features:
    - Lazy-loaded tree for efficient browsing of large hierarchies
    - Detailed class information in the right panel
    - Interactive visualization of class relationships
    - Search functionality

    Returns:
        Response: HTML page with the interactive taxonomy explorer
    """
    # Import JavaScript for tree view
    typeahead_js_path = (
        Path(__file__).parent.parent / "static" / "js" / "typeahead_search.js"
    )
    typeahead_js_source = typeahead_js_path.read_text(encoding="utf-8")

    return request.app.state.templates.TemplateResponse(
        "taxonomy/tree.html",
        {
            "request": request,
            "typeahead_js_source": typeahead_js_source,
            "config": request.app.state.config,
        },
    )


@router.get(
    "/browse",
    tags=["taxonomy"],
    response_model=None,
    summary="Browse Top-Level OWL Classes",
    description="Browse all top-level OWL classes in the ontology in a human-readable HTML format",
    status_code=status.HTTP_200_OK,
)
async def browse_top_level_classes(request: Request) -> Response:
    """
    Browse all top-level (root) classes from the FOLIO ontology in a rich HTML format.

    This endpoint returns an interactive HTML representation of the top-level classes in the
    ontology hierarchy, styled with Tailwind CSS for a modern, responsive design.

    Top-level classes are those that are direct subclasses of the OWL Thing class
    (http://www.w3.org/2002/07/owl#Thing).

    This view is ideal for:
    - Getting a visual overview of the ontology structure
    - Human-readable browsing of the ontology's top-level categories
    - Educational purposes and learning about FOLIO
    - Sharing ontology information with non-technical stakeholders

    HTTP Status Codes:
    - 200 OK: Successfully retrieved top-level classes in HTML format
    """
    folio: FOLIO = request.app.state.folio

    # OWL_THING URI from the FOLIO library
    OWL_THING = "http://www.w3.org/2002/07/owl#Thing"

    # Filter for classes that are direct subclasses of owl:Thing
    root_classes = []

    # Get all IRIs from the FOLIO instance
    for iri in FOLIO_TYPE_IRIS.values():
        owl_class = folio[iri]

        # Check if this class directly inherits from owl:Thing
        if hasattr(owl_class, "sub_class_of") and isinstance(
            owl_class.sub_class_of, list
        ):
            if (
                len(owl_class.sub_class_of) == 1
                and owl_class.sub_class_of[0] == OWL_THING
            ):
                root_classes.append(owl_class)

    # Import JavaScript for typeahead search
    typeahead_js_path = (
        Path(__file__).parent.parent / "static" / "js" / "typeahead_search.js"
    )
    typeahead_js_source = typeahead_js_path.read_text(encoding="utf-8")

    # Render template
    return request.app.state.templates.TemplateResponse(
        "taxonomy/browse.html",
        {
            "request": request,
            "root_classes": root_classes,
            "typeahead_js_source": typeahead_js_source,
            "config": request.app.state.config,
        },
    )
