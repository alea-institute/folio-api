"""Isolated Explorer fixture server implemented through Playwright routing.

No API import, runtime configuration, live ontology, or network server is needed.
"""

import asyncio
from collections import Counter
from dataclasses import dataclass, field
from html import escape
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
import unittest

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "https://explorer.test"
IRI_PREFIX = "https://example.test/"


def iri(name):
    return IRI_PREFIX + name


def canon_iri(name):
    prefix, local = name.split("-", 1)
    namespace = "concepts" if prefix == "c" else "relations"
    return f"https://{namespace}.canon.test/ns#{local}"


@dataclass
class RequestBarrier:
    """Hold one matching response until the test explicitly releases it."""

    contains: str
    started: asyncio.Event = field(default_factory=asyncio.Event)
    released: asyncio.Event = field(default_factory=asyncio.Event)

    async def wait(self):
        await asyncio.wait_for(self.started.wait(), 5)

    def release(self):
        self.released.set()


class ExplorerFixtures:
    def __init__(self, ontology_key="folio"):
        self.ontology_key = ontology_key
        self.iri = canon_iri if ontology_key == "canon" else iri
        self.canon_state = "ready"
        self.document_ontologies = {}
        self.requests = Counter()
        self.unexpected = []
        self.barriers = []
        self.failures = []
        tailwind_path = os.environ.get("FOLIO_BROWSER_TAILWIND")
        self.tailwind = Path(tailwind_path).read_bytes() if tailwind_path else b""
        self.nodes = {}
        self.roots = {}
        for section, prefix, noun in (
            ("class", "c", "Concept"),
            ("property", "p", "Relation"),
        ):
            definitions = {
                "root": (f"{noun} Topics", ["alpha", "context", "shared"]),
                "other": (f"Other {noun} Topics", ["beta", "shared"]),
                "alpha": (f"Alpha {noun}", ["alpha-child"]),
                "alpha-child": (f"Nested {noun}", []),
                "context": (f"Context {noun}", ["context-child"]),
                "context-child": (f"Retained {noun}", []),
                "beta": (f"Beta {noun}", []),
                "shared": (f"Shared {noun}", ["deep"]),
                "deep": (f"Deep {noun}", []),
            }
            self.roots[section] = [
                self.iri(f"{prefix}-root"),
                self.iri(f"{prefix}-other"),
            ]
            for suffix, (label, children) in definitions.items():
                identity = self.iri(f"{prefix}-{suffix}")
                self.nodes[identity] = {
                    "id": identity,
                    "label": label,
                    "type": section,
                    "children": [self.iri(f"{prefix}-{child}") for child in children],
                }
        for identity, node in self.nodes.items():
            node["parents"] = [
                parent
                for parent, data in self.nodes.items()
                if identity in data["children"]
            ]
        env = Environment(
            loader=FileSystemLoader(ROOT / "folio_api/templates/jinja2"),
            autoescape=select_autoescape(),
        )
        self.template = env.get_template("explore/tree.html")
        self.canon = ExplorerFixtures("canon") if ontology_key == "folio" else None

    def html(self, ontology_key):
        return self.template.render(
            asset_version="browser-fixture",
            typeahead_js_source="",
            config={"folio": {"branch": "synthetic browser fixture"}},
            ontology_key=ontology_key,
            canon_state=self.canon_state,
            tree_status=(
                "Canon unavailable"
                if ontology_key == "canon" and self.canon_state != "ready"
                else None
            ),
        )

    def hold(self, contains):
        barrier = RequestBarrier(contains)
        self.barriers.append(barrier)
        return barrier

    def fail_next(self, contains, status=503):
        self.failures.append((contains, status))

    def resolve(self, value):
        if self.ontology_key == "canon":
            return value
        return value if value in self.nodes else iri(value)

    def children(self, identity, section):
        identities = (
            self.roots[section]
            if identity == "#"
            else self.nodes.get(identity, {}).get("children", [])
        )
        return [
            {
                "id": child,
                "text": self.nodes[child]["label"],
                "children": bool(self.nodes[child]["children"]),
            }
            for child in identities
        ]

    def search(self, query, section):
        prefix = "c" if section == "class" else "p"
        query = query.lower()
        if query not in ("alpha", "beta", "shared"):
            return {
                "matches": [],
                "tree": {"root_nodes": [], "nodes": {}, "hidden_root_count": 2},
            }
        hit = self.iri(f"{prefix}-{query}")
        parents = self.nodes[hit]["parents"]
        nodes = {}
        for identity in [*parents, hit]:
            source = self.nodes[identity]
            nodes[identity] = {
                "id": identity,
                "label": source["label"],
                "preferred_label": None,
                "children": [hit] if identity in parents else [],
                "is_match": identity == hit,
                "match_field": "label" if identity == hit else None,
                "child_count": len(source["children"]),
            }
        return {
            "matches": [{"iri": hit, "label": self.nodes[hit]["label"]}],
            "tree": {
                "root_nodes": parents,
                "nodes": nodes,
                "hidden_root_count": 2 - len(parents),
            },
        }

    def node_data(self, identity):
        node = self.nodes[identity]
        return {
            "iri": identity,
            "label": node["label"],
            "definition": "Synthetic browser fixture.",
            "parents": [
                {"iri": parent, "label": self.nodes[parent]["label"]}
                for parent in node["parents"]
            ],
        }

    def graph(self, identity):
        selected = self.nodes[identity]
        parents = selected["parents"]

        def graph_node(key):
            node = self.nodes[key]
            return {
                "iri": key,
                "label": node["label"],
                "type": node["type"],
                "child_count": len(node["children"]),
                "branch_root_type": "ultimate" if not node["parents"] else None,
            }

        return {
            "selected": graph_node(identity),
            "ancestors": [graph_node(key) for key in parents],
            "nodes": [graph_node(key) for key in [*parents, identity]],
            "edges": [
                {"source": parent, "target": identity, "relationship": "subClassOf"}
                for parent in parents
            ],
            "children": [graph_node(key) for key in selected["children"]],
        }

    async def route(self, route):
        request = route.request
        parsed = urlsplit(request.url)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        key = path + ("?" + parsed.query if parsed.query else "")
        self.requests[key] += 1
        document_ontology = self.document_ontologies.get(request.frame, "folio")
        fixture = self.canon if document_ontology == "canon" else self
        if path.startswith(("/taxonomy/", "/properties/", "/explore/api/")):
            requested_ontology = query.get("ontology", ["folio"])[0]
            if requested_ontology != document_ontology or (
                document_ontology == "canon" and path.startswith("/explore/api/")
            ):
                self.unexpected.append(request.url)
                await route.abort()
                return
        status, content_type, body = 200, "application/json", None
        if parsed.netloc == "cdn.tailwindcss.com":
            # Serve the existing CDN dependency from the explicit local cache.
            content_type, body = "application/javascript", self.tailwind
        elif parsed.netloc in ("fonts.googleapis.com", "fonts.gstatic.com"):
            content_type, body = "text/css", ""
        elif parsed.netloc != urlsplit(ORIGIN).netloc:
            self.unexpected.append(request.url)
            await route.abort()
            return
        elif path == "/explore/tree":
            ontology_key = query.get("ontology", ["folio"])[0].lower()
            self.document_ontologies[request.frame] = ontology_key
            content_type, body = "text/html", self.html(ontology_key)
        elif path.startswith("/static/"):
            asset = ROOT / "folio_api" / path.lstrip("/")
            if asset.is_file() and asset.resolve().is_relative_to(
                ROOT / "folio_api/static"
            ):
                content_type, body = (
                    mimetypes.guess_type(asset.name)[0] or "application/octet-stream",
                    asset.read_bytes(),
                )
        elif path.startswith("/explore/api/entity-graph/"):
            identity = self.resolve(path.removeprefix("/explore/api/entity-graph/"))
            if identity in self.nodes:
                body = self.graph(identity)
        elif path.startswith(("/taxonomy/", "/properties/")):
            section = "class" if path.startswith("/taxonomy/") else "property"
            if path.endswith("/tree/data"):
                body = fixture.children(query.get("node_id", ["#"])[0], section)
            elif path.endswith("/tree/search"):
                body = fixture.search(query.get("query", [""])[0], section)
            elif "/tree/path/" in path:
                identity = fixture.resolve(path.split("/tree/path/", 1)[1])
                chain = [identity]
                while fixture.nodes.get(chain[0], {}).get("parents"):
                    chain.insert(0, fixture.nodes[chain[0]]["parents"][0])
                if (
                    identity in fixture.nodes
                    and fixture.nodes[identity]["type"] == section
                ):
                    body = {
                        "path": [
                            {
                                "iri": key,
                                "label": fixture.nodes[key]["label"],
                                "id": key.rsplit("/", 1)[-1],
                            }
                            for key in chain
                        ]
                    }
                else:
                    status, body = 404, {"detail": "Not found"}
            elif "/tree/node/" in path:
                identity = fixture.resolve(path.split("/tree/node/", 1)[1])
                if (
                    identity in fixture.nodes
                    and fixture.nodes[identity]["type"] == section
                ):
                    body = fixture.node_data(identity)
                else:
                    status, body = 404, {"detail": "Not found"}
            elif "/class-details/" in path or "/property-details/" in path:
                endpoint = (
                    "/class-details/" if section == "class" else "/property-details/"
                )
                identity = fixture.resolve(path.split(endpoint, 1)[1])
                if (
                    identity in fixture.nodes
                    and fixture.nodes[identity]["type"] == section
                ):
                    node = fixture.nodes[identity]
                    content_type = "text/html"
                    body = f'<article data-details-iri="{escape(identity)}"><h3>{escape(node["label"])}</h3><p>Synthetic browser fixture.</p><a href="#" onclick="event.preventDefault(); selectNodeByIri(\'{fixture.iri("p-beta")}\')">Related Beta Relation</a></article>'
                else:
                    status, body = 404, {"detail": "Not found"}
        if body is None:
            self.unexpected.append(request.url)
            await route.abort()
            return
        for failure in list(self.failures):
            if failure[0] in key:
                self.failures.remove(failure)
                status, content_type, body = (
                    failure[1],
                    "application/json",
                    {"detail": "Fixture failure"},
                )
                break
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        for barrier in self.barriers:
            if barrier.contains in key and not barrier.started.is_set():
                barrier.started.set()
                await barrier.released.wait()
                break
        try:
            await route.fulfill(status=status, content_type=content_type, body=body)
        except Exception:
            if not request.frame.page.is_closed():
                raise


class ExplorerBrowserCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.playwright = await async_playwright().start()
        self.addAsyncCleanup(self.playwright.stop)
        self.browser = await self.playwright.chromium.launch()
        self.addAsyncCleanup(self.browser.close)
        self.context = await self.browser.new_context(
            viewport={"width": 1440, "height": 1000}, service_workers="block"
        )
        self.addAsyncCleanup(self.context.close)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(5000)
        self.fixtures = ExplorerFixtures()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        await self.context.route("**/*", self.fixtures.route)

    async def asyncTearDown(self):
        for barrier in self.fixtures.barriers:
            barrier.release()
        self.assertEqual(
            self.fixtures.unexpected, [], "Unexpected browser network requests"
        )
        self.assertEqual(self.errors, [], "Uncaught browser JavaScript errors")

    async def open(self, suffix=""):
        await self.page.goto(ORIGIN + "/explore/tree" + suffix)
        await expect(self.page.locator("#class-tree-root > .tree-node")).to_have_count(
            2
        )
        await expect(
            self.page.locator("#property-tree-root > .tree-node")
        ).to_have_count(2)

    def node(self, name, within=None):
        container = within if within is not None else self.page
        return container.locator(f'.tree-node[data-id="{iri(name)}"]')

    async def search(self, query):
        await self.page.locator("#explore-search-input").fill(query)
        await self.page.locator("#explore-search-input").press("Enter")
        await expect(self.page.locator("#search-match-count")).to_have_text(
            "2 matches (1 class, 1 property)"
        )
        await expect(
            self.page.locator(".tree-node-match > .node-content > .node-label").first
        ).to_contain_text(query.capitalize())

    async def selected(self, name):
        await expect(self.page.locator(".tree-node.selected")).to_have_count(1)
        await expect(self.page.locator(".tree-node.selected")).to_have_attribute(
            "data-id", iri(name)
        )
        await expect(
            self.page.locator("#class-details [data-details-iri]")
        ).to_have_attribute("data-details-iri", iri(name))

    async def screenshot(self, name):
        if os.environ.get("FOLIO_BROWSER_SCREENSHOTS") == "1":
            self.assertTrue(
                self.fixtures.tailwind, "Screenshots require FOLIO_BROWSER_TAILWIND"
            )
            destination = ROOT / "docs/plans/evidence" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(
                path=str(destination), full_page=True, animations="disabled"
            )
