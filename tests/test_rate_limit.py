"""Tests for app-level rate limiting (folio_api/rate_limit.py).

Self-contained: each test builds a tiny Starlette app wrapped in
``RateLimitMiddleware`` with small, fast limits and a fresh in-memory store, so
nothing depends on the FOLIO ontology load or the real config thresholds. This
keeps the suite deterministic and instant.

Coverage:
  * per-route tiers — the paid ``/search/llm/*`` tier is tighter than the
    moderate ``/search/*`` tier, which is tighter than the generous default;
  * 429 body + ``Retry-After``/``X-RateLimit-*`` header handling;
  * ``X-Forwarded-For`` parsing — separate IPs get separate buckets, a
    client-spoofed leftmost value is ignored (rightmost trusted), and
    ``trusted_proxy_hops`` controls how many hops are trusted;
  * exempt prefixes are never limited.
"""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from fastapi.testclient import TestClient

from folio_api.rate_limit import (
    RateLimitConfig,
    RateLimitMiddleware,
    client_ip_from_scope,
)


def _make_client(raw_config: dict) -> TestClient:
    """Tiny app with three probe routes covering the three tiers + an exempt
    health route, wrapped in the middleware under test."""

    async def ok(request):  # noqa: ANN001
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[
            Route("/search/llm/events", ok),
            Route("/search/prefix", ok),
            Route("/taxonomy/tree", ok),  # falls through to default tier
            Route("/info/health", ok),  # exempt
        ]
    )
    app.add_middleware(RateLimitMiddleware, config=RateLimitConfig(raw_config))
    # raise_server_exceptions so any middleware bug surfaces as a test error.
    return TestClient(app, raise_server_exceptions=True)


# ─────────────────────────── tier enforcement ───────────────────────────


def test_llm_tier_is_tightest():
    """The paid /search/llm/* tier rejects after its (small) threshold."""
    client = _make_client(
        {
            "tiers": {
                "/search/llm/": ["2/minute"],
                "/search/": ["5/minute"],
                "default": ["100/minute"],
            }
        }
    )
    assert client.get("/search/llm/events?query=x").status_code == 200
    assert client.get("/search/llm/events?query=x").status_code == 200
    r = client.get("/search/llm/events?query=x")
    assert r.status_code == 429


def test_search_tier_more_generous_than_llm():
    """The moderate /search/ tier allows more than the llm tier before 429."""
    client = _make_client(
        {
            "tiers": {
                "/search/llm/": ["2/minute"],
                "/search/": ["5/minute"],
                "default": ["100/minute"],
            }
        }
    )
    # 5 allowed on the moderate tier, 6th rejected.
    for _ in range(5):
        assert client.get("/search/prefix?query=x").status_code == 200
    assert client.get("/search/prefix?query=x").status_code == 429


def test_most_specific_prefix_wins():
    """/search/llm/ must match its own tier, not the broader /search/ tier."""
    client = _make_client(
        {
            "tiers": {
                "/search/llm/": ["1/minute"],
                "/search/": ["50/minute"],
                "default": ["100/minute"],
            }
        }
    )
    assert client.get("/search/llm/events?query=x").status_code == 200
    assert client.get("/search/llm/events?query=x").status_code == 429
    # the moderate /search/ route is unaffected by the llm bucket
    assert client.get("/search/prefix?query=x").status_code == 200


def test_default_tier_applies_to_other_paths():
    client = _make_client(
        {"tiers": {"/search/": ["50/minute"], "default": ["2/minute"]}}
    )
    assert client.get("/taxonomy/tree").status_code == 200
    assert client.get("/taxonomy/tree").status_code == 200
    assert client.get("/taxonomy/tree").status_code == 429


# ──────────────────────────── 429 headers ───────────────────────────────


def test_429_has_retry_after_and_ratelimit_headers():
    client = _make_client(
        {"tiers": {"/search/llm/": ["1/minute"], "default": ["100/minute"]}}
    )
    assert client.get("/search/llm/events?query=x").status_code == 200
    r = client.get("/search/llm/events?query=x")
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) >= 1
    assert r.headers["X-RateLimit-Remaining"] == "0"
    assert r.headers["X-RateLimit-Limit"]  # non-empty (e.g. "1 per 1 minute")
    body = r.json()
    assert body["retry_after"] >= 1
    assert "limit" in body


def test_allowed_response_carries_ratelimit_headers():
    client = _make_client(
        {"tiers": {"/search/": ["5/minute"], "default": ["100/minute"]}}
    )
    r = client.get("/search/prefix?query=x")
    assert r.status_code == 200
    # 5 allowed, one consumed -> 4 remaining
    assert r.headers["X-RateLimit-Remaining"] == "4"


# ────────────────────────── exempt prefixes ─────────────────────────────


def test_health_is_exempt():
    """Liveness probes must never be limited or carry limiter headers."""
    client = _make_client({"tiers": {"default": ["1/minute"]}})
    for _ in range(10):
        r = client.get("/info/health")
        assert r.status_code == 200
    assert "X-RateLimit-Remaining" not in r.headers


# ─────────────────── X-Forwarded-For / proxy trust ──────────────────────


def test_separate_client_ips_get_separate_buckets():
    client = _make_client(
        {"tiers": {"/search/llm/": ["1/minute"], "default": ["100/minute"]}}
    )
    h1 = {"X-Forwarded-For": "203.0.113.1"}
    h2 = {"X-Forwarded-For": "203.0.113.2"}
    assert client.get("/search/llm/events?query=x", headers=h1).status_code == 200
    # second request from the SAME ip -> limited
    assert client.get("/search/llm/events?query=x", headers=h1).status_code == 429
    # a different client ip still has its own budget
    assert client.get("/search/llm/events?query=x", headers=h2).status_code == 200


def test_spoofed_leftmost_xff_is_ignored():
    """With one trusted hop the rightmost XFF entry (appended by our proxy) is
    the key; a client-supplied leftmost value cannot rotate to evade limits."""
    client = _make_client(
        {"tiers": {"/search/llm/": ["1/minute"], "default": ["100/minute"]}}
    )
    # Same real client (rightmost 198.51.100.9), different spoofed leftmost.
    r1 = client.get(
        "/search/llm/events?query=x",
        headers={"X-Forwarded-For": "1.1.1.1, 198.51.100.9"},
    )
    r2 = client.get(
        "/search/llm/events?query=x",
        headers={"X-Forwarded-For": "2.2.2.2, 198.51.100.9"},
    )
    assert r1.status_code == 200
    assert r2.status_code == 429  # same real client -> still limited


def test_client_ip_from_scope_rightmost_with_one_hop():
    scope = {
        "client": ("172.17.0.1", 5000),
        "headers": [(b"x-forwarded-for", b"1.1.1.1, 198.51.100.9")],
    }
    assert client_ip_from_scope(scope, trusted_proxy_hops=1) == "198.51.100.9"


def test_client_ip_from_scope_two_hops():
    scope = {
        "client": ("172.17.0.1", 5000),
        "headers": [(b"x-forwarded-for", b"real, proxyA, proxyB")],
    }
    # trust 2 hops -> the entry 2 from the right = "proxyA"'s left neighbor
    assert client_ip_from_scope(scope, trusted_proxy_hops=2) == "proxyA"


def test_client_ip_from_scope_zero_hops_uses_socket():
    """hops=0 (no trusted proxy) must ignore XFF entirely and use socket IP."""
    scope = {
        "client": ("198.51.100.50", 5000),
        "headers": [(b"x-forwarded-for", b"1.1.1.1")],
    }
    assert client_ip_from_scope(scope, trusted_proxy_hops=0) == "198.51.100.50"


def test_client_ip_from_scope_no_xff_falls_back_to_socket():
    scope = {"client": ("198.51.100.77", 5000), "headers": []}
    assert client_ip_from_scope(scope, trusted_proxy_hops=1) == "198.51.100.77"


# ───────────────────────────── config ───────────────────────────────────


def test_config_defaults_when_absent():
    cfg = RateLimitConfig(None)
    assert cfg.enabled is True
    assert cfg.trusted_proxy_hops == 1
    # default tier always present; llm prefix tighter than search prefix
    name_llm, _ = cfg.limits_for("/search/llm/events")
    name_search, _ = cfg.limits_for("/search/prefix")
    name_other, _ = cfg.limits_for("/taxonomy/tree")
    assert name_llm == "/search/llm/"
    assert name_search == "/search/"
    assert name_other == "default"


def test_config_can_disable():
    assert RateLimitConfig({"enabled": False}).enabled is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
