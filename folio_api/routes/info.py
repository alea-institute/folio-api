"""
Info routes for the API.
"""

# imports

# packages
from fastapi import APIRouter, Request, status
from folio import FOLIO

# project
from folio_api.models import HealthResponse, FOLIOGraphInfo

# API router
router = APIRouter(prefix="/info", tags=["info"])


@router.get("/health", 
           tags=["info"], 
           response_model=HealthResponse, 
           summary="API Health Status",
           description="Provides health status of the API and information about the loaded FOLIO ontology",
           status_code=status.HTTP_200_OK,
           responses={
               status.HTTP_200_OK: {
                   "description": "API is healthy and operational",
                   "content": {
                       "application/json": {
                           "example": {
                               "status": "healthy",
                               "folio_graph": {
                                   "num_classes": 1025,
                                   "title": "FOLIO Ontology",
                                   "description": "Federated Open Legal Information Ontology",
                                   "source_type": "github",
                                   "http_url": None,
                                   "github_repo_owner": "alea-institute",
                                   "github_repo_name": "folio",
                                   "github_repo_branch": "2.0.0"
                               }
                           }
                       }
                   }
               },
               status.HTTP_503_SERVICE_UNAVAILABLE: {
                   "description": "API service is currently unavailable",
                   "content": {
                       "application/json": {
                           "example": {
                               "status": "unhealthy",
                               "folio_graph": None
                           }
                       }
                   }
               }
           })
async def health(request: Request) -> HealthResponse:
    """
    Check the health status of the API and retrieve information about the FOLIO ontology graph.
    
    This endpoint returns:
    - API status ("healthy" when operational)
    - FOLIO graph metadata (number of classes, title, description)
    - Graph source information (source type, repository details)
    
    Use this endpoint to:
    - Verify API availability
    - Check which version of the FOLIO ontology is being served
    - Get basic statistics about the loaded ontology graph
    
    HTTP Status Codes:
    - 200 OK: API is healthy and operational
    - 503 Service Unavailable: API service is currently unavailable (not implemented yet)
    
    Example response:
    ```json
    {
        "status": "healthy",
        "folio_graph": {
            "num_classes": 1025,
            "title": "FOLIO Ontology",
            "description": "Federated Open Legal Information Ontology",
            "source_type": "github",
            "http_url": null,
            "github_repo_owner": "alea-institute",
            "github_repo_name": "folio",
            "github_repo_branch": "2.0.0"
        }
    }
    ```
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
