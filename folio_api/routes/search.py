"""
Search routes.
"""

# imports

# packages
from fastapi import APIRouter, Request, HTTPException, status
from folio import FOLIO

# project
from folio_api.models import OWLClassList, OWLSearchResults

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


@router.get(
    "/prefix",
    tags=["search"],
    response_model=OWLClassList,
    summary="Search by Label Prefix or Substring",
    description="Find ontology classes whose labels start with or contain the given query string",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "description": "Successfully retrieved matching classes",
            "content": {
                "application/json": {
                    "example": {
                        "classes": [
                            {
                                "iri": "8H5wUAUQ0N9s4hHaF2cNO8k",
                                "label": "Contract",
                                "definition": "A legally binding agreement between two or more parties.",
                            }
                        ]
                    }
                }
            },
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid query parameter",
            "content": {
                "application/json": {
                    "example": {"detail": "Query must be between 2 and 1024 characters"}
                }
            },
        },
    },
)
async def search_prefix(request: Request, query: str) -> OWLClassList:
    """
    Search for FOLIO ontology classes whose labels start with or contain the provided search string.

    This endpoint performs a prefix-based and substring search on class labels, returning all classes
    whose labels either begin with or contain the provided query string. The search is case-insensitive.

    This is useful for:
    - Autocomplete suggestions in user interfaces
    - Finding classes with similar naming conventions
    - Exploring related concepts in the ontology

    Example queries:
    - `Contract` would match "Contract", "Contractual Agreement", "Contract Breach", etc.
    - `Agr` would match "Agreement", "Agricultural Land", etc.
    - `law` would match "Law", "Lawyer", but also "Criminal Law", "Contract Law", etc.

    Requirements:
    - Query must be at least 2 characters long (limited to 1024 characters)
    - An HTTP 400 error is returned if query length requirements are not met
    - A successful response with an empty array is returned if no matches are found

    Example response:
    ```json
    {
      "classes": [
        {
          "iri": "8H5wUAUQ0N9s4hHaF2cNO8k",
          "label": "Contract",
          "definition": "A legally binding agreement between two or more parties.",
          ...
        },
        {...}
      ]
    }
    ```
    """
    # check query length
    if len(query) < MIN_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query must be at least {MIN_QUERY_LENGTH} characters long",
        )
    if len(query) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters",
        )

    folio: FOLIO = request.app.state.folio

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

    # Then get label matches that aren't already in prefix results
    label_results = []

    # Combine prefix results with deduplication
    prefix_results = []
    seen_iris = set()

    # Add results in order of priority but avoid duplicates
    for result_list in [
        prefix_results_original,
        prefix_results_lower,
        prefix_results_title,
    ]:
        for owl_class in result_list:
            if owl_class.iri not in seen_iris:
                seen_iris.add(owl_class.iri)
                prefix_results.append(owl_class)

    # Check all classes for substring matches
    # In the FOLIO library, classes is a list of OWLClass objects
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
            label_results.append(owl_class)

    # Combine results, with prefix matches first
    results = prefix_results + label_results

    # Return 200 OK with results (empty array if no matches)
    return OWLClassList(classes=results)


@router.get(
    "/label",
    tags=["search"],
    response_model=OWLSearchResults,
    summary="Search by Label Content",
    description="Find ontology classes whose labels contain the given query string, with relevance scores",
)
async def search_label(request: Request, query: str) -> OWLSearchResults:
    """
    Search for FOLIO ontology classes whose labels contain the provided query string.

    This endpoint performs a fuzzy search on class labels, returning classes with labels
    that contain the query string along with a relevance score. Unlike the prefix search,
    this searches for the query string anywhere in the label, not just at the beginning.

    This is useful for:
    - Finding classes when you know part of the label but not the beginning
    - More flexible searching when the exact term is unknown
    - Getting results ranked by relevance

    Example queries:
    - `agreement` would match "Lease Agreement", "Purchase Agreement", etc.
    - `party` would match "Third Party", "Party to Contract", "Political Party", etc.

    Requirements:
    - Query must be at least 2 characters long (limited to 1024 characters)
    - Returns an empty list if no matches are found or query is too short/long

    Example response:
    ```json
    {
      "results": [
        [
          {
            "iri": "8H5wUAUQ0N9s4hHaF2cNO8k",
            "label": "Contractual Agreement",
            "definition": "A legally binding agreement between two or more parties.",
            ...
          },
          0.95  // Relevance score
        ],
        [...]
      ]
    }
    ```

    Note: The results are returned as a list of tuples, each containing an OWLClass object
    and a numeric relevance score between 0 and 1, with higher scores indicating better matches.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(results=folio.search_by_label(query))


@router.get(
    "/definition",
    tags=["search"],
    response_model=OWLSearchResults,
    summary="Search by Definition Content",
    description="Find ontology classes whose definitions contain the given query string, with relevance scores",
)
async def search_definition(request: Request, query: str) -> OWLSearchResults:
    """
    Search for FOLIO ontology classes whose definitions contain the provided query string.

    This endpoint performs a text search on class definitions, returning classes with definitions
    that contain the query string along with a relevance score. This allows you to find concepts
    based on their meaning rather than just their labels.

    This is useful for:
    - Finding classes based on conceptual meaning
    - Exploring concepts related to specific terms or ideas
    - Research and discovery of related legal concepts

    Example queries:
    - `property` would match classes with definitions mentioning property concepts
    - `obligation` would match classes related to duties, requirements, or obligations

    Requirements:
    - Query must be at least 2 characters long (limited to 1024 characters)
    - Returns an empty list if no matches are found or query is too short/long

    Example response:
    ```json
    {
      "results": [
        [
          {
            "iri": "rTn1gH6J3mLpOqZxS0uW9vY",
            "label": "Real Property",
            "definition": "Land and anything fixed, immovable, or permanently attached to it.",
            ...
          },
          0.88  // Relevance score
        ],
        [...]
      ]
    }
    ```

    Note: The results are returned as a list of tuples, each containing an OWLClass object
    and a numeric relevance score between 0 and 1, with higher scores indicating better matches.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(results=folio.search_by_definition(query))


@router.get(
    "/llm/area-of-law",
    tags=["search"],
    response_model=OWLSearchResults,
    summary="AI-Powered Area of Law Search",
    description="Use LLM-based semantic search to find areas of law related to your query",
)
async def search_llm_area_of_law(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Search for areas of law in the FOLIO ontology using AI-powered semantic search.

    This endpoint uses a Large Language Model (LLM) to perform semantic search against
    the Areas of Law in the FOLIO ontology. Unlike traditional keyword search, this can
    understand the meaning and intent behind your query, even if it doesn't match the
    exact words used in class labels or definitions.

    This is useful for:
    - Finding relevant legal domains for specific legal questions
    - Exploring which areas of law might apply to a particular scenario
    - Discovering connections between legal concepts and practice areas

    Parameters:
    - query: A natural language description of what you're looking for
    - max_depth: Controls how many levels deep in the taxonomy to search (default: 3)

    Example queries:
    - "I'm having issues with my landlord not fixing things"
    - "My business partner is using company funds for personal expenses"
    - "Can I use copyrighted material in my educational presentations?"

    Requirements:
    - Query must be at least 2 characters long (limited to 1024 characters)
    - Returns an empty list if no matches are found or query is too short/long

    Example response:
    ```json
    {
      "results": [
        [
          {
            "iri": "uY5tR1zX9vB7nM3kL7jH5gF",
            "label": "Landlord-Tenant Law",
            "definition": "Body of law that governs rental properties and agreements.",
            ...
          },
          0.92  // Relevance score
        ],
        [...]
      ]
    }
    ```

    Note: LLM-based search may take slightly longer than traditional keyword search
    but provides more semantically meaningful results.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_areas_of_law(max_depth=max_depth)
        )
    )


@router.get("/llm/asset-types", tags=["search"], response_model=OWLSearchResults)
async def search_asset_types(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO asset types.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_asset_types(max_depth=max_depth)
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
    Get class information using the FOLIO communication modalities.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query,
            search_set=folio.get_communication_modalities(max_depth=max_depth),
        )
    )


# get currencies
@router.get("/llm/currencies", tags=["search"], response_model=OWLSearchResults)
async def search_currencies(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO currencies.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_currencies(max_depth=max_depth)
        )
    )


# data formats
@router.get("/llm/data-formats", tags=["search"], response_model=OWLSearchResults)
async def search_data_formats(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO data formats.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_data_formats(max_depth=max_depth)
        )
    )


# document artifacts
@router.get("/llm/document-artifacts", tags=["search"], response_model=OWLSearchResults)
async def search_document_artifacts(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO document artifacts.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_document_artifacts(max_depth=max_depth)
        )
    )


# engagement terms
@router.get("/llm/engagement-terms", tags=["search"], response_model=OWLSearchResults)
async def search_engagement_terms(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO engagement terms.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_engagement_terms(max_depth=max_depth)
        )
    )


# events
@router.get("/llm/events", tags=["search"], response_model=OWLSearchResults)
async def search_events(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO events.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_events(max_depth=max_depth)
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
    Get class information using the FOLIO governmental bodies.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_governmental_bodies(max_depth=max_depth)
        )
    )


# industries
@router.get("/llm/industries", tags=["search"], response_model=OWLSearchResults)
async def search_industries(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO industries.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_industries(max_depth=max_depth)
        )
    )


# legal authorities
@router.get("/llm/legal-authorities", tags=["search"], response_model=OWLSearchResults)
async def search_legal_authorities(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO legal authorities.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_legal_authorities(max_depth=max_depth)
        )
    )


# locations
@router.get("/llm/locations", tags=["search"], response_model=OWLSearchResults)
async def search_locations(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO locations.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_locations(max_depth=max_depth)
        )
    )


# matter narratives
@router.get("/llm/matter-narratives", tags=["search"], response_model=OWLSearchResults)
async def search_matter_narratives(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO matter narratives.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_matter_narratives(max_depth=max_depth)
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
    Get class information using the FOLIO matter narrative formats.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query,
            search_set=folio.get_matter_narrative_formats(max_depth=max_depth),
        )
    )


# objectives
@router.get("/llm/objectives", tags=["search"], response_model=OWLSearchResults)
async def search_objectives(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO objectives.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_objectives(max_depth=max_depth)
        )
    )


@router.get("/llm/player-actors", tags=["search"], response_model=OWLSearchResults)
async def search_player_actors(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO player actors.

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

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_player_actors(max_depth=max_depth)
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
    Get class information using the FOLIO standards compatibilities.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query,
            search_set=folio.get_standards_compatibilities(max_depth=max_depth),
        )
    )


# statuses
@router.get("/llm/statuses", tags=["search"], response_model=OWLSearchResults)
async def search_statuses(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO statuses.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_statuses(max_depth=max_depth)
        )
    )


# system identifiers
@router.get("/llm/system-identifiers", tags=["search"], response_model=OWLSearchResults)
async def search_system_identifiers(
    request: Request, query: str, max_depth: int = DEFAULT_MAX_DEPTH
) -> OWLSearchResults:
    """
    Get class information using the FOLIO system identifiers.
    """
    # check query length
    if not query_length_check(query):
        return OWLClassList(classes=[])

    folio: FOLIO = request.app.state.folio
    return OWLSearchResults(
        results=await folio.search_by_llm(
            query=query, search_set=folio.get_system_identifiers(max_depth=max_depth)
        )
    )
