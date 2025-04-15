"""
Models for FOLIO ontology classes and search results.

These models define the response schemas for the API endpoints that return
FOLIO ontology classes and search results.
"""

# Standard library imports
from typing import List, Tuple, Union

# Third-party imports
from pydantic import BaseModel, Field
from folio import OWLClass


class OWLClassList(BaseModel):
    """
    A collection of OWLClass objects from the FOLIO ontology.

    This model represents a list of ontology classes returned by various
    endpoints, particularly the taxonomy endpoints that return multiple
    classes of a specific type.

    Attributes:
        classes: A list of OWLClass objects representing FOLIO ontology classes

    Example:
        ```json
        {
          "classes": [
            {
              "iri": "R8pNPutX0TN6DlEqkyZuxSw",
              "label": "Lessor",
              "definition": "A party that grants a right to use something in return for payment.",
              "subClassOf": ["oS5FqyVBbOYQbhqb0G28oZR"],
              ...
            },
            ...
          ]
        }
        ```
    """

    classes: List[OWLClass] = Field(
        description="List of OWLClass objects from the FOLIO ontology",
        example=[
            {
                "iri": "R8pNPutX0TN6DlEqkyZuxSw",
                "label": "Lessor",
                "definition": "A party that grants a right to use something in return for payment.",
            }
        ],
    )


class OWLSearchResults(BaseModel):
    """
    Search results containing FOLIO ontology classes with relevance scores.

    This model represents the results of search operations that return ontology
    classes along with relevance scores indicating how well each class matches
    the search query.

    Attributes:
        results: A list of tuples where each tuple contains an OWLClass and its
                relevance score (higher scores indicate better matches)

    Example:
        ```json
        {
          "results": [
            [
              {
                "iri": "R8pNPutX0TN6DlEqkyZuxSw",
                "label": "Lessor",
                "definition": "A party that grants a right to use something in return for payment.",
                ...
              },
              0.95
            ],
            ...
          ]
        }
        ```
    """

    results: List[Tuple[OWLClass, Union[int, float]]] = Field(
        description="List of tuples containing OWLClass objects and their relevance scores",
        example=[
            [
                {
                    "iri": "R8pNPutX0TN6DlEqkyZuxSw",
                    "label": "Lessor",
                    "definition": "A party that grants a right to use something in return for payment.",
                },
                0.95,
            ]
        ],
    )
