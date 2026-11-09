"""Main API module to define the FastAPI app and its configuration"""

# imports
import asyncio
import copy
import logging
import logging.config
import os
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Any, Dict
from pathlib import Path

# packages
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.routing import Route
from folio import FOLIO
from mcp.server.transport_security import TransportSecuritySettings
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
from folio_api.folio_compat import bound_folio_search_cache
from folio_api.ontologies import OntologyRegistry, build_property_children, make_folio_entry
from folio_api.rate_limit import RateLimitConfig, RateLimitMiddleware

# folio-python <= 0.4.0 caches every distinct fuzzy search forever (~600 KiB
# each); bound it before any FOLIO instance searches. See folio_compat.
bound_folio_search_cache()

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
    app_instance.state.property_children = build_property_children(app_instance.state.folio)

    # Share FOLIO instance with MCP server
    from folio_mcp.server import set_shared_folio

    set_shared_folio(app_instance.state.folio)

    # log it
    llm = app_instance.state.folio.llm
    app_instance.state.logger.info(
        "FOLIO instance initialized with llm %s",
        llm.model if llm is not None else "<disabled>",
    )

    # The MCP server is mounted as a sub-application (see get_app()), but Starlette
    # does not forward ASGI lifespan events to mounted sub-apps. Its streamable-HTTP
    # session manager needs its own lifespan entered explicitly here, or every
    # request 500s with "Task group is not initialized."
    mcp_app = app_instance.state.mcp_app
    async with AsyncExitStack() as mcp_stack:
        await mcp_stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))

        registry = OntologyRegistry(
            make_folio_entry(app_instance.state.folio, app_instance.state.property_children),
            enabled=app_instance.state.config.get("canon", {}).get("enabled", True),
        )
        app_instance.state.ontologies = registry
        canon_task = (
            asyncio.create_task(registry.load_canon())
            if registry.canon_state == "loading" else None
        )
        try:
            yield
        finally:
            if canon_task is not None:
                canon_task.cancel()
                with suppress(asyncio.CancelledError):
                    await canon_task

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
            - llm_kwargs: Optional object of provider parameters passed to every
              LLM call, overriding effort/tier (e.g. {"reasoning_effort": "low"})

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
    # Provider parameters passed verbatim to every LLM call, overriding what
    # effort/tier map to. alea-llm-client <= 0.3.3 only maps effort/tier for
    # gpt-5.x and silently drops them for gpt-6*, so e.g.
    # {"reasoning_effort": "low"} must be set here for those models.
    llm_kwargs = llm_config.get("llm_kwargs", None)
    if llm_kwargs is not None and not isinstance(llm_kwargs, dict):
        raise ValueError(
            "config.llm.llm_kwargs must be an object mapping parameter names "
            f"to values, got {type(llm_kwargs).__name__}"
        )

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
        llm_kwargs=llm_kwargs,
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

    # The FOLIO MCP server is a Starlette sub-app that serves its own
    # streamable_http_path ("/mcp"). It is routed with an exact
    # Route(path, endpoint=mcp_app) registered BEFORE root.router, because:
    # - root.router's /{iri} catch-all matches "/mcp" for GET. When MCP was
    #   only mounted after it, GET /mcp (the streamable-HTTP SSE stream) got
    #   the IRI lookup's 404, which MCP clients read as "session expired".
    # - Mount("/mcp", mcp_app) would nest the endpoint at "/mcp/mcp", and
    #   Starlette's Mount never matches the bare mount path anyway.
    # Route passes the full, unstripped path to mcp_app, so its own "/mcp"
    # route and any middleware it carries still apply, for every method.
    # The sub-app is stashed on state so lifespan_handler can enter its
    # session-manager lifespan (Starlette does not cascade ASGI lifespan
    # events into sub-apps).
    from folio_mcp.server import mcp as folio_mcp_server

    public_hosts = api_config.get(
        "mcp_allowed_hosts",
        [
            "folio.openlegalstandard.org",
            "soli.openlegalstandard.org",
            "folio-api.dev.openlegalstandard.org",
        ],
    )
    # SDK defaults allow loopback only; Caddy forwards the public Host.
    folio_mcp_server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
            "127.0.0.1",
            "localhost",
            "[::1]",
            *public_hosts,
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            "http://127.0.0.1",
            "http://localhost",
            "http://[::1]",
            *(f"https://{host}" for host in public_hosts),
        ],
    )
    mcp_app = folio_mcp_server.streamable_http_app()
    app_instance.state.mcp_app = mcp_app
    # mcp keeps stateful sessions until the client sends DELETE; clients that
    # just vanish would leak one (~47 KiB) each for the life of the process.
    # FastMCP does not expose the manager's idle timeout, but the manager
    # reads this public attribute per session and per request. null disables.
    folio_mcp_server.session_manager.session_idle_timeout = api_config.get(
        "mcp_session_idle_timeout", 1800
    )
    app_instance.router.routes.append(
        Route(
            folio_mcp_server.settings.streamable_http_path,
            endpoint=mcp_app,
            include_in_schema=False,
        )
    )

    # root.router has the /{iri} catch-all, so it must be registered last
    app_instance.include_router(folio_api.routes.root.router)

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
