"""
Unified explore routes for the FOLIO API — combined class + property tree view.
"""

# imports
from pathlib import Path

# packages
from fastapi import APIRouter, Request
from starlette.responses import Response

# API router
router = APIRouter(prefix="/explore", tags=["explore"])


@router.get(
    "/tree",
    tags=["explore"],
    response_model=None,
    summary="Unified Ontology Explorer",
    description="Explore both FOLIO classes and properties in a single interactive tree view",
    include_in_schema=False,
)
async def explore_tree(request: Request) -> Response:
    """Unified tree explorer combining classes (nouns) and properties (verbs)."""
    typeahead_js_path = Path(__file__).parent.parent / "static" / "js" / "typeahead_search.js"
    typeahead_js_source = typeahead_js_path.read_text(encoding="utf-8")

    return request.app.state.templates.TemplateResponse(
        "explore/tree.html",
        {
            "request": request,
            "typeahead_js_source": typeahead_js_source,
            "config": request.app.state.config,
        },
    )
