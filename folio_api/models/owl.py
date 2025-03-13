"""
Models for the health check endpoint.
"""

# imports
from typing import List, Tuple

# packages
from pydantic import BaseModel
from folio import OWLClass


class OWLClassList(BaseModel):
    """
    List of OWLClass objects.
    """

    classes: List[OWLClass]


class OWLSearchResults(BaseModel):
    """
    Search result for class information in OWL format.
    """

    results: List[Tuple[OWLClass, int | float]]
