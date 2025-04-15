"""
Root API routes for IRI resolution.
"""

# imports
import json

# packages
from fastapi import APIRouter, Request, status
from folio import FOLIO, OWLClass
from starlette.responses import JSONResponse, Response

from folio_api.templates.basic_html import render_tailwind_html

# project

# API router
router = APIRouter(prefix="", tags=["ontology"])


# redirect GET / to /docs
@router.get("/", 
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
                         "schema": {"type": "string", "example": "/docs"}
                     }
                 }
             }
         })
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
        status_code=status.HTTP_301_MOVED_PERMANENTLY, 
        headers={"Location": "/docs"}
    )


@router.get("/{iri}", 
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
                               "superClassOfIris": ["tBwJ5Vv1FxWdYC7hb3rCJcG"]
                           }
                       }
                   }
               },
               status.HTTP_404_NOT_FOUND: {
                   "description": "Class not found",
                   "content": {
                       "application/json": {
                           "example": {"message": "Class not found."}
                       }
                   }
               }
           })
async def get_class(request: Request, iri: str) -> OWLClass:
    """
    Retrieve detailed information about a FOLIO ontology class by its IRI identifier in JSON format.
    
    This endpoint returns comprehensive information about the requested class, including:
    - Label and definition
    - Parent and child classes
    - Properties and relationships
    - Additional metadata
    
    The IRI parameter is typically the unique identifier for the class, such as `R8pNPutX0TN6DlEqkyZuxSw`.
    
    Example URLs:
    - `/R8pNPutX0TN6DlEqkyZuxSw` - Returns the Lessor class
    
    Example response (partial):
    ```json
    {
      "iri": "R8pNPutX0TN6DlEqkyZuxSw",
      "label": "Lessor",
      "definition": "A party that grants a right to use something in return for payment.",
      "subClassOf": ["oS5FqyVBbOYQbhqb0G28oZR"],
      "superClassOfIris": ["tBwJ5Vv1FxWdYC7hb3rCJcG"],
      ...
    }
    ```
    
    HTTP Status Codes:
    - 200 OK: Successfully retrieved class information
    - 404 Not Found: The requested IRI does not exist in the ontology
    """
    folio: FOLIO = request.app.state.folio
    if iri not in folio:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, 
            content={"message": "Class not found."}
        )

    return folio[iri]


@router.get("/{iri}/markdown", 
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
                   }
               },
               status.HTTP_404_NOT_FOUND: {
                   "description": "Class not found",
                   "content": {
                       "text/plain": {
                           "example": "Class not found."
                       }
                   }
               }
           })
async def get_class_markdown(request: Request, iri: str) -> Response:
    """
    Retrieve information about a FOLIO ontology class by its IRI in Markdown format.
    
    This endpoint returns a Markdown representation of the requested class, suitable for:
    - Documentation
    - README files
    - GitHub or other markdown-compatible platforms
    
    The Markdown format includes headers, lists, and proper formatting of the class
    properties and relationships.
    
    Example URLs:
    - `/R8pNPutX0TN6DlEqkyZuxSw/markdown` - Returns the Lessor class in Markdown format
    
    HTTP Status Codes:
    - 200 OK: Successfully retrieved class information in Markdown format
    - 404 Not Found: The requested IRI does not exist in the ontology
    """
    folio: FOLIO = request.app.state.folio
    if iri not in folio:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND, 
            content="Class not found.",
            media_type="text/plain"
        )

    return Response(content=folio[iri].to_markdown(), media_type="text/markdown")


@router.get("/{iri}/jsonld", 
           tags=["ontology"], 
           response_model=None,
           summary="Get Class by IRI (JSON-LD)",
           description="Retrieves ontology class information by its IRI identifier in JSON-LD format")
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
    if iri not in folio:
        return JSONResponse(status_code=404, content={"message": "Class not found."})

    return JSONResponse(content=folio[iri].to_jsonld(), media_type="application/ld+json")


@router.get("/{iri}/xml", 
           tags=["ontology"], 
           response_model=None,
           summary="Get Class by IRI (OWL XML)",
           description="Retrieves ontology class information by its IRI identifier in OWL XML format")
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
    if iri not in folio:
        return Response(
            status_code=404, content=json.dumps({"message": "Class not found."})
        )

    return Response(content=folio[iri].to_owl_xml(), media_type="application/xml")


@router.get("/{iri}/html", 
           tags=["ontology"], 
           response_model=None,
           summary="Get Class by IRI (HTML)",
           description="Retrieves ontology class information by its IRI identifier in a human-readable HTML format")
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
    if iri not in folio:
        return Response(
            status_code=404, content=json.dumps({"message": "Class not found."})
        )

    return Response(
        content=render_tailwind_html(folio[iri], folio, request.app.state.config), media_type="text/html"
    )