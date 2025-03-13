"""
Info routes for the API.
"""

# imports

# packages
from fastapi import APIRouter, Request
from folio import FOLIO

# project
from folio_api.models.health import HealthResponse, FOLIOGraphInfo

# API router
router = APIRouter(prefix="/info", tags=["info"])


@router.get("/health", tags=["info"], response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """
    Health check endpoint to check the status of the API.

    Args:
        request (Request): FastAPI request object

    Returns:
        HealthResponse: Pydantic model with health status and FOLIO graph information
    """
    folio: FOLIO = request.app.state.folio
    return HealthResponse(
        status="healthy",
        folio_graph=FOLIOGraphInfo(
            num_classes=len(folio),
            title=folio.title,
            description=folio.description,
            source_type=folio.source_type,
            http_url=folio.http_url,
            github_repo_owner=folio.github_repo_owner,
            github_repo_name=folio.github_repo_name,
            github_repo_branch=folio.github_repo_branch,
        ),
    )
