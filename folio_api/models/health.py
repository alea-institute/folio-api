"""
Models for the health check endpoint.

These models define the response schemas for the health endpoints
that provide information about the API status and the loaded FOLIO ontology.
"""

# Standard library imports
from typing import Optional, Literal

# Third-party imports
from pydantic import BaseModel, Field, HttpUrl


class FOLIOGraphInfo(BaseModel):
    """
    Information about the loaded FOLIO ontology graph.
    
    This model contains metadata about the FOLIO ontology graph that is currently
    loaded in the API, including its size, source, and descriptive information.
    
    Attributes:
        num_classes: Total number of ontology classes in the graph
        title: Title of the FOLIO ontology
        description: Description of the FOLIO ontology
        source_type: Source type of the ontology (http or github)
        http_url: HTTP URL of the ontology source (when source_type is 'http')
        github_repo_owner: GitHub repository owner (when source_type is 'github')
        github_repo_name: GitHub repository name (when source_type is 'github')
        github_repo_branch: GitHub repository branch (when source_type is 'github')
    
    Example:
        ```json
        {
          "num_classes": 1025,
          "title": "FOLIO Ontology",
          "description": "Federated Open Legal Information Ontology",
          "source_type": "github",
          "http_url": null,
          "github_repo_owner": "alea-institute",
          "github_repo_name": "folio",
          "github_repo_branch": "2.0.0"
        }
        ```
    """
    num_classes: int = Field(
        description="Total number of ontology classes in the graph",
        example=1025,
        gt=0
    )
    
    title: str = Field(
        description="Title of the FOLIO ontology",
        example="FOLIO Ontology"
    )
    
    description: str = Field(
        description="Description of the FOLIO ontology",
        example="Federated Open Legal Information Ontology"
    )
    
    source_type: Literal["http", "github"] = Field(
        description="Source type of the ontology (http or github)",
        example="github"
    )
    
    http_url: Optional[HttpUrl] = Field(
        description="HTTP URL of the ontology source (when source_type is 'http')",
        example=None,
        default=None
    )
    
    github_repo_owner: Optional[str] = Field(
        description="GitHub repository owner (when source_type is 'github')",
        example="alea-institute",
        default=None
    )
    
    github_repo_name: Optional[str] = Field(
        description="GitHub repository name (when source_type is 'github')",
        example="folio",
        default=None
    )
    
    github_repo_branch: Optional[str] = Field(
        description="GitHub repository branch (when source_type is 'github')",
        example="2.0.0",
        default=None
    )


class HealthResponse(BaseModel):
    """
    Response model for the health check endpoint.
    
    This model contains information about the API's health status and
    metadata about the loaded FOLIO ontology graph.
    
    Attributes:
        status: Health status of the API ("healthy" when operational)
        folio_graph: Information about the loaded FOLIO ontology graph
    
    Example:
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
    status: Literal["healthy", "unhealthy"] = Field(
        description="Health status of the API",
        example="healthy"
    )
    
    folio_graph: FOLIOGraphInfo = Field(
        description="Information about the loaded FOLIO ontology graph"
    )
