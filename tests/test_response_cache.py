"""ResponseCacheMiddleware: serves repeated explorer GETs from memory, safely."""

from types import SimpleNamespace

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from folio_api.response_cache import ResponseCacheMiddleware


def _make(max_bytes=1024, max_entry_bytes=1024):
    calls = []

    async def ok(request):
        calls.append(str(request.url))
        size = int(request.query_params.get("size", "3"))
        return PlainTextResponse("x" * size, headers={"X-Call": str(len(calls))})

    async def missing(request):
        calls.append(str(request.url))
        return PlainTextResponse("nope", status_code=404)

    async def cookie(request):
        calls.append(str(request.url))
        response = PlainTextResponse("c")
        response.set_cookie("a", "b")
        return response

    app = Starlette(
        routes=[
            Route("/taxonomy/tree/search", ok, methods=["GET", "POST"]),
            Route("/taxonomy/tree/data", missing),
            Route("/taxonomy/tree/node/c", cookie),
            Route("/info/other", ok),
        ]
    )
    app.state.ontologies = SimpleNamespace(canon_state="ready")
    middleware = ResponseCacheMiddleware(app, max_bytes=max_bytes, max_entry_bytes=max_entry_bytes)

    async def outer(scope, receive, send):
        # In the real app Starlette sets scope["app"] before user middleware runs.
        scope["app"] = app
        await middleware(scope, receive, send)

    return TestClient(outer), middleware, calls, app


def test_repeat_get_is_served_from_cache_byte_identical():
    client, mw, calls, _ = _make()
    first = client.get("/taxonomy/tree/search?query=contract")
    second = client.get("/taxonomy/tree/search?query=contract")
    assert len(calls) == 1
    assert second.content == first.content
    assert second.headers["x-call"] == "1"
    assert second.headers["content-type"] == first.headers["content-type"]
    assert (mw.hits, mw.misses) == (1, 1)


def test_key_includes_query_host_and_canon_state():
    client, _, calls, app = _make()
    client.get("/taxonomy/tree/search?query=a")
    client.get("/taxonomy/tree/search?query=b")
    client.get("/taxonomy/tree/search?query=a", headers={"host": "soli.example"})
    app.state.ontologies.canon_state = "loading"
    client.get("/taxonomy/tree/search?query=a")
    assert len(calls) == 4


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/taxonomy/tree/search"),
        ("GET", "/taxonomy/tree/data"),  # 404
        ("GET", "/taxonomy/tree/node/c"),  # Set-Cookie
        ("GET", "/info/other"),  # not an allowlisted prefix
    ],
)
def test_uncacheable_requests_always_reach_the_app(method, path):
    client, _, calls, _ = _make()
    client.request(method, path)
    client.request(method, path)
    assert len(calls) == 2


def test_oversized_bodies_are_not_stored():
    client, mw, calls, _ = _make(max_bytes=1000, max_entry_bytes=100)
    client.get("/taxonomy/tree/search?size=101")
    client.get("/taxonomy/tree/search?size=101")
    assert len(calls) == 2 and mw._bytes == 0


def test_lru_eviction_keeps_total_under_budget():
    client, mw, calls, _ = _make(max_bytes=250, max_entry_bytes=100)
    for q in ("a", "b", "c"):
        client.get(f"/taxonomy/tree/search?size=100&q={q}")
    assert mw._bytes <= 250
    client.get("/taxonomy/tree/search?size=100&q=c")  # newest: still cached
    assert len(calls) == 3
    client.get("/taxonomy/tree/search?size=100&q=a")  # oldest: evicted
    assert len(calls) == 4


def test_zero_budget_disables():
    client, _, calls, _ = _make(max_bytes=0)
    client.get("/taxonomy/tree/search")
    client.get("/taxonomy/tree/search")
    assert len(calls) == 2


def test_real_app_cache_hit_matches_and_keeps_cors(client):
    url = "/taxonomy/tree/search?query=contract"
    headers = {"Origin": "https://example.org"}
    first = client.get(url, headers=headers)
    second = client.get(url, headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.content == first.content
    assert second.headers.get("access-control-allow-origin") == "*"


def test_real_app_class_details_cached(client):
    first = client.get("/taxonomy/class-details/RCIPwpgRpMs1eVz4vPid0pV")
    second = client.get("/taxonomy/class-details/RCIPwpgRpMs1eVz4vPid0pV")
    assert first.status_code == 200 and second.content == first.content


def test_cache_hits_are_still_rate_limited():
    from folio_api.rate_limit import RateLimitConfig, RateLimitMiddleware

    calls = []

    async def ok(request):
        calls.append(1)
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/search/prefix", ok)])
    app.add_middleware(ResponseCacheMiddleware)  # innermost, as in folio_api.api
    app.add_middleware(RateLimitMiddleware, config=RateLimitConfig({"tiers": {"/search/": ["2/minute"]}}))
    client = TestClient(app)
    statuses = [client.get("/search/prefix?query=co").status_code for _ in range(3)]
    assert statuses == [200, 200, 429]
    assert len(calls) == 1  # second 200 was a cache hit


def test_real_app_cache_hit_keeps_template_context(client):
    url = "/properties/property-details/R3zM4v3AKS03zKslpmcdLP"
    first = client.get(url)
    second = client.get(url)
    assert second.content == first.content
    assert second.template.name == first.template.name
    assert second.context.keys() == first.context.keys()
