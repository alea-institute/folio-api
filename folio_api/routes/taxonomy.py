"""
Taxonomy routes for the FOLIO API.
"""

# imports

# packages
from fastapi import APIRouter, Request
from folio import FOLIO

# project
from folio_api.models.owl import OWLClassList

# API router
router = APIRouter(prefix="/taxonomy", tags=["graph"])


@router.get("/actor_player", tags=["graph"], response_model=OWLClassList)
async def get_actor_player(request: Request, max_depth: int = 1) -> OWLClassList:
    """
    Get all classes of type Actor Player.

    Args:
        request (Request): FastAPI request object
        max_depth (int): Maximum depth to traverse the graph

    Returns:
        OWLClassList: Pydantic model with list of OWLClass objects
    """
    folio: FOLIO = request.app.state.folio
    return OWLClassList(classes=folio.get_player_actors(max_depth=max_depth))


@router.get("/area_of_law", tags=["graph"], response_model=OWLClassList)
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


@router.get("/asset_type", tags=["graph"], response_model=OWLClassList)
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


@router.get("/communication_modality", tags=["graph"], response_model=OWLClassList)
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


@router.get("/currency", tags=["graph"], response_model=OWLClassList)
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


@router.get("/data_format", tags=["graph"], response_model=OWLClassList)
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


@router.get("/document_artifact", tags=["graph"], response_model=OWLClassList)
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


@router.get("/engagement_terms", tags=["graph"], response_model=OWLClassList)
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


@router.get("/event", tags=["graph"], response_model=OWLClassList)
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


@router.get("/forums_venues", tags=["graph"], response_model=OWLClassList)
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


@router.get("/governmental_body", tags=["graph"], response_model=OWLClassList)
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


@router.get("/industry", tags=["graph"], response_model=OWLClassList)
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


@router.get("/language", tags=["graph"], response_model=OWLClassList)
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


@router.get("/legal_authorities", tags=["graph"], response_model=OWLClassList)
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


@router.get("/legal_entity", tags=["graph"], response_model=OWLClassList)
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


@router.get("/location", tags=["graph"], response_model=OWLClassList)
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


@router.get("/matter_narrative", tags=["graph"], response_model=OWLClassList)
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


@router.get("/matter_narrative_format", tags=["graph"], response_model=OWLClassList)
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


@router.get("/objectives", tags=["graph"], response_model=OWLClassList)
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


@router.get("/service", tags=["graph"], response_model=OWLClassList)
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


@router.get("/standards_compatibility", tags=["graph"], response_model=OWLClassList)
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
    return OWLClassList(classes=folio.get_standards_compatibilities(max_depth=max_depth))


@router.get("/status", tags=["graph"], response_model=OWLClassList)
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


@router.get("/system_identifiers", tags=["graph"], response_model=OWLClassList)
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
