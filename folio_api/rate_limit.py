"""App-level rate limiting for the FOLIO API.

Why app-level (not Caddy/Traefik): the edge rate_limit directive that used to
guard prod required a Caddy plugin absent from stock ``caddy:latest`` and was
silently dropped in PR #19 — leaving ``/search/llm/*`` (real, *paid* OpenAI/XAI
calls) with **zero** limiting: an unauthenticated cost-DoS vector. Enforcing in
the app makes the protection portable across every deploy target we run (Caddy
on bare-metal prod, Traefik/Coolify on dev, Railway, plain ``docker run``) —
the limiter travels with the code instead of living in one proxy's config.

Design:
  * **Engine:** the ``limits`` library (the same primitive ``slowapi`` /
    ``flask-limiter`` wrap). We drive it directly from a single pure-ASGI
    middleware rather than decorating ~20 ``/search/llm/*`` routes one-by-one:
    tiers stay centralized in one config dict, and pure-ASGI passes streaming
    responses (the mounted ``/mcp`` SSE app) through untouched — a
    ``BaseHTTPMiddleware`` would buffer and break them.
  * **Tiers by path prefix:** tightest on the paid ``/search/llm/*`` routes,
    moderate on the other ``/search/*`` routes, generous default everywhere
    else. Health, static, docs and ``/mcp`` are exempt.
  * **Key = client IP, proxy-aware.** Behind a single trusted reverse proxy
    (Caddy/Traefik) the real client is the *rightmost* entry of
    ``X-Forwarded-For`` (the proxy appends the socket peer it actually saw, so
    a client-spoofed leftmost value is ignored). ``trusted_proxy_hops`` makes
    the number of trusted hops configurable; set it to ``0`` if the app is ever
    exposed to the internet with no proxy in front (then only the socket IP is
    trusted).
  * **429 + Retry-After** plus ``X-RateLimit-*`` headers on limited responses.

Scaling note: the default ``memory://`` storage is per-process. uvicorn runs a
single worker here, so counts are global. If this ever runs multiple
workers/replicas, point ``rate_limit.storage_uri`` at Redis
(``redis://host:6379``) so the window is shared — otherwise the effective limit
multiplies by the worker count.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from limits import RateLimitItem, parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Sensible built-in defaults, used when config.json has no ``api.rate_limit``
# block so an old config still gets protected. Ordered most→least specific;
# longest matching prefix wins.
DEFAULT_TIERS: Dict[str, List[str]] = {
    "/search/llm/": ["10/minute", "100/hour"],  # paid LLM calls — tightest
    "/search/": ["60/minute", "1000/hour"],  # non-LLM search — moderate
    "default": ["240/minute"],  # everything else — generous
}

DEFAULT_EXEMPT_PREFIXES: List[str] = [
    "/info/health",  # Docker/Coolify/uptime probes — never limit liveness
    "/static",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/mcp",  # mounted MCP sub-app (SSE) — must pass through untouched
    "/favicon.ico",
]


class RateLimitConfig:
    """Parsed, validated rate-limit configuration.

    Built from the ``api.rate_limit`` block of ``config.json`` (all keys
    optional; missing keys fall back to the module defaults).
    """

    def __init__(self, raw: Optional[Dict[str, Any]] = None) -> None:
        raw = raw or {}
        self.enabled: bool = bool(raw.get("enabled", True))
        self.storage_uri: str = raw.get("storage_uri", "memory://")
        self.trusted_proxy_hops: int = int(raw.get("trusted_proxy_hops", 1))
        self.exempt_prefixes: List[str] = list(
            raw.get("exempt_prefixes", DEFAULT_EXEMPT_PREFIXES)
        )

        tiers_raw: Dict[str, Any] = dict(raw.get("tiers", DEFAULT_TIERS))
        if "default" not in tiers_raw:
            tiers_raw["default"] = DEFAULT_TIERS["default"]

        # name/prefix -> parsed RateLimitItem list. "default" is the fallback.
        self.tiers: Dict[str, List[RateLimitItem]] = {}
        for name, limits_spec in tiers_raw.items():
            if isinstance(limits_spec, str):
                limits_spec = [limits_spec]
            self.tiers[name] = [parse(spec) for spec in limits_spec]

        # Prefixes (everything but "default"), longest first so the most
        # specific tier wins (e.g. "/search/llm/" before "/search/").
        self._prefixes: List[str] = sorted(
            (p for p in self.tiers if p != "default"),
            key=len,
            reverse=True,
        )

    def is_exempt(self, path: str) -> bool:
        """True if ``path`` is under an exempt prefix (no limiting applied)."""
        return any(path.startswith(pref) for pref in self.exempt_prefixes)

    def limits_for(self, path: str) -> Tuple[str, List[RateLimitItem]]:
        """Return ``(tier_name, limits)`` for a request path."""
        for pref in self._prefixes:
            if path.startswith(pref):
                return pref, self.tiers[pref]
        return "default", self.tiers["default"]


def client_ip_from_scope(scope: Scope, trusted_proxy_hops: int) -> str:
    """Resolve the real client IP from an ASGI scope, proxy-aware.

    With ``trusted_proxy_hops == N`` and a chain
    ``client -> proxy1 -> ... -> proxyN -> app``, the real client is the entry
    ``N`` positions from the right of ``X-Forwarded-For`` (each trusted proxy
    appends the peer it saw; the rightmost ``N`` entries are the ones our own
    trusted proxies wrote, so a client-supplied leftmost value can't spoof the
    key). Falls back to the socket peer when there is no usable header.
    """
    if trusted_proxy_hops > 0:
        xff = _header(scope, b"x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                idx = min(trusted_proxy_hops, len(parts))
                return parts[-idx]

    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


def _header(scope: Scope, name: bytes) -> Optional[str]:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin-1")
    return None


class RateLimitMiddleware:
    """Pure-ASGI middleware enforcing per-path-tier IP rate limits."""

    def __init__(self, app: ASGIApp, config: RateLimitConfig) -> None:
        self.app = app
        self.config = config
        self.storage = storage_from_string(config.storage_uri)
        self.limiter = MovingWindowRateLimiter(self.storage)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if self.config.is_exempt(path):
            await self.app(scope, receive, send)
            return

        tier_name, limits = self.config.limits_for(path)
        key = client_ip_from_scope(scope, self.config.trusted_proxy_hops)

        allowed, offending = self._check(limits, tier_name, key)
        if not allowed:
            assert offending is not None
            await self._reject(
                offending,
                tier_name,
                key,
                scope=scope,
                receive=receive,
                send=send,
            )
            return

        # Allowed: surface the tightest remaining budget in response headers.
        remaining, reset = self._tightest_stats(limits, tier_name, key)
        limit_header = str(limits[0]) if limits else ""
        rl_headers = [
            (b"x-ratelimit-limit", limit_header.encode("latin-1")),
            (b"x-ratelimit-remaining", str(remaining).encode("latin-1")),
            (b"x-ratelimit-reset", str(int(reset)).encode("latin-1")),
        ]

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(rl_headers)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)

    def _check(
        self, limits: Sequence[RateLimitItem], tier: str, key: str
    ) -> Tuple[bool, Optional[RateLimitItem]]:
        """Consume one hit against every limit in the tier.

        Returns ``(True, None)`` if all pass, else ``(False, offending_limit)``.
        """
        for item in limits:
            if not self.limiter.hit(item, tier, key):
                return False, item
        return True, None

    def _tightest_stats(
        self, limits: Sequence[RateLimitItem], tier: str, key: str
    ) -> Tuple[int, float]:
        """Lowest remaining budget (and its reset) across the tier's limits."""
        remaining = None
        reset = time.time()
        for item in limits:
            stats = self.limiter.get_window_stats(item, tier, key)
            if remaining is None or stats.remaining < remaining:
                remaining = stats.remaining
                reset = stats.reset_time
        return (remaining if remaining is not None else 0, reset)

    async def _reject(
        self,
        offending: RateLimitItem,
        tier: str,
        key: str,
        *,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        stats = self.limiter.get_window_stats(offending, tier, key)
        retry_after = max(1, int(round(stats.reset_time - time.time())))
        limit_str = str(offending)
        response = JSONResponse(
            status_code=429,
            content={
                "detail": (
                    f"Rate limit exceeded: {limit_str}. " f"Retry in {retry_after}s."
                ),
                "limit": limit_str,
                "retry_after": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": limit_str,
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(stats.reset_time)),
            },
        )
        await response(scope, receive, send)
