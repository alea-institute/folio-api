"""
Models for the health check endpoint.
"""

# imports
from typing import Optional

# packages
from pydantic import BaseModel


class FOLIOGraphInfo(BaseModel):
    """
    Basic information about the FOLIO graph, including the number of classes, title, and description.
    """

    # Number of classes in the FOLIO graph
    num_classes: int

    # Title of the FOLIO graph
    title: str

    # Description of the FOLIO graph
    description: str

    # Source type of the FOLIO graph; http or github
    source_type: str

    # Source URL of the FOLIO graph if source type is http
    http_url: Optional[str]

    # GitHub owner of the FOLIO graph if source type is github
    github_repo_owner: Optional[str]

    # GitHub repository name of the FOLIO graph if source type is github
    github_repo_name: Optional[str]

    # GitHub repository branch of the FOLIO graph if source type is github
    github_repo_branch: Optional[str]


class HealthResponse(BaseModel):
    """
    Response model for the health check endpoint, including the status of the service and information about the FOLIO graph.
    """

    # Status of the service
    status: str

    # Information about the FOLIO graph
    folio_graph: FOLIOGraphInfo
