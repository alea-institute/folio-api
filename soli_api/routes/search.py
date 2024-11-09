"""
Search routes.
"""

# imports

# packages
from fastapi import APIRouter, Request
from soli import SOLI

# project
from soli_api.models.owl import OWLClassList, OWLSearchResults

# API router
router = APIRouter(prefix="/search", tags=["search"])

# set min and max query length defaults
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 1024

# default depth
DEFAULT_MAX_DEPTH = 3


def query_length_check(query: str) -> bool:
    """
    Check if the query string is at least 2 characters long.

    Args:
        query (str): Query string

    Returns:
        bool: True if the query string is at least 2 characters long
    """
    return MIN_QUERY_LENGTH <= len(query) <= MAX_QUERY_LENGTH


@router.get("/prefix", tags=["search"], response_model=OWLClassList)
async def search_prefix(request: Request, query: str) -> OWLClassList:
    """
    Get class information for labels that start with the query string.

    Args:
        request (Request): FastAPI request object
        query (str): Query string

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLClassList(classes=soli.search_by_prefix(query))


@router.get("/label", tags=["search"], response_model=OWLSearchResults)
async def search_label(request: Request, query: str) -> OWLSearchResults:
    """
    Get class information using the soli-python search_by_label method.

    Args:
        request (Request): FastAPI request object
        query (str): Query string

    Returns:
        OWLSearchResults: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(results=soli.search_by_label(query))


@router.get("/definition", tags=["search"], response_model=OWLSearchResults)
async def search_definition(request: Request, query: str) -> OWLSearchResults:
    """
    Get class information using the soli-python search_by_definition method.

    Args:
        request (Request): FastAPI request object
        query (str): Query string

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(results=soli.search_by_definition(query))


@router.get("/llm/area-of-law", tags=["search"], response_model=OWLSearchResults)
async def search_llm_area_of_law(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI areas of law.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth of the search

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_areas_of_law(max_depth=max_depth)
        )
    )


@router.get("/llm/asset-types", tags=["search"], response_model=OWLSearchResults)
async def search_asset_types(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI asset types.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_asset_types(max_depth=max_depth)
        )
    )


# communication modalities
@router.get(
    "/llm/communication-modalities", tags=["search"], response_model=OWLSearchResults
)
async def search_communication_modalities(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI communication modalities.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query,
            search_set=soli.get_communication_modalities(max_depth=max_depth),
        )
    )


# get currencies
@router.get("/llm/currencies", tags=["search"], response_model=OWLSearchResults)
async def search_currencies(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI currencies.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_currencies(max_depth=max_depth)
        )
    )


# data formats
@router.get("/llm/data-formats", tags=["search"], response_model=OWLSearchResults)
async def search_data_formats(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI data formats.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_data_formats(max_depth=max_depth)
        )
    )


# document artifacts
@router.get("/llm/document-artifacts", tags=["search"], response_model=OWLSearchResults)
async def search_document_artifacts(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI document artifacts.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_document_artifacts(max_depth=max_depth)
        )
    )


# engagement terms
@router.get("/llm/engagement-terms", tags=["search"], response_model=OWLSearchResults)
async def search_engagement_terms(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI engagement terms.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_engagement_terms(max_depth=max_depth)
        )
    )


# events
@router.get("/llm/events", tags=["search"], response_model=OWLSearchResults)
async def search_events(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI events.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_events(max_depth=max_depth)
        )
    )


# governmental bodies
@router.get(
    "/llm/governmental-bodies", tags=["search"], response_model=OWLSearchResults
)
async def search_governmental_bodies(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI governmental bodies.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_governmental_bodies(max_depth=max_depth)
        )
    )


# industries
@router.get("/llm/industries", tags=["search"], response_model=OWLSearchResults)
async def search_industries(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI industries.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_industries(max_depth=max_depth)
        )
    )


# legal authorities
@router.get("/llm/legal-authorities", tags=["search"], response_model=OWLSearchResults)
async def search_legal_authorities(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI legal authorities.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_legal_authorities(max_depth=max_depth)
        )
    )


# locations
@router.get("/llm/locations", tags=["search"], response_model=OWLSearchResults)
async def search_locations(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI locations.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_locations(max_depth=max_depth)
        )
    )


# matter narratives
@router.get("/llm/matter-narratives", tags=["search"], response_model=OWLSearchResults)
async def search_matter_narratives(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI matter narratives.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_matter_narratives(max_depth=max_depth)
        )
    )


# matter narrative formats
@router.get(
    "/llm/matter-narrative-formats", tags=["search"], response_model=OWLSearchResults
)
async def search_matter_narrative_formats(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI matter narrative formats.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query,
            search_set=soli.get_matter_narrative_formats(max_depth=max_depth),
        )
    )


# objectives
@router.get("/llm/objectives", tags=["search"], response_model=OWLSearchResults)
async def search_objectives(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI objectives.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_objectives(max_depth=max_depth)
        )
    )


@router.get("/llm/player-actors", tags=["search"], response_model=OWLSearchResults)
async def search_player_actors(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI player actors.

    Args:
        request (Request): FastAPI request object
        query (str): Query string
        max_depth (int): Maximum depth

    Returns:
        OWLClassList: Pydantic model with list of classes
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_player_actors(max_depth=max_depth)
        )
    )


# standards compatibilities
@router.get(
    "/llm/standards-compatibilities", tags=["search"], response_model=OWLSearchResults
)
async def search_standards_compatibilities(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI standards compatibilities.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query,
            search_set=soli.get_standards_compatibilities(max_depth=max_depth),
        )
    )


# statuses
@router.get("/llm/statuses", tags=["search"], response_model=OWLSearchResults)
async def search_statuses(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI statuses.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_statuses(max_depth=max_depth)
        )
    )


# system identifiers
@router.get("/llm/system-identifiers", tags=["search"], response_model=OWLSearchResults)
async def search_system_identifiers(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the SOLI system identifiers.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    soli: SOLI = request.app.state.soli
    return OWLSearchResults(
        results=await soli.search_by_llm(
            query=query, search_set=soli.get_system_identifiers(max_depth=max_depth)
        )
    )
