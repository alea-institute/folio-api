---
title: "App-level rate limiting restoration (portable across Caddy/Traefik/Coolify)"
category: security-issues
date: 2026-07-07
component: folio_api/rate_limit.py
tags: [rate-limiting, cost-dos, x-forwarded-for, asgi-middleware, limits, caddy, coolify, proxy-trust]
pr: "https://github.com/alea-institute/folio-api/pull/21"
merged: "864d1dc"
---

# App-level rate limiting restoration

## Problem

PR #19 dropped the Caddy `rate_limit @api 100r/m` directive from the prod
Caddyfile (it needed a Caddy plugin absent from stock `caddy:latest` that broke
`docker compose up`). Result: **zero rate limiting in production** on
`/search/*`, including `/search/llm/*` routes that make real paid OpenAI/XAI
calls per request — an unauthenticated cost-DoS vector, flagged HIGH in review.

## Root cause

Rate limiting lived in ONE proxy's config (Caddy, plugin-dependent). Any infra
change (image swap, proxy swap, new deploy target) could silently drop it —
and did. Edge config is not portable across our targets (Caddy bare-metal
prod, Traefik/Coolify dev, Railway).

## Solution

Enforce in the app so the protection travels with the code:
`folio_api/rate_limit.py` — a **pure-ASGI middleware** driving the
[`limits`](https://github.com/alisaifee/limits) library directly (the engine
slowapi/flask-limiter wrap). Key decisions, each earned by a review finding or
a deployment constraint:

1. **Pure-ASGI, not `BaseHTTPMiddleware`** — the mounted `/mcp` sub-app
   streams SSE; `BaseHTTPMiddleware` buffers and breaks it. Exempt paths
   short-circuit before any send-wrapping.
2. **One middleware + config-dict tiers, not per-route decorators** — ~20
   `/search/llm/*` routes stay untouched; tiers live in `config.json`
   (`api.rate_limit`) with protective code defaults if the block is absent.
   Longest-prefix wins: `/search/llm/` 10/min+100/hr, `/search/` 60/min+1000/hr,
   default 240/min. Health/static/docs/`/mcp` exempt (segment-boundary matched:
   `/mcp` does not exempt `/mcp-evil`).
3. **Socket-gated XFF trust** (the critical one): `X-Forwarded-For` is only
   honored when the *socket peer* is a private/loopback address (the docker
   network Caddy/Traefik connect from). A direct internet client can never
   rotate buckets with spoofed XFF — even if the app port is accidentally
   exposed. Behind the proxy, use the **rightmost** XFF entry
   (`trusted_proxy_hops` configurable); join multiple XFF header *lines* in
   wire order first (a client-smuggled separate line must not shadow the
   proxy-written one).
4. **Async engine** (`limits.aio`, `async+memory://`) so a future `redis://`
   backend (multi-worker) can't block the event loop. `memory://` is correct
   for single-worker uvicorn; redis needs the `limits[async-redis]` extra.
5. **429 + `Retry-After` + `X-RateLimit-*`**; the limiter middleware is added
   *before* CORS so CORS is outermost and 429s are readable cross-origin.
   `X-RateLimit-Limit` and `-Remaining` must describe the SAME (tightest)
   limit item.

Verification trick worth remembering: **drive the LLM-route limiter with
1-char queries** — the handler's min-length check fails *before* the LLM call,
so you can prove "10 handled → 429" thresholds on prod with **$0 spend**.

## Prevention

- App-level enforcement for anything security-critical that must survive
  infra churn; proxy config is a bonus layer, never the only layer.
- When trusting `X-Forwarded-For`, always gate on the socket peer being your
  proxy — never trust the header shape alone (rightmost-entry logic is only
  safe when the header was verifiably appended by your own proxy).
- Tests must cover the spoofing cases: public-socket-peer XFF, multi-line XFF
  smuggling, hops 0/1/2, exemption boundary matching (`tests/test_rate_limit.py`).

## Known ride-along (pre-existing, NOT fixed here)

`/search/llm/*` and `/search/label|definition` return **500** for
length-check-failing queries: handlers return `OWLClassList` where
`response_model=OWLSearchResults` → response-validation error
(`folio_api/routes/search.py`, e.g. line 414). Cheap fix for the next change.
