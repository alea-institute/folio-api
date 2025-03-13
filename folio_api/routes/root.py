"""
Root API routes for IRI resolution.
"""

# imports
import json

# packages
from fastapi import APIRouter, Request
from folio import FOLIO, OWLClass
from starlette.responses import JSONResponse, Response

from folio_api.templates.basic_html import render_tailwind_html

# project


# API router
router = APIRouter(prefix="", tags=[])


# redirect GET / to /docs
@router.get("/", tags=[])
async def root_redirect() -> Response:
    """
    Redirect to API documentation.

    Returns:
        Response: Redirect to API documentation
    """
    return Response(status_code=301, headers={"Location": "/docs"})


@router.get("/{iri}", tags=[], response_model=OWLClass or JSONResponse)
async def get_class(request: Request, iri: str) -> OWLClass or JSONResponse:
    """
    Get class information in JSON format by IRI.

    Args:
        request (Request): FastAPI request object
        iri (str): IRI of the class
        response_format (str): Response format

    Returns:
        OWLClass: Pydantic model with class information
    """
    folio: FOLIO = request.app.state.folio
    if iri not in folio:
        return JSONResponse(status_code=404, content={"message": "Class not found."})

    return folio[iri]


# add /{iri}/markdown with Response format and .to_markdown()
@router.get("/{iri}/markdown", tags=[], response_model=None)
async def get_class_markdown(request: Request, iri: str) -> Response:
    """
    Get class information in Markdown format by IRI.

    Args:
        request (Request): FastAPI request object
        iri (str): IRI of the class

    Returns:
        str: Markdown formatted class information
    """
    folio: FOLIO = request.app.state.folio
    if iri not in folio:
        return Response(status_code=404, content="Class not found.")

    return Response(content=folio[iri].to_markdown(), media_type="text/markdown")


@router.get("/{iri}/jsonld", tags=[], response_model=None)
async def get_class_jsonld(request: Request, iri: str) -> JSONResponse:
    """
    Get class information in JSON-LD format by IRI.

    Args:
        request (Request): FastAPI request object
        iri (str): IRI of the class

    Returns:
        JSONResponse: JSON-LD formatted class information
    """

    folio: FOLIO = request.app.state.folio
    if iri not in folio:
        return JSONResponse(status_code=404, content={"message": "Class not found."})

    return JSONResponse(content=folio[iri].to_jsonld(), media_type="application/ld+json")


@router.get("/{iri}/xml", tags=[], response_model=None)
async def get_class_xml(request: Request, iri: str) -> Response:
    """
    Get class information in XML format by IRI.

    Args:
        request (Request): FastAPI request object
        iri (str): IRI of the class

    Returns:
        Response: XML formatted class information
    """

    folio: FOLIO = request.app.state.folio
    if iri not in folio:
        return Response(
            status_code=404, content=json.dumps({"message": "Class not found."})
        )

    return Response(content=folio[iri].to_owl_xml(), media_type="application/xml")


@router.get("/{iri}/html", tags=[], response_model=None)
async def get_class_html(request: Request, iri: str) -> Response:
    """
    Get class information in HTML format by IRI.

    Args:
        request (Request): FastAPI request object
        iri (str): IRI of the class

    Returns:
        Response: HTML formatted class information
    """

    folio: FOLIO = request.app.state.folio
    if iri not in folio:
        return Response(
            status_code=404, content=json.dumps({"message": "Class not found."})
        )

    return Response(
        content=render_tailwind_html(folio[iri], folio), media_type="text/html"
    )
