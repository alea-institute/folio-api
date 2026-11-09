"""In-process cache of rendered responses for the explorer's read-only routes.

Every route listed in ``CACHED_PREFIXES`` is a pure function of the request
URL and the ontologies loaded at startup (which never change while the
process runs), but each response is rebuilt on the event loop per request:
``/taxonomy/tree/search`` with a short query is ~75 ms locally (several
hundred ms on prod), and a large ``class-details`` fragment ~8 ms. When a
presenter says "now search for *contract*", every attendee sends the same
URL, so caching the finished bytes turns repeats into a dict lookup.

Safety rules:
  * GET only; only ``200`` responses without ``Set-Cookie`` are stored.
  * The key is (Host, path, raw query string, canon load state), so a
    response rendered while Canon was still loading is never served after.
  * LRU bounded by total body bytes; bodies over ``max_entry_bytes`` are not
    stored. ``max_bytes = 0`` disables the cache.
  * Pure ASGI (no ``BaseHTTPMiddleware``), registered innermost so rate
    limiting and CORS still apply to cache hits; it is single-threaded on
    the event loop, so no locking is needed.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

CACHED_PREFIXES: tuple[str, ...] = (
    "/taxonomy/tree/",  # data, node, path, search
    "/taxonomy/class-details/",
    "/properties/tree/",  # data, node, path, search
    "/properties/property-details/",
    "/explore/api/entity-graph/",
    "/search/prefix",
)

DEFAULT_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_ENTRY_BYTES = 8 * 1024 * 1024

# (status, headers, body, debug message or None)
_Entry = tuple[int, list[tuple[bytes, bytes]], bytes, "Message | None"]


class ResponseCacheMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_entry_bytes: int = DEFAULT_MAX_ENTRY_BYTES,
        prefixes: tuple[str, ...] = CACHED_PREFIXES,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.max_entry_bytes = min(max_entry_bytes, max_bytes)
        self.prefixes = prefixes
        self._entries: "OrderedDict[tuple, _Entry]" = OrderedDict()
        self._bytes = 0
        self.hits = 0
        self.misses = 0

    def _key(self, scope: Scope) -> tuple | None:
        if scope["type"] != "http" or scope["method"] != "GET" or self.max_bytes <= 0:
            return None
        path: str = scope["path"]
        if not path.startswith(self.prefixes):
            return None
        host = next((v for k, v in scope["headers"] if k == b"host"), b"")
        app = scope.get("app")
        registry = getattr(getattr(app, "state", None), "ontologies", None)
        canon_state = getattr(registry, "canon_state", None)
        return (host, path, scope.get("query_string", b""), canon_state)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        key = self._key(scope)
        if key is None:
            await self.app(scope, receive, send)
            return

        entry = self._entries.get(key)
        if entry is not None:
            self._entries.move_to_end(key)
            self.hits += 1
            status, headers, body, debug = entry
            if debug is not None:
                # Test clients' template introspection (only sent when the
                # server advertises the "http.response.debug" extension).
                await send(debug)
            await send({"type": "http.response.start", "status": status, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return

        self.misses += 1
        start: dict[str, Any] = {}
        debug: Message | None = None
        chunks: list[bytes] = []
        size = 0
        cacheable = True

        async def capture(message: Message) -> None:
            nonlocal size, cacheable, debug
            if message["type"] == "http.response.debug":
                debug = message
            elif message["type"] == "http.response.start":
                start.update(message)
                headers = message.get("headers", [])
                if message["status"] != 200 or any(k.lower() == b"set-cookie" for k, _ in headers):
                    cacheable = False
            elif message["type"] == "http.response.body" and cacheable:
                body = message.get("body", b"")
                size += len(body)
                if size > self.max_entry_bytes:
                    cacheable = False
                    chunks.clear()
                else:
                    chunks.append(body)
                if not message.get("more_body", False) and cacheable:
                    self._store(
                        key, start["status"], list(start.get("headers", [])), b"".join(chunks), debug
                    )
            await send(message)

        await self.app(scope, receive, capture)

    def _store(
        self, key: tuple, status: int, headers: list, body: bytes, debug: Message | None
    ) -> None:
        old = self._entries.pop(key, None)
        if old is not None:
            self._bytes -= len(old[2])
        self._entries[key] = (status, headers, body, debug)
        self._bytes += len(body)
        while self._bytes > self.max_bytes and self._entries:
            _, (_, _, evicted, _) = self._entries.popitem(last=False)
            self._bytes -= len(evicted)
