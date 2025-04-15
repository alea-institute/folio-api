"""
Taxonomy routes for the FOLIO API.
"""

# imports
from pathlib import Path

# packages
from fastapi import APIRouter, Request, status
from folio import FOLIO, FOLIO_TYPE_IRIS
from starlette.responses import Response

# project
from folio_api.models import OWLClassList

# API router
router = APIRouter(
    prefix="/taxonomy", 
    tags=["taxonomy"]
)


@router.get("/actor_player", 
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
                                       "definition": "An entity recognized by the legal system as having legal rights and obligations."
                                   },
                                   {
                                       "iri": "7bN3mK6jH5gF1dS4aP8oI7u",
                                       "label": "Natural Person",
                                       "definition": "A human being, as distinguished from a legal entity created by law."
                                   }
                               ]
                           }
                       }
                   }
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
                                       "type": "type_error.integer"
                                   }
                               ]
                           }
                       }
                   }
               }
           })
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


@router.get("/area_of_law", 
           tags=["taxonomy"], 
           response_model=OWLClassList,
           summary="Get Area of Law Classes",
           description="Retrieve all Area of Law classes from the FOLIO ontology with optional traversal depth")
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
    return OWLClassList(classes=folio.get_standards_compatibilities(max_depth=max_depth))


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


@router.get("/browse", 
          tags=["taxonomy"], 
          response_model=None,
          summary="Browse Top-Level OWL Classes",
          description="Browse all top-level OWL classes in the ontology in a human-readable HTML format",
          status_code=status.HTTP_200_OK)
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
        if hasattr(owl_class, "sub_class_of") and isinstance(owl_class.sub_class_of, list):
            if len(owl_class.sub_class_of) == 1 and owl_class.sub_class_of[0] == OWL_THING:
                root_classes.append(owl_class)
                
    # Import JavaScript for typeahead search
    typeahead_js_path = Path(__file__).parent.parent / "templates" / "typeahead_search.js"
    typeahead_js_source = typeahead_js_path.read_text(encoding="utf-8")
    
    # Generate HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FOLIO Top-Level Classes</title>
        <script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js" integrity="sha512-v2CJ7UaYy4JwqLDIrZUI/4hqeoQieOmAZNXBeQyjo21dadnwR+8ZaIJVT8EE2iyI61OV8e6M8PP2/4hpQINQ/g==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/typeahead.js/0.11.1/typeahead.bundle.min.js" integrity="sha512-qOBWNAMfkz+vXXgbh0Wz7qYSLZp6c14R0bZeVX2TdQxWpuKr6yHjBIM69fcF8Ve4GUX6B6AKRQJqiiAmwvmUmQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <style type="text/css">
            @import url('https://fonts.googleapis.com/css2?family=Public+Sans:ital,wght@0,100..900;1,100..900&display=swap');
            :root {{
                --font-sans: 'Public Sans Variable';
                --font-serif: 'Public Sans Variable';
                --font-heading: 'Public Sans Variable';
                --color-primary: rgb(24 70 120);
                --color-secondary: rgb(134, 147, 171);
                --color-accent: rgb(234, 82, 111);
                --color-text-heading: rgb(0 0 0);
                --color-text-default: rgb(16 16 16);
                --color-text-muted: rgb(16 16 16 / 66%);
                --color-bg-page: rgb(255 255 255);
                --color-bg-page-dark: rgb(12 35 60);
            }}

            .dark {{
                --color-primary: rgb(24 70 120);
                --color-secondary: rgb(134 147 171);
                --color-accent: rgb(234 82 111);
                --color-text-heading: rgb(247 248 248);
                --color-text-default: rgb(229 236 246);
                --color-text-muted: rgba(229, 236, 246, 0.66);
                --color-bg-page: rgb(12 35 60);
            }}
            .dark ::selection {{
                background-color: black;
                color: snow;
            }}

            .twitter-typeahead {{
                width: 100%;
            }}
            .tt-menu {{
                width: 100%;
                margin-top: 0.5rem;
                background-color: white;
                border: 1px solid var(--color-secondary);
                border-radius: 0.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }}
            .tt-suggestion {{
                padding: 0.75rem 1rem;
                cursor: pointer;
            }}
            .tt-suggestion:hover, .tt-suggestion.tt-cursor {{
                background-color: rgba(24, 70, 120, 0.1);
            }}
        </style>
    </head>
    <body class="font-['Public_Sans'] bg-gray-100 min-h-screen">
        <header class="bg-[--color-primary] py-6 text-white">
            <div class="container mx-auto px-4">
                <div class="flex justify-between items-start">
                    <div>
                        <h1 class="text-3xl font-bold mb-2">FOLIO Top-Level Classes</h1>
                        <p class="text-xl text-white opacity-80">Browse the highest level categories in the FOLIO ontology hierarchy</p>
                    </div>
                    <div class="hidden md:block">
                        <a href="https://openlegalstandard.org/" target="_blank" class="inline-block bg-white text-[--color-primary] font-semibold px-4 py-2 rounded hover:bg-opacity-90 transition-colors duration-200 mr-2">FOLIO Website</a>
                        <a href="https://openlegalstandard.org/education/" target="_blank" class="inline-block bg-transparent text-white border border-white font-semibold px-4 py-2 rounded hover:bg-white hover:bg-opacity-10 transition-colors duration-200">Learn More</a>
                    </div>
                </div>
                
                <div class="mt-6 max-w-3xl">
                    <p class="mb-3 text-white text-opacity-90">FOLIO is an open standard for legal concepts and knowledge.</p>
                    <div class="relative">
                        <input id="search-input" type="text" placeholder="Search for FOLIO classes..." class="w-full p-3 rounded-lg border border-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50 text-gray-800">
                        <div id="search-results" class="absolute top-14 left-0 w-full bg-white dark:bg-[--color-bg-page] shadow-lg rounded-lg overflow-hidden mt-2 border border-[--color-secondary] border-opacity-20"></div>
                    </div>
                </div>
            </div>
        </header>
        
        <div class="bg-white border-b">
            <div class="container mx-auto px-4 py-6">
                <div class="flex flex-col md:flex-row gap-6">
                    <div class="flex-1">
                        <h2 class="text-xl font-bold text-[--color-primary] mb-2">About FOLIO</h2>
                        <p class="text-gray-700 mb-2">FOLIO is an open standard for legal concepts and knowledge, designed to make legal information more accessible and interoperable.</p>
                        <p class="text-gray-700">Explore the <a href="https://openlegalstandard.org/resources/folio-python-library/" class="text-blue-600 hover:underline">FOLIO Python Library</a> to integrate FOLIO ontology into your applications.</p>
                    </div>
                    <div class="flex-1">
                        <h2 class="text-xl font-bold text-[--color-primary] mb-2">Resources</h2>
                        <ul class="list-disc list-inside text-gray-700 space-y-1">
                            <li><a href="https://openlegalstandard.org/" class="text-blue-600 hover:underline">Official FOLIO Website</a></li>
                            <li><a href="https://openlegalstandard.org/education/" class="text-blue-600 hover:underline">FOLIO Education Resources</a></li>
                            <li><a href="https://openlegalstandard.org/resources/folio-python-library/" class="text-blue-600 hover:underline">FOLIO Python Library Documentation</a></li>
                            <li><a href="https://github.com/alea-institute/folio-api" class="text-blue-600 hover:underline">FOLIO API on GitHub</a></li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <main class="container mx-auto px-4 py-8">
            <p class="mb-6 text-gray-600">These classes are direct subclasses of owl:Thing and represent the highest level categories in the FOLIO ontology.</p>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-fr">
                {
                    ''.join([f'''
                        <div class="bg-white rounded-lg shadow p-8 flex flex-col h-full min-h-56">
                            <h2 class="text-xl font-semibold mb-2 text-[--color-primary]">
                                <a href="{owl_class.iri}">{owl_class.label or "Unnamed Class"}</a>
                            </h2>
                            <p class="text-gray-500 text-sm mb-2 truncate" title="{owl_class.iri}">IRI: {owl_class.iri}</p>
                            <div class="flex-grow mb-4">
                                <p class="text-gray-700 line-clamp-3" title="{owl_class.definition or 'No definition available'}">{owl_class.definition or "No definition available"}</p>
                            </div>
                            <div class="flex justify-between items-center mt-auto">
                                <span class="text-xs text-gray-500">{len(owl_class.parent_class_of) if hasattr(owl_class, 'parent_class_of') else 0} subclasses</span>
                                <a href="{owl_class.iri}/html" class="text-blue-500 text-sm font-medium">View details →</a>
                            </div>
                        </div>
                    ''' for owl_class in root_classes])
                }
            </div>
        </main>
        
        <footer class="bg-[--color-primary] text-white py-8 mt-8">
            <div class="container mx-auto px-4 text-center">
                <a href="https://openlegalstandard.org/" target="_blank"><img src="https://openlegalstandard.org/_astro/soli-2x1-accent.DYUFAzgH_1CFhgX.webp" alt="FOLIO Logo" class="w-16 mx-auto mt-4"></a>
                <p>The FOLIO ontology is licensed under the CC-BY 4.0 license.</p>
                <p>Any FOLIO software is licensed under the MIT license.</p>
                
                <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl mx-auto">
                    <div class="text-left">
                        <h3 class="font-bold text-lg mb-2">FOLIO Resources</h3>
                        <ul class="space-y-2">
                            <li><a href="https://openlegalstandard.org/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO Official Website</a></li>
                            <li><a href="https://openlegalstandard.org/education/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO Education</a></li>
                            <li><a href="https://openlegalstandard.org/resources/folio-python-library/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO Python Library</a></li>
                            <li><a href="https://github.com/alea-institute/folio-api" class="text-[--color-secondary] hover:text-white transition-colors duration-200">FOLIO API (GitHub)</a></li>
                        </ul>
                    </div>
                    <div class="text-left">
                        <h3 class="font-bold text-lg mb-2">About FOLIO</h3>
                        <p class="text-sm mb-2">FOLIO is an open standard for legal concepts and knowledge, designed to make legal information more accessible and interoperable.</p>
                        <p class="text-sm">Learn more about how FOLIO is being used to improve legal technology and access to justice by visiting the <a href="https://openlegalstandard.org/" class="text-[--color-secondary] hover:text-white transition-colors duration-200">Open Legal Standard website</a>.</p>
                    </div>
                </div>
                
                <p class="mt-4 text-small">Copyright &copy; 2024-2025. <a href="https://aleainstitute.ai/" target="_blank">The Institute for the Advancement of Legal and Ethical AI</a>.</p>
                <p class="mt-2 text-xs">FOLIO Version: <span class="font-mono">{request.app.state.config["folio"]["branch"]}</span> | Repository: <a href="https://github.com/{request.app.state.config["folio"]["repository"]}" class="text-[--color-secondary] hover:text-white transition-colors duration-200">{request.app.state.config["folio"]["repository"]}</a></p>
            </div>
        </footer>
        
        <script>
            {typeahead_js_source}
        </script>
    </body>
    </html>
    """
    
    return Response(content=html_content, media_type="text/html")