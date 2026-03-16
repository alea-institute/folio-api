"""
Connection routes for the FOLIO API — find semantic triples between concepts.
"""

# packages
from fastapi import APIRouter, Request, status
from folio import FOLIO
from starlette.responses import JSONResponse

# API router
router = APIRouter(tags=["ontology"])


@router.get(
    "/connections",
    tags=["ontology"],
    response_model=None,
    summary="Find Semantic Connections",
    description="Find subject-property-object triples between FOLIO concepts",
    status_code=status.HTTP_200_OK,
)
async def find_connections(
    request: Request,
    subject: str,
    property: str | None = None,
    object: str | None = None,
) -> JSONResponse:
    """Find semantic connections (triples) for a given subject concept.

    Args:
        subject: IRI of the subject concept.
        property: Optional property name or IRI to filter by.
        object: Optional object concept IRI to filter by.

    Returns:
        JSON array of triples [{subject: {iri, label}, property: {iri, label}, object: {iri, label}}].
    """
    folio: FOLIO = request.app.state.folio

    # Resolve subject
    entity = folio[subject]
    if entity is None:
        # Try with prefix
        if not subject.startswith("http"):
            entity = folio[f"https://folio.openlegalstandard.org/{subject}"]
    if entity is None:
        return JSONResponse(
            content={"error": f"Subject not found: {subject}"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    connections = folio.find_connections(
        subject_class=entity.iri,
        property_name=property,
        object_class=object,
    )

    result = []
    for subj, prop, obj in connections:
        result.append({
            "subject": {"iri": subj.iri, "label": subj.label},
            "property": {"iri": prop.iri, "label": prop.label},
            "object": {"iri": obj.iri, "label": obj.label},
        })
    return JSONResponse(content=result)
