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

`limits` (https://github.com/alisaifee/limits, MIT) is the rate-limiting
primitive behind `folio_api/rate_limit.py` — the same engine `slowapi` /
`flask-limiter` wrap. We depend on it directly and drive it from one
pure-ASGI middleware (centralized per-path tiers; no per-route decorators;
SSE-safe for the mounted `/mcp` app), rather than pulling in `slowapi`'s
decorator layer. Added 2026-07-07 to restore rate limiting at the app level
(portable across Caddy/Traefik/Coolify) after the edge Caddy directive was
dropped in PR #19.
