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
    ``flask-limiter`` wrap), via its **async** strategy so a networked storage
    backend (``redis://``) never blocks the event loop. We drive it directly
    from a single pure-ASGI middleware rather than decorating ~20
    ``/search/llm/*`` routes one-by-one: tiers stay centralized in one config
    dict, and pure-ASGI passes streaming responses (the mounted ``/mcp`` SSE
    app) through untouched — a ``BaseHTTPMiddleware`` would buffer and break
    them.
  * **Tiers by path prefix:** tightest on the paid ``/search/llm/*`` routes,
    moderate on the other ``/search/*`` routes, generous default everywhere
    else. Health, static, docs and ``/mcp`` are exempt (segment-boundary
    matched, so ``/mcp-evil`` is NOT exempt).
  * **Key = client IP, proxy-aware AND socket-gated.** ``X-Forwarded-For`` is
    only consulted when the *socket peer* is a plausible reverse proxy
    (loopback / RFC-1918 / CGNAT / link-local / ULA — i.e. the docker network
    Caddy/Traefik connect from). A direct internet client therefore can never
    spoof XFF to rotate buckets: its own socket IP is used. Behind the trusted
    proxy, the real client is the *rightmost* XFF entry (the proxy appends the
    peer it actually saw), with ``trusted_proxy_hops`` configurable for deeper
    chains; ``0`` disables XFF trust entirely.
  * **429 + Retry-After** plus ``X-RateLimit-*`` headers on limited responses.

Scaling note: the default ``memory://`` storage is per-process. uvicorn runs a
single worker here, so counts are global. If this ever runs multiple
workers/replicas, point ``rate_limit.storage_uri`` at Redis
(``redis://host:6379``) so the window is shared — otherwise the effective limit
multiplies by the worker count. The redis path additionally requires the
``limits[async-redis]`` extra to be installed.
"""

from __future__ import annotations

import ipaddress
import time
from typing import Any, Sequence

from limits import RateLimitItem, parse
from limits.aio.storage import Storage as AsyncStorage
from limits.aio.strategies import MovingWindowRateLimiter
from limits.storage import storage_from_string
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Sensible built-in defaults, used when config.json has no ``api.rate_limit``
# block so an old config still gets protected. Ordered most→least specific;
# longest matching prefix wins.
DEFAULT_TIERS: dict[str, list[str]] = {
    "/search/llm/": ["10/minute", "100/hour"],  # paid LLM calls — tightest
    "/search/": ["60/minute", "1000/hour"],  # non-LLM search — moderate
    "default": ["240/minute"],  # everything else — generous
}

DEFAULT_EXEMPT_PREFIXES: list[str] = [
    "/info/health",  # Docker/Coolify/uptime probes — never limit liveness
    "/static",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/mcp",  # mounted MCP sub-app (SSE) — must pass through untouched
    "/favicon.ico",
]

# Socket-peer networks from which we accept X-Forwarded-For as proxy-written.
# These cover every topology we deploy: docker bridge/compose networks
# (RFC 1918), Coolify/Traefik overlay nets, CGNAT (100.64/10), loopback for
# on-box proxies, and their IPv6 equivalents. A *public* socket peer is by
# definition not our reverse proxy, so its XFF header is attacker-controlled
# and must be ignored — this is what makes bucket-rotation-by-spoofed-XFF
# impossible even if the app port is accidentally exposed to the internet.
_PROXY_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _is_proxy_peer(host: str | None) -> bool:
    """True if the socket peer could be our reverse proxy.

    Non-IP hosts (e.g. Starlette's ``TestClient`` uses the literal string
    ``"testclient"``; UDS transports have no peer) can only occur in embedded
    or test transports — never on a real TCP connection, where uvicorn always
    reports an IP — so they are treated as trusted.
    """
    if host is None:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return True  # embedded/test transport, not a real TCP peer
    return any(addr in net for net in _PROXY_NETWORKS)


class RateLimitConfig:
    """Parsed, validated rate-limit configuration.

    Built from the ``api.rate_limit`` block of ``config.json`` (all keys
    optional; missing keys fall back to the module defaults).
    """

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        raw = raw or {}
        self.enabled: bool = bool(raw.get("enabled", True))
        self.storage_uri: str = raw.get("storage_uri", "memory://")
        self.trusted_proxy_hops: int = int(raw.get("trusted_proxy_hops", 1))
        self.exempt_prefixes: list[str] = list(
            raw.get("exempt_prefixes", DEFAULT_EXEMPT_PREFIXES)
        )

        tiers_raw: dict[str, Any] = dict(raw.get("tiers", DEFAULT_TIERS))
        if "default" not in tiers_raw:
            tiers_raw["default"] = DEFAULT_TIERS["default"]

        # name/prefix -> parsed RateLimitItem list. "default" is the fallback.
        self.tiers: dict[str, list[RateLimitItem]] = {}
        for name, limits_spec in tiers_raw.items():
            if isinstance(limits_spec, str):
                limits_spec = [limits_spec]
            if not limits_spec:
                raise ValueError(
                    f"rate_limit tier {name!r} has no limits; remove the tier "
                    "or give it at least one limit string (e.g. '60/minute')"
                )
            self.tiers[name] = [parse(spec) for spec in limits_spec]

        # Prefixes (everything but "default"), longest first so the most
        # specific tier wins (e.g. "/search/llm/" before "/search/").
        self._prefixes: list[str] = sorted(
            (p for p in self.tiers if p != "default"),
            key=len,
            reverse=True,
        )

    def is_exempt(self, path: str) -> bool:
        """True if ``path`` is under an exempt prefix (no limiting applied).

        Segment-boundary matched: ``/mcp`` exempts ``/mcp`` and ``/mcp/...``
        but NOT ``/mcp-evil`` — a bare ``startswith`` would over-exempt.
        """
        return any(_prefix_match(path, pref) for pref in self.exempt_prefixes)

    def limits_for(self, path: str) -> tuple[str, list[RateLimitItem]]:
        """Return ``(tier_name, limits)`` for a request path."""
        for pref in self._prefixes:
            if path.startswith(pref):
                return pref, self.tiers[pref]
        return "default", self.tiers["default"]


def _prefix_match(path: str, prefix: str) -> bool:
    """Prefix match that respects path-segment boundaries."""
    if prefix.endswith("/"):
        return path.startswith(prefix) or path == prefix.rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def client_ip_from_scope(scope: Scope, trusted_proxy_hops: int) -> str:
    """Resolve the real client IP from an ASGI scope, proxy-aware.

    ``X-Forwarded-For`` is honored only when BOTH hold:
      1. ``trusted_proxy_hops > 0``, and
      2. the socket peer is a plausible proxy address (loopback/private —
         see ``_PROXY_NETWORKS``). A public socket peer connected directly,
         so its XFF header is client-controlled noise and is ignored.

    With ``trusted_proxy_hops == N`` and a chain
    ``client -> proxy1 -> ... -> proxyN -> app``, the real client is the entry
    ``N`` positions from the right of the (comma-joined) XFF value: each
    trusted proxy appends the peer it saw, so the rightmost ``N`` entries were
    written by our own proxies and a client-supplied leftmost value can't
    spoof the key. Falls back to the socket peer when there is no usable
    header.
    """
    client = scope.get("client")
    socket_host: str | None = client[0] if client else None

    if trusted_proxy_hops > 0 and _is_proxy_peer(socket_host):
        xff = _xff_joined(scope)
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                idx = min(trusted_proxy_hops, len(parts))
                return parts[-idx]

    return socket_host if socket_host is not None else "unknown"


def _xff_joined(scope: Scope) -> str | None:
    """All ``X-Forwarded-For`` header values, comma-joined in wire order.

    A client may smuggle its own XFF as a *separate* header line before the
    proxy-appended one; taking only the first line would return the forged
    value. Joining preserves order, keeping the proxy-written entry rightmost.
    """
    values = [
        value.decode("latin-1")
        for key, value in scope.get("headers", [])
        if key == b"x-forwarded-for"
    ]
    return ",".join(values) if values else None


def _async_storage(storage_uri: str) -> AsyncStorage:
    """Build the async variant of the configured storage backend.

    Config uses the familiar sync-style URIs (``memory://``, ``redis://...``);
    the ``async+`` scheme prefix selects the asyncio implementations that the
    async strategy requires.
    """
    uri = storage_uri
    if not uri.startswith("async+"):
        uri = f"async+{uri}"
    return storage_from_string(uri)  # type: ignore[return-value]


class RateLimitMiddleware:
    """Pure-ASGI middleware enforcing per-path-tier IP rate limits."""

    def __init__(self, app: ASGIApp, config: RateLimitConfig) -> None:
        self.app = app
        self.config = config
        self.storage = _async_storage(config.storage_uri)
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

        offending = await self._check(limits, tier_name, key)
        if offending is not None:
            await self._reject(
                offending,
                tier_name,
                key,
                scope=scope,
                receive=receive,
                send=send,
            )
            return

        # Allowed: surface the tightest remaining budget in response headers
        # (limit + remaining + reset all reported from the SAME limit item).
        tightest, remaining, reset = await self._tightest_stats(limits, tier_name, key)
        rl_headers = [
            (b"x-ratelimit-limit", str(tightest).encode("latin-1")),
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

    async def _check(
        self, limits: Sequence[RateLimitItem], tier: str, key: str
    ) -> RateLimitItem | None:
        """Consume one hit against every limit in the tier.

        Returns ``None`` if all pass, else the first offending limit. Note:
        limits checked *before* the offending one have already been consumed —
        a slight over-count on rejected requests, acceptable (and fail-safe)
        for a protective limiter.
        """
        for item in limits:
            if not await self.limiter.hit(item, tier, key):
                return item
        return None

    async def _tightest_stats(
        self, limits: Sequence[RateLimitItem], tier: str, key: str
    ) -> tuple[RateLimitItem, int, float]:
        """The limit with the lowest remaining budget, plus its stats."""
        tightest = limits[0]
        remaining: int | None = None
        reset = time.time()
        for item in limits:
            stats = await self.limiter.get_window_stats(item, tier, key)
            if remaining is None or stats.remaining < remaining:
                tightest = item
                remaining = stats.remaining
                reset = stats.reset_time
        return tightest, (remaining if remaining is not None else 0), reset

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
        stats = await self.limiter.get_window_stats(offending, tier, key)
        retry_after = max(1, int(round(stats.reset_time - time.time())))
        limit_str = str(offending)
        response = JSONResponse(
            status_code=429,
            content={
                "detail": (
                    f"Rate limit exceeded: {limit_str}. Retry in {retry_after}s."
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
