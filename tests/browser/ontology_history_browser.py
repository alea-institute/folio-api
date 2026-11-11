"""History remains inside the ontology owned by each rendered document."""

from urllib.parse import parse_qs, quote, unquote, urlsplit

from playwright.async_api import expect
from support import ExplorerBrowserCase, ORIGIN, canon_iri, iri


class OntologyHistoryBrowserTests(ExplorerBrowserCase):
    async def settled(self):
        await expect(self.page.locator("#explore-tree")).to_have_attribute(
            "aria-busy", "false"
        )

    def canon_node(self, name):
        return self.page.locator(f'.tree-node[data-id="{canon_iri(name)}"]')

    async def canon_selected(self, name):
        await self.settled()
        await expect(self.page.locator(".tree-node.selected")).to_have_count(1)
        await expect(self.page.locator(".tree-node.selected")).to_have_attribute(
            "data-id", canon_iri(name)
        )
        await expect(self.page.locator("[data-details-iri]")).to_have_attribute(
            "data-details-iri", canon_iri(name)
        )
        params = parse_qs(urlsplit(self.page.url).query)
        self.assertEqual(params["ontology"], ["canon"])
        self.assertEqual(params["node"], [canon_iri(name)])
        self.assertEqual(
            params["type"], ["class" if name.startswith("c-") else "property"]
        )

    async def test_canon_full_identifiers_survive_cross_type_links_and_history(self):
        await self.open("?ontology=canon")
        await self.search("beta")
        await self.canon_selected("c-beta")
        await self.page.get_by_role("link", name="Related Beta Relation").click()
        await self.canon_selected("p-beta")
        length = await self.page.evaluate("history.length")
        await self.page.go_back()
        await self.canon_selected("c-beta")
        await expect(self.page.locator("#explore-search-input")).to_have_value("beta")
        await self.page.go_forward()
        await self.canon_selected("p-beta")
        await expect(self.page.locator("#explore-search-input")).to_have_value("beta")
        self.assertEqual(await self.page.evaluate("history.length"), length)
        await expect(self.page.locator("#tab-graph")).to_have_count(0)
        for kind, endpoint, name in (
            ("taxonomy", "class-details", "c-beta"),
            ("properties", "property-details", "p-beta"),
        ):
            self.assertTrue(
                any(
                    key.startswith(f"/{kind}/{endpoint}/" + canon_iri(name))
                    for key in self.fixtures.requests
                )
            )

    async def test_canon_legacy_link_path_and_details_fallback_keep_namespace(self):
        for kind, name, detail in (
            ("class", "c-beta", "class-details"),
            ("property", "p-beta", "property-details"),
        ):
            with self.subTest(kind=kind):
                self.fixtures.fail_next("/" + detail + "/" + canon_iri(name))
                await self.page.goto(
                    ORIGIN
                    + "/explore/tree?ontology=canon&node="
                    + quote(canon_iri(name), safe="")
                    + "&type="
                    + kind
                )
                await self.settled()
                await expect(
                    self.page.locator(".tree-node.selected")
                ).to_have_attribute("data-id", canon_iri(name))
                await expect(self.page.locator("#class-details h3")).to_have_text(
                    self.fixtures.canon.nodes[canon_iri(name)]["label"]
                )
                self.assertTrue(
                    any(
                        "/tree/path/" + canon_iri(name) in key
                        for key in self.fixtures.requests
                    )
                )
                self.assertTrue(
                    any(
                        "/tree/node/" + canon_iri(name) in key
                        for key in self.fixtures.requests
                    )
                )
                await self.search("alpha")
                await self.page.go_back()
                await self.canon_selected(name)

    async def test_ontology_switch_opens_roots_and_traverses_saved_documents(self):
        await self.open()
        await self.search("alpha")
        await self.node("c-alpha").locator(
            ":scope > .node-content > .expand-icon"
        ).click()
        await expect(self.node("c-alpha-child")).to_be_visible()
        await self.node("c-alpha-child").locator(":scope > .node-content").click()
        await self.selected("c-alpha-child")
        await self.page.get_by_role(
            "link", name="Switch to the Catholic Semantic Canon"
        ).click()
        await self.settled()
        await expect(self.page.locator("h1")).to_have_text("Catholic Semantic Canon")
        await expect(self.page.locator("[data-ontology]")).to_have_attribute(
            "data-ontology", "canon"
        )
        await expect(self.page.locator("#explore-search-input")).to_have_value("")
        await expect(self.page.locator(".tree-node.selected")).to_have_count(0)
        await expect(self.canon_node("c-root")).to_be_visible()
        await expect(self.page.locator("#tab-graph")).to_have_count(0)
        await expect(
            self.page.get_by_role("link", name="Switch to FOLIO")
        ).to_be_visible()
        length = await self.page.evaluate("history.length")
        await self.page.go_back()
        await self.settled()
        await expect(self.page.locator("h1")).to_have_text("FOLIO Ontology Explorer")
        await expect(self.page.locator("[data-ontology]")).to_have_attribute(
            "data-ontology", "folio"
        )
        await self.selected("c-alpha-child")
        await expect(self.node("c-alpha-child")).to_be_visible()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await self.page.locator("#tab-graph").click()
        await expect(self.page.locator(".graph-node-selected")).to_have_attribute(
            "data-iri", iri("c-alpha-child")
        )
        await self.page.go_forward()
        await self.settled()
        await expect(self.page.locator("h1")).to_have_text("Catholic Semantic Canon")
        await expect(self.canon_node("c-root")).to_be_visible()
        await expect(self.page.locator("#explore-search-input")).to_have_value("")
        await expect(self.page.locator(".tree-node.selected")).to_have_count(0)
        await expect(self.page.locator("#tab-graph")).to_have_count(0)
        self.assertEqual(await self.page.evaluate("history.length"), length)

    async def test_clear_and_collapse_keep_canon_and_unrelated_parameters(self):
        await self.open("?ontology=canon&source=history-test")
        for control in ("#explore-search-clear", "#collapse-all-tree"):
            with self.subTest(control=control):
                await self.search("alpha")
                await self.canon_selected("c-alpha")
                await self.page.locator(control).click()
                await self.settled()
                if control == "#explore-search-clear":
                    await expect(
                        self.page.locator(".tree-node.selected")
                    ).to_have_count(0)
                else:
                    await expect(self.canon_node("c-alpha")).to_be_hidden()
                self.assertEqual(
                    parse_qs(urlsplit(self.page.url).query),
                    {"ontology": ["canon"], "source": ["history-test"]},
                )
                if control == "#explore-search-clear":
                    length = await self.page.evaluate("history.length")
                    await self.page.go_back()
                    await self.canon_selected("c-alpha")
                    await self.page.go_forward()
                    await self.settled()
                    self.assertIsNone(
                        await self.page.evaluate(
                            "history.state.folioExplorer.selection"
                        )
                    )
                    self.assertEqual(await self.page.evaluate("history.length"), length)
                else:
                    destination = await self.page.evaluate("history.state")
                    await self.search("beta")
                    await self.page.go_back()
                    await self.settled()
                    await expect(self.canon_node("c-alpha")).to_be_hidden()
                    self.assertEqual(
                        await self.page.evaluate("history.state"), destination
                    )
                    self.assertNotIn("node", parse_qs(urlsplit(self.page.url).query))

    async def test_restoring_snapshot_normalizes_url_without_overwriting_state(self):
        for selector in ("folio", "canon"):
            with self.subTest(ontology=selector):
                await self.open("?ontology=" + selector + "&source=history-test")
                await self.search("alpha")
                await self.settled()
                # Emulate an older entry with the same view but a redundant or
                # noncanonical ontology selector. Traversal must keep the snapshot.
                await self.page.evaluate(
                    "selector => { const url = new URL(location); url.searchParams.set('ontology', selector.toUpperCase()); history.replaceState(history.state, '', url); }",
                    selector,
                )
                destination = await self.page.evaluate("history.state")
                await self.page.evaluate("history.pushState(null, '', location.href)")
                length = await self.page.evaluate("history.length")
                await self.page.go_back()
                await self.settled()
                params = parse_qs(urlsplit(self.page.url).query)
                self.assertEqual(
                    params.get("ontology"), ["canon"] if selector == "canon" else None
                )
                self.assertEqual(params["source"], ["history-test"])
                self.assertEqual(await self.page.evaluate("history.state"), destination)
                self.assertEqual(await self.page.evaluate("history.length"), length)
                await self.page.evaluate(
                    "selector => { const url = new URL(location); url.searchParams.set('ontology', selector.toUpperCase()); history.replaceState(history.state, '', url); }",
                    selector,
                )
                await self.page.reload()
                await self.settled()
                self.assertEqual(await self.page.evaluate("history.state"), destination)
                self.assertEqual(
                    parse_qs(urlsplit(self.page.url).query).get("ontology"),
                    ["canon"] if selector == "canon" else None,
                )

    async def test_blocked_canon_keeps_status_and_starts_no_history_requests(self):
        for state in ("loading", "unavailable"):
            with self.subTest(state=state):
                self.fixtures.canon_state = state
                await self.page.goto(
                    ORIGIN + "/explore/tree?ontology=canon&node=missing&type=class"
                )
                await expect(self.page.locator("[data-ontology]")).to_have_attribute(
                    "data-tree-state", "blocked"
                )
                await expect(
                    self.page.locator("#explore-tree [role=status]")
                ).to_have_text("Catholic Semantic Canon is " + state)
                for control in (
                    "#explore-search-input",
                    "#explore-search-button",
                    "#expand-all-tree",
                    "#collapse-all-tree",
                ):
                    await expect(self.page.locator(control)).to_be_disabled()
                await expect(self.page.locator("#tab-graph")).to_have_count(0)
                self.assertIsNone(await self.page.evaluate("history.state"))
                self.assertFalse(
                    any(
                        key.startswith(("/taxonomy/", "/properties/", "/explore/api/"))
                        for key in self.fixtures.requests
                    )
                )

    async def test_delayed_canon_details_cannot_replace_history_destination(self):
        await self.open("?ontology=canon")
        await self.search("alpha")
        await self.canon_selected("c-alpha")
        barrier = self.fixtures.hold("/class-details/" + canon_iri("c-beta"))
        await self.search("beta")
        await barrier.wait()
        await self.page.go_back()
        await self.settled()
        destination = await self.page.evaluate("history.state")
        async with self.page.expect_response(
            lambda response: barrier.contains in unquote(response.url)
        ):
            barrier.release()
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await self.canon_selected("c-alpha")
        self.assertEqual(await self.page.evaluate("history.state"), destination)
        await self.page.go_forward()
        await self.canon_selected("c-beta")
