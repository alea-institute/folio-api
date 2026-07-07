"""Main API module to define the FastAPI app and its configuration"""

# imports
import copy
import logging
import logging.config
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Dict
from pathlib import Path

# packages
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from folio import FOLIO
from alea_llm_client import (
    AnthropicModel,
    GoogleModel,
    GrokModel,
    OpenAIModel,
    VLLMModel,
)

# project imports
import folio_api.routes.info
import folio_api.routes.root
import folio_api.routes.search
import folio_api.routes.taxonomy
import folio_api.routes.properties
import folio_api.routes.explore
import folio_api.routes.connections
from folio_api.api_config import load_config
from folio_api.rate_limit import RateLimitConfig, RateLimitMiddleware

_DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class CachedStaticFiles(StaticFiles):
    """StaticFiles that sets an explicit ``Cache-Control`` header.

    Without it, Starlette serves static assets with only ``ETag`` /
    ``Last-Modified``, so browsers apply *heuristic* freshness and can keep
    serving a stale ``.js``/``.css`` long after a deploy (this is exactly what
    broke the Entity Graph for returning visitors: new HTML, but a cached old
    ``unified_tree.js`` with no graph wiring). Paired with ``?v=`` cache-busting
    on asset URLs, a deploy now changes the URL and browsers revalidate.
    """

    def file_response(self, *args: Any, **kwargs: Any):
        response = super().file_response(*args, **kwargs)
        response.headers.setdefault(
            "Cache-Control", "public, max-age=3600, must-revalidate"
        )
        return response


def _compute_asset_version(directory: Path) -> str:
    """Cache-busting token = newest static-asset mtime (integer seconds).

    Appended to asset URLs as ``?v=``; changes whenever any static file is
    rebuilt/redeployed, so returning browsers fetch the new asset instead of a
    stale cached copy.
    """
    try:
        latest = max(
            (p.stat().st_mtime for p in directory.rglob("*") if p.is_file()),
            default=0.0,
        )
        return str(int(latest))
    except Exception:
        return "0"


@asynccontextmanager
async def lifespan_handler(app_instance: FastAPI):
    """Context manager to handle the lifespan events of the FastAPI app

    Args:
        app_instance (FastAPI): FastAPI app instance

    Yields:
        None
    """
    # Initialize the FOLIO graph
    app_instance.state.config = load_config()
    app_instance.state.logger = logging.getLogger("folio_api")

    # Configure logging via dictConfig if provided, otherwise fall back to
    # simple FileHandler setup using the log_level key.
    api_config = app_instance.state.config["api"]
    logging_config = api_config.get("logging")
    if logging_config and "version" in logging_config:
        logging_config = copy.deepcopy(logging_config)
        if "formatters" not in logging_config:
            logging_config["formatters"] = {"default": {"format": _DEFAULT_LOG_FORMAT}}
            for handler in logging_config.get("handlers", {}).values():
                handler.setdefault("formatter", "default")
        logging.config.dictConfig(logging_config)
    else:
        log_level = {
            "info": logging.INFO,
            "debug": logging.DEBUG,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }.get(api_config.get("log_level", "info").lower().strip(), logging.INFO)

        app_instance.state.logger.setLevel(log_level)
        log_handler = logging.FileHandler("api.log")
        log_handler.setLevel(log_level)
        log_formatter = logging.Formatter(_DEFAULT_LOG_FORMAT)
        log_handler.setFormatter(log_formatter)
        app_instance.state.logger.addHandler(log_handler)

    # initialize the FOLIO instance
    app_instance.state.folio = initialize_folio(
        app_instance.state.config["folio"],
        app_instance.state.config["llm"],
    )

    # Build reverse index for property children lookups
    property_children = defaultdict(list)
    for prop in app_instance.state.folio.object_properties:
        for parent_iri in prop.sub_property_of:
            property_children[parent_iri].append(prop)
    app_instance.state.property_children = dict(property_children)

    # Share FOLIO instance with MCP server
    from folio_mcp.server import set_shared_folio

    set_shared_folio(app_instance.state.folio)

    # log it
    llm = app_instance.state.folio.llm
    app_instance.state.logger.info(
        "FOLIO instance initialized with llm %s",
        llm.model if llm is not None else "<disabled>",
    )

    yield

    # log shutdown
    app_instance.state.logger.info("Shutting down API")


_LLM_CLASSES = {
    "openai": OpenAIModel,
    "anthropic": AnthropicModel,
    "google": GoogleModel,
    "grok": GrokModel,
    "xai": GrokModel,
    "vllm": VLLMModel,
}

_API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "grok": "XAI_API_KEY",
    "xai": "XAI_API_KEY",
    "vllm": "VLLM_API_KEY",
}


def initialize_folio(folio_config: Dict[str, Any], llm_config: Dict[str, Any]) -> FOLIO:
    """Initialize FOLIO instance based on configuration.

    Args:
        folio_config: FOLIO configuration dictionary
        llm_config: LLM configuration dictionary. Supports keys:
            - type: Provider name ("openai", "anthropic", "google", "grok", "vllm")
            - model: Model name (default: "gpt-5.1-mini")
            - endpoint: Optional API endpoint override
            - api_key: Optional API key (falls back to env var)
            - effort: Universal effort level ("low", "medium", "high")
            - tier: Universal service tier ("flex", "standard", "priority")

    Returns:
        FOLIO: Initialized FOLIO instance
    """
    llm_engine = llm_config.get("type", "openai").lower().strip()
    llm_model = llm_config.get("model", "gpt-5.1-mini").strip()
    llm_endpoint = llm_config.get("endpoint", None)
    llm_api_key = llm_config.get(
        "api_key", os.getenv(_API_KEY_ENV_VARS.get(llm_engine, "OPENAI_API_KEY"))
    )
    # Treat un-substituted "${ENV_VAR}" placeholders as missing so the literal
    # string isn't passed to the LLM client as a key. Falls back to env var.
    if (
        isinstance(llm_api_key, str)
        and llm_api_key.startswith("${")
        and llm_api_key.endswith("}")
    ):
        llm_api_key = os.getenv(_API_KEY_ENV_VARS.get(llm_engine, "OPENAI_API_KEY"))
    llm_effort = llm_config.get("effort", None)
    llm_tier = llm_config.get("tier", None)

    # Create the LLM. The provider's client (e.g. alea_llm_client.OpenAIModel)
    # raises ValueError at construction if no api_key can be resolved from
    # init kwargs / env vars / key file. That hard-depends startup on a key,
    # which prevents read-only deploys (the entity graph + tree browsing don't
    # need an LLM). Skip LLM construction entirely when no key is available;
    # /search and other LLM-backed routes will fail at call time, which is the
    # right failure mode — startup succeeds, the app serves what it can.
    llm_cls = _LLM_CLASSES.get(llm_engine)
    if llm_cls is not None and llm_api_key:
        llm_args: Dict[str, Any] = {"model": llm_model, "api_key": llm_api_key}
        if llm_endpoint is not None:
            llm_args["endpoint"] = llm_endpoint
        llm = llm_cls(**llm_args)
    else:
        if llm_cls is not None:
            logging.getLogger("folio_api").warning(
                "LLM disabled: no api_key resolved for engine %r; "
                "/search and other LLM-backed routes will return errors. "
                "Set %s env var or config.llm.api_key to enable.",
                llm_engine,
                _API_KEY_ENV_VARS.get(llm_engine, "OPENAI_API_KEY"),
            )
        llm = None

    return FOLIO(
        source_type=folio_config["source"],
        github_repo_owner=folio_config["repository"].split("/")[0],
        github_repo_name=folio_config["repository"].split("/")[1],
        github_repo_branch=folio_config["branch"],
        use_cache=True,
        llm=llm,
        effort=llm_effort,
        tier=llm_tier,
    )


def get_app() -> FastAPI:
    """Factory to create FastAPI app with proper configuration

    Returns:
        FastAPI: FastAPI app with configuration
    """
    # Load the configuration
    config = load_config()
    api_config = config["api"]
    app_instance = FastAPI(
        title=api_config["title"],
        description=api_config["description"],
        version=api_config["version"],
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "documentation", "description": "Documentation-related endpoints"},
            {
                "name": "info",
                "description": "API information and health monitoring endpoints",
            },
            {
                "name": "ontology",
                "description": "Endpoints for retrieving specific ontology classes by IRI in various formats",
            },
            {
                "name": "search",
                "description": "Search endpoints for finding relevant classes in the FOLIO ontology",
            },
            {
                "name": "taxonomy",
                "description": "Endpoints for exploring ontology hierarchies and class categories",
            },
            {
                "name": "properties",
                "description": "Endpoints for browsing and exploring OWL object properties",
            },
        ],
        docs_url="/docs",
        terms_of_service=api_config["terms_of_service"],
        contact=api_config["contact"],
        license_info={
            "name": "CC-BY 4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/deed.en",
        },
        lifespan=lifespan_handler,
    )

    # App-level rate limiting (portable across Caddy/Traefik/Coolify/Railway).
    # Added before CORS so that CORS ends up the OUTERMOST middleware and its
    # headers are applied even to a 429 — browsers can then read the rejection.
    # Tiers/limits come from config.json ``api.rate_limit`` (module defaults if
    # absent). See folio_api/rate_limit.py for the design rationale.
    rate_limit_config = RateLimitConfig(api_config.get("rate_limit"))
    if rate_limit_config.enabled:
        app_instance.add_middleware(
            RateLimitMiddleware,  # type: ignore
            config=rate_limit_config,
        )

    # Enable CORS as this is a public API by default.
    app_instance.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=api_config.get("cors_origins", ["*"]),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files with appropriate cache headers
    static_dir = Path(__file__).parent / "static"

    # Check if the directory exists
    if not static_dir.exists():
        # Create the directory if it doesn't exist
        try:
            static_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(
                "Failed to create static directory: %s" % static_dir
            ) from e

    # Cache-busting token derived from the newest static asset mtime; exposed to
    # templates as `asset_version` and appended to asset URLs as `?v=`.
    asset_version = _compute_asset_version(static_dir)

    app_instance.mount(
        "/static", CachedStaticFiles(directory=static_dir), name="static"
    )

    # Initialize Jinja2 templates
    templates_dir = Path(__file__).parent / "templates" / "jinja2"

    # Create templates directory if it doesn't exist
    if not templates_dir.exists():
        try:
            templates_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(
                "Failed to create templates directory: %s" % templates_dir
            ) from e

    # Store templates instance in app state
    app_instance.state.templates = Jinja2Templates(directory=templates_dir)

    # Expose the cache-busting token to all templates (used as ?v= on assets).
    app_instance.state.templates.env.globals["asset_version"] = asset_version

    # INTERIM FIX: Register strip_folio_prefix Jinja2 filter for human-readable property labels.
    # Remove this once https://github.com/alea-institute/FOLIO/pull/5 is merged and
    # folio-python is updated with human-readable rdfs:label values.
    from folio_api.rendering import english_alternative_labels, strip_folio_prefix

    app_instance.state.templates.env.filters["strip_folio_prefix"] = strip_folio_prefix
    # Filter altLabels to exclude translation values — folio-python ≥0.3.5
    # conflates translations into alternative_labels.
    app_instance.state.templates.env.filters["english_alternative_labels"] = (
        english_alternative_labels
    )

    # Attach the routes
    app_instance.include_router(folio_api.routes.info.router)
    app_instance.include_router(folio_api.routes.search.router)
    app_instance.include_router(folio_api.routes.taxonomy.router)
    app_instance.include_router(folio_api.routes.properties.router)
    app_instance.include_router(folio_api.routes.explore.router)
    app_instance.include_router(folio_api.routes.connections.router)
    # root.router has /{iri} catch-all, so it must be registered last
    app_instance.include_router(folio_api.routes.root.router)

    # Mount FOLIO MCP server at /mcp
    from folio_mcp.server import mcp as folio_mcp_server

    app_instance.mount("/mcp", folio_mcp_server.streamable_http_app())

    return app_instance


# get instance from factory
app = get_app()

if __name__ == "__main__":
    # Load the configuration and run the dev server
    config = load_config()
    bind_host = config.get("api", {}).get("bind_ip", "0.0.0.0")
    bind_port = config.get("api", {}).get("bind_port", 8000)
    uvicorn.run(app, host=bind_host, port=bind_port)

    # Alternatively, run the app on CLI from the uvicorn command:
    # uvicorn folio_api.api:app --reload
