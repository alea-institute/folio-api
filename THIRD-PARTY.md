# Third-Party Licenses & Attribution

folio-api is licensed **MIT** (see `LICENSE`, `license = "MIT"` in
`pyproject.toml`). It serves and incorporates the components below.

## Openly-licensed data

### FOLIO ontology — CC-BY 4.0
folio-api's entire purpose is to serve **FOLIO** (Federated Open Legal
Information Ontology), maintained by the **ALEA Institute**, originating from the
**SALI Alliance**, licensed **Creative Commons Attribution 4.0 International
(CC-BY 4.0)**. Consumers of this API must attribute FOLIO accordingly.
- Source: https://github.com/alea-institute/FOLIO
- License: https://creativecommons.org/licenses/by/4.0/

## Notable dependencies

| Component | License |
|-----------|---------|
| folio-python[search], fastapi, folio-mcp | MIT |
| `limits` (>=3.13,<6; pinned to 5.8.0 in `uv.lock`) | MIT |
| uvicorn, jinja2 | BSD-3-Clause |
| starlette, pydantic | BSD-3-Clause / MIT (pulled by FastAPI; imported directly) |
| alea-llm-client | MIT (ALEA Institute) — backs the `/search/llm/*` routes |

**Undeclared direct import.** `folio_api` imports `alea_llm_client` directly but
`pyproject.toml` does not list it; it resolves today only as a transitive of
`folio-python[search]`. Licensing is clean (MIT, same authors), but the manifest
should declare it — flagged rather than changed here, since dependency edits are
out of scope for a docs pass.

### Dev dependencies

| Component | License |
|-----------|---------|
| pytest, pytest-asyncio, pytest-cov | MIT / Apache-2.0 |
| black, pylint | MIT / GPL-2.0-or-later (pylint is a dev-only tool, never linked or redistributed) |
| sphinx, myst-parser, sphinx-book-theme, sphinxcontrib-mermaid | BSD-2-Clause / MIT |
| hatchling (build backend) | MIT |

`limits` (https://github.com/alisaifee/limits, MIT) is the rate-limiting
primitive behind `folio_api/rate_limit.py` — the same engine `slowapi` /
`flask-limiter` wrap. We depend on it directly and drive it from one
pure-ASGI middleware (centralized per-path tiers; no per-route decorators;
SSE-safe for the mounted `/mcp` app), rather than pulling in `slowapi`'s
decorator layer. Added 2026-07-07 to restore rate limiting at the app level
(portable across Caddy/Traefik/Coolify) after the edge Caddy directive was
dropped in PR #19.
