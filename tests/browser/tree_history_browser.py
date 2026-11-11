"""Behavior checks through the real Explorer page and native browser history."""

import re
from urllib.parse import quote

from playwright.async_api import expect
from support import ExplorerBrowserCase, iri


class TreeHistoryBrowserTests(ExplorerBrowserCase):
    async def test_search_and_sibling_controls_for_both_sections(self):
        await self.open()
        await self.search("alpha")
        await self.selected("c-alpha")
        for prefix in ("c", "p"):
            with self.subTest(section=prefix):
                root = self.node(prefix + "-root")
                button = root.locator(
                    ":scope > .children-container > .siblings-row > button"
                )
                await button.focus()
                await button.press("Enter")
                context = self.node(prefix + "-context")
                await expect(context).to_be_visible()
                await expect(context).to_have_class(
                    "tree-node tree-node-context has-children collapsed"
                )
                await context.locator(":scope > .node-content > .expand-icon").click()
                await expect(self.node(prefix + "-context-child")).to_be_visible()
                await button.focus()
                await button.press("Space")
                await expect(context).to_be_hidden()
                await button.press("Enter")
                await expect(self.node(prefix + "-context-child")).to_be_visible()
        await self.node("c-alpha").locator(":scope > .node-content").click()
        await self.page.locator("#explore-search-input").blur()
        await self.page.keyboard.press("ArrowRight")
        await expect(self.node("c-alpha-child")).to_be_visible()
        await self.page.keyboard.press("ArrowLeft")
        await expect(self.node("c-alpha-child")).to_be_hidden()

    async def test_back_and_forward_restore_query_and_context(self):
        await self.restore_query_and_context("c", screenshots=True)

    async def test_property_back_and_forward_restore_query_and_context(self):
        await self.restore_query_and_context("p")

    async def restore_query_and_context(self, prefix, screenshots=False):
        await self.open()
        await self.search("alpha")
        button = self.node(prefix + "-root").locator(
            ":scope > .children-container > .siblings-row > button"
        )
        await button.click()
        await self.node(prefix + "-context").locator(
            ":scope > .node-content > .expand-icon"
        ).click()
        await self.node(prefix + "-context-child").locator(
            ":scope > .node-content"
        ).click()
        await self.selected(prefix + "-context-child")
        await self.search("beta")
        await self.selected("c-beta")
        await self.node(prefix + "-other").locator(
            ":scope > .children-container > .siblings-row > button"
        ).click()
        await self.expand(prefix + "-shared")
        await expect(self.node(prefix + "-deep")).to_be_visible()
        if prefix == "p":
            await self.choose("p-beta")
        length = await self.page.evaluate("history.length")
        await self.page.go_back()
        if prefix == "p":
            # Property selection is its own deliberate navigation after search.
            await self.selected("c-beta")
            await expect(self.node("p-deep")).to_be_visible()
            await self.page.go_back()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await self.selected(prefix + "-context-child")
        await expect(self.node(prefix + "-context-child")).to_be_visible()
        await expect(self.node(prefix + "-context")).to_have_class(
            re.compile("expanded")
        )
        await expect(self.node(prefix + "-root")).to_have_class(re.compile("expanded"))
        await expect(button).to_have_attribute("aria-expanded", "true")
        await expect(self.node(prefix + "-deep")).to_have_count(0)
        await expect(self.page.locator("#search-match-count")).to_have_text(
            "2 matches (1 class, 1 property)"
        )
        if screenshots:
            await self.screenshot("fa-5-tree-history-back.png")
        await self.page.go_forward()
        if prefix == "p":
            await self.selected("c-beta")
            await self.page.go_forward()
        await expect(self.page.locator("#explore-search-input")).to_have_value("beta")
        await self.selected(prefix + "-beta")
        await expect(self.node(prefix + "-other")).to_have_class(re.compile("expanded"))
        await expect(self.node(prefix + "-shared")).to_have_class(
            re.compile("expanded")
        )
        await expect(self.node(prefix + "-deep")).to_be_visible()
        await expect(self.node(prefix + "-context-child")).to_have_count(0)
        await expect(self.page.locator("#search-match-count")).to_have_text(
            "2 matches (1 class, 1 property)"
        )
        self.assertEqual(await self.page.evaluate("history.length"), length)
        if screenshots:
            await self.screenshot("fa-5-tree-history-forward.png")

    async def test_details_link_reveals_property_in_filtered_tree(self):
        await self.open()
        await self.search("alpha")
        await self.selected("c-alpha")
        await self.page.get_by_role("link", name="Related Beta Relation").click()
        await self.selected("p-beta")
        await expect(self.node("p-beta")).to_be_visible()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")

    async def test_details_navigation_scrolls_loaded_and_new_targets_into_view(self):
        await self.open()
        for index in range(60):
            identity = iri(f"c-extra-root-{index}")
            self.fixtures.nodes[identity] = {
                "id": identity,
                "label": f"Extra Concept {index}",
                "type": "class",
                "children": [],
                "parents": [],
            }
            self.fixtures.roots["class"].append(identity)
        await self.page.reload()
        await self.settled()
        await expect(self.page.locator("#class-tree-root > .tree-node")).to_have_count(
            62
        )
        target = self.node("p-beta").locator(":scope > .node-content")
        for loaded in (False, True):
            with self.subTest(target_already_loaded=loaded):
                await self.choose("c-root")
                if loaded:
                    await expect(target).not_to_be_in_viewport()
                else:
                    await expect(target).to_have_count(0)
                length = await self.page.evaluate("history.length")
                await self.page.get_by_role(
                    "link", name="Related Beta Relation"
                ).click()
                await self.selected("p-beta")
                await expect(target).to_be_in_viewport()
                self.assertEqual(await self.page.evaluate("history.length"), length + 1)
        with self.subTest(legacy_node_link=True):
            await self.page.evaluate(
                "iri => history.replaceState(null, '', '?node=' + encodeURIComponent(iri) + '&type=property')",
                iri("p-beta"),
            )
            await self.page.reload()
            await self.settled()
            await self.selected("p-beta")
            await expect(target).to_be_in_viewport()

    async def test_legacy_links_outside_curated_roots_restore_details_and_graph(self):
        for kind, prefix in (("class", "c"), ("property", "p")):
            with self.subTest(section=kind):
                self.fixtures.roots[kind].remove(iri(prefix + "-other"))
                target = iri(prefix + "-beta")
                await self.page.goto(
                    "https://explorer.test/explore/tree?node="
                    + quote(target, safe="")
                    + "&type="
                    + kind
                )
                await self.settled()
                details = self.page.locator("#class-details [data-details-iri]")
                await expect(details).to_have_attribute("data-details-iri", target)
                await expect(self.node(prefix + "-other")).to_have_count(0)
                await expect(self.page.locator(".tree-node.selected")).to_have_count(0)
                await self.page.locator("#tab-graph").click()
                graph = self.page.locator(".graph-node-selected")
                await expect(graph).to_have_attribute("data-iri", target)
                await self.choose("c-root")
                length = await self.page.evaluate("history.length")
                await self.page.go_back()
                await self.settled()
                await expect(details).to_have_attribute("data-details-iri", target)
                await expect(graph).to_have_attribute("data-iri", target)
                await expect(self.node(prefix + "-other")).to_have_count(0)
                self.assertEqual(await self.page.evaluate("history.length"), length)
                await self.page.reload()
                await self.settled()
                await expect(details).to_have_attribute("data-details-iri", target)
                await self.page.locator("#tab-graph").click()
                await expect(graph).to_have_attribute("data-iri", target)
                await self.page.go_forward()
                await self.settled()
                await self.selected("c-root")
                await expect(graph).to_have_attribute("data-iri", iri("c-root"))

    async def test_details_link_outside_curated_roots_survives_history_and_clear(self):
        self.fixtures.roots["property"].remove(iri("p-other"))
        await self.page.goto("https://explorer.test/explore/tree")
        await self.settled()
        await self.choose("c-root")
        length = await self.page.evaluate("history.length")
        await self.page.get_by_role("link", name="Related Beta Relation").click()
        details = self.page.locator("#class-details [data-details-iri]")
        await expect(details).to_have_attribute("data-details-iri", iri("p-beta"))
        self.assertEqual(await self.page.evaluate("history.length"), length + 1)
        await self.page.go_back()
        await self.settled()
        await self.selected("c-root")
        await self.page.go_forward()
        await self.settled()
        await expect(details).to_have_attribute("data-details-iri", iri("p-beta"))
        await self.search("alpha")
        await self.page.locator("#explore-search-input").press("Escape")
        await self.settled()
        await expect(details).to_have_count(0)
        self.assertIsNone(
            await self.page.evaluate("history.state.folioExplorer.selection")
        )

    async def test_hidden_retained_children_and_collapsed_section_survive(self):
        await self.open()
        await self.search("alpha")
        for prefix in ("c", "p"):
            row = self.node(prefix + "-root").locator(
                ":scope > .children-container > .siblings-row > button"
            )
            await row.click()
            await self.expand(prefix + "-context")
            await expect(self.node(prefix + "-context-child")).to_be_visible()
            await row.click()
        await self.page.locator('.section-header[data-section="property"]').click()
        await self.search("beta")
        await self.page.go_back()
        await self.settled()
        await expect(self.page.locator("#property-tree-root")).to_be_hidden()
        await self.page.locator('.section-header[data-section="property"]').click()
        for prefix in ("c", "p"):
            context = self.node(prefix + "-context")
            await expect(context).to_be_hidden()
            before = sum(self.fixtures.requests.values())
            await self.node(prefix + "-root").locator(
                ":scope > .children-container > .siblings-row > button"
            ).click()
            await expect(self.node(prefix + "-context-child")).to_be_visible()
            self.assertEqual(sum(self.fixtures.requests.values()), before)

    async def test_duplicate_occurrences_and_hidden_selection(self):
        await self.open("?keep=yes#anchor")
        await self.search("shared")
        left = self.node("c-root")
        right = self.node("c-other")
        await self.expand("c-shared", left)
        await self.choose("c-deep", left)
        await self.page.locator("#collapse-all-tree").click()
        await expect(self.node("c-deep", left)).to_be_hidden()
        await expect(self.page).not_to_have_url(re.compile("node="))
        await self.search("beta")
        await self.page.go_back()
        await self.settled()
        await self.selected("c-deep")
        await expect(self.node("c-deep", left)).to_be_hidden()
        await expect(self.node("c-shared", right)).to_have_class(
            re.compile("collapsed")
        )
        await expect(self.node("c-deep", right)).to_have_count(0)
        self.assertIn("keep=yes", self.page.url)
        self.assertTrue(self.page.url.endswith("#anchor"))

    async def test_search_clear_escape_empty_zero_results_and_forward_branch(self):
        await self.open()
        await self.search("alpha")
        length = await self.page.evaluate("history.length")
        await self.search("alpha")
        await self.choose("c-alpha")
        self.assertEqual(await self.page.evaluate("history.length"), length)
        await self.search("beta")
        for action in ("clear", "escape", "empty", "zero"):
            with self.subTest(action=action):
                field = self.page.locator("#explore-search-input")
                if action == "clear":
                    await self.page.locator("#explore-search-clear").click()
                elif action == "escape":
                    await field.press("Escape")
                else:
                    await field.fill("no matches" if action == "zero" else "")
                    await field.press("Enter")
                await self.settled()
                await expect(field).to_have_value("")
                await expect(self.page.locator(".tree-node.selected")).to_have_count(0)
                await self.page.go_back()
                await self.settled()
                await expect(field).to_have_value("beta")
                await self.selected("c-beta")
        await self.page.go_back()
        await self.settled()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await self.choose("p-alpha")
        current = self.page.url
        await self.page.go_forward()
        self.assertEqual(self.page.url, current)

    async def test_initial_null_legacy_invalid_state_and_reload(self):
        await self.open("?node=" + iri("p-alpha-child") + "&type=property")
        await self.settled()
        await self.selected("p-alpha-child")
        await self.search("alpha")
        await self.page.reload()
        await self.settled()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await self.selected("c-alpha")
        await self.page.go_back()
        await self.settled()
        await self.selected("p-alpha-child")
        for state in (
            None,
            {"nodeId": iri("c-alpha"), "type": "class"},
            {"folioExplorer": {"version": 999}},
            {"folioExplorer": {"version": 1, "query": [], "sections": {}}},
        ):
            await self.page.evaluate(
                "state => history.replaceState(state, '', '/explore/tree?node=c-alpha&type=invalid')",
                state,
            )
            await self.page.evaluate(
                "history.pushState({}, '', '/explore/tree?node=c-beta')"
            )
            await self.page.go_back()
            await self.settled()
            await self.selected("c-alpha")

    async def test_gestures_preserve_envelope_and_add_no_history_entries(self):
        await self.open("?keep=yes#anchor")
        await self.page.evaluate(
            "history.replaceState({...history.state, unrelated: {retained: true}}, '')"
        )
        await self.search("alpha")
        before = await self.page.evaluate("history.length")
        await self.expand("c-alpha")
        await expect(self.node("c-alpha-child")).to_be_visible()
        await self.page.locator("#expand-all-tree").click()
        await self.page.locator("#collapse-all-tree").click()
        await self.page.locator('.section-header[data-section="class"]').click()
        self.assertEqual(await self.page.evaluate("history.length"), before)
        self.assertEqual(
            await self.page.evaluate("history.state.unrelated"), {"retained": True}
        )
        await self.page.go_back()
        await self.settled()
        await expect(self.page.locator("#explore-search-input")).to_have_value("")
        await expect(self.page.locator(".tree-node.selected")).to_have_count(0)

    async def test_missing_selected_branch_keeps_remaining_view(self):
        await self.open()
        await self.search("alpha")
        await self.expand("c-alpha")
        await self.choose("c-alpha-child")
        snapshot = await self.page.evaluate("history.state")
        await self.search("beta")
        self.fixtures.nodes[iri("c-alpha")]["children"] = []
        await self.page.go_back()
        await self.settled()
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "no longer available"
        )
        await expect(self.page.locator(".tree-node.selected")).to_have_count(0)
        await expect(self.node("p-alpha")).to_be_visible()
        self.assertEqual(await self.page.evaluate("history.state"), snapshot)

    async def test_full_tree_navigation_and_stale_path_response(self):
        await self.open()
        await self.expand("c-root")
        await self.choose("c-alpha")
        await self.page.locator("#class-details a").click()
        await self.selected("p-beta")
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")
        await expect(self.node("p-beta")).to_have_count(0)
        barrier = self.fixtures.hold("/properties/tree/path/p-beta")
        await self.page.locator("#class-details a").click()
        await barrier.wait()
        await self.search("alpha")
        await self.release_response(barrier)
        await self.selected("c-alpha")
        await expect(self.node("p-beta")).to_have_count(0)

    async def test_old_root_response_cannot_overwrite_new_search(self):
        barrier = self.fixtures.hold("/taxonomy/tree/data?node_id=%23")
        await self.page.goto("https://explorer.test/explore/tree")
        await barrier.wait()
        await self.search("alpha")
        await self.selected("c-alpha")
        await self.release_response(barrier)
        await expect(self.page.locator("#class-tree-root > .tree-node")).to_have_count(
            1
        )
        await self.selected("c-alpha")

    async def test_repeated_parent_requests_are_shared_during_restore(self):
        await self.open()
        await self.search("shared")
        for prefix in ("c", "p"):
            for parent in ("root", "other"):
                await self.expand(prefix + "-shared", self.node(prefix + "-" + parent))
                await expect(
                    self.node(prefix + "-deep", self.node(prefix + "-" + parent))
                ).to_be_visible()
        await self.search("beta")
        before = dict(self.fixtures.requests)
        await self.page.go_back()
        await self.settled()
        for prefix, endpoint in (("c", "taxonomy"), ("p", "properties")):
            key = (
                "/"
                + endpoint
                + "/tree/data?node_id="
                + quote(iri(prefix + "-shared"), safe="")
            )
            self.assertEqual(self.fixtures.requests[key] - before.get(key, 0), 1)
            await expect(self.node(prefix + "-deep")).to_have_count(2)

    async def test_large_retained_view_and_search_expand_limit(self):
        parents = []
        for index in range(60):
            identity = iri(f"c-extra-{index}")
            parents.append(identity)
            self.fixtures.nodes[identity] = {
                "id": identity,
                "label": f"Topic {index:02}",
                "type": "class",
                "children": [iri("c-shared")],
                "parents": [],
            }
        self.fixtures.nodes[iri("c-shared")]["parents"] = parents
        await self.open()
        await self.search("shared")
        await self.page.locator("#expand-all-tree").click()
        await expect(self.node("c-deep")).to_have_count(50)
        await expect(
            self.page.locator('.tree-node.collapsed[data-id="' + iri("c-shared") + '"]')
        ).to_have_count(10)
        await self.page.locator("#expand-all-tree").click()
        await expect(self.node("c-deep")).to_have_count(60)
        await self.search("beta")
        before = dict(self.fixtures.requests)
        await self.page.go_back()
        await self.settled()
        await expect(self.node("c-deep")).to_have_count(60)
        key = "/taxonomy/tree/data?node_id=" + quote(iri("c-shared"), safe="")
        self.assertEqual(self.fixtures.requests[key] - before.get(key, 0), 1)

    async def test_missing_legacy_node_does_not_leave_tree_locked(self):
        await self.open("?node=deleted&type=class")
        await self.settled()
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "no longer available"
        )
        await self.choose("c-root")

    async def test_only_one_duplicate_occurrence_is_expanded_on_return(self):
        await self.open()
        await self.search("shared")
        left = self.node("p-root")
        right = self.node("p-other")
        await self.expand("p-shared", left)
        await self.choose("p-deep", left)
        await self.search("beta")
        await self.page.go_back()
        await self.settled()
        await self.selected("p-deep")
        await expect(self.node("p-deep", left)).to_be_visible()
        await expect(self.node("p-deep", right)).to_have_count(0)
        await expect(self.node("p-shared", right)).to_have_class(
            re.compile("collapsed")
        )
        await expect(self.node("c-deep")).to_have_count(0)

    async def test_mobile_dark_history_preserves_property_selection(self):
        await self.page.set_viewport_size({"width": 390, "height": 844})
        await self.open()
        await self.page.evaluate("document.documentElement.classList.add('dark')")
        await self.search("alpha")
        await self.choose("p-alpha")
        await self.search("beta")
        await self.page.go_back()
        await self.settled()
        await self.selected("p-alpha")
        await expect(self.node("p-alpha")).to_be_visible()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await expect(self.page.locator("html")).to_have_class(re.compile("dark"))

    async def test_repeated_full_tree_expansion_shares_inflight_load(self):
        await self.open()
        key = "/taxonomy/tree/data?node_id=" + quote(iri("c-root"), safe="")
        barrier = self.fixtures.hold(key)
        await self.expand("c-root")
        await barrier.wait()
        await self.expand("c-root")
        await self.expand("c-root")
        await self.release_response(barrier)
        await self.choose("c-alpha")
        self.assertEqual(self.fixtures.requests[key], 1)

    async def test_details_navigation_opens_full_tree_destination_section(self):
        await self.open()
        await self.expand("c-root")
        await self.choose("c-alpha")
        await self.page.locator('.section-header[data-section="property"]').click()
        await expect(self.page.locator("#property-tree-root")).to_be_hidden()
        length = await self.page.evaluate("history.length")
        await self.page.locator("#class-details a").click()
        await self.selected("p-beta")
        await expect(self.node("p-beta")).to_be_visible()
        self.assertEqual(await self.page.evaluate("history.length"), length + 1)
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")
        await expect(self.page.locator("#property-tree-root")).to_be_hidden()

    async def test_empty_search_section_retains_revealed_root_siblings(self):
        original_search = self.fixtures.search
        self.fixtures.search = lambda query, section: (
            {
                "matches": [],
                "tree": {"root_nodes": [], "nodes": {}, "hidden_root_count": 2},
            }
            if query == "alpha" and section == "property"
            else original_search(query, section)
        )
        await self.open()
        await self.page.locator("#explore-search-input").fill("alpha")
        await self.page.locator("#explore-search-input").press("Enter")
        await self.selected("c-alpha")
        await self.page.locator("#class-details a").click()
        await self.selected("p-beta")
        row = self.page.locator("#property-tree-root > .siblings-row > button")
        await expect(row).to_be_visible()
        await row.click()
        await expect(self.node("p-beta")).to_be_hidden()
        await self.search("beta")
        await self.page.go_back()
        await self.settled()
        await self.selected("p-beta")
        await expect(self.node("p-beta")).to_be_hidden()
        await expect(row).to_be_visible()
        before = dict(self.fixtures.requests)
        await row.click()
        await expect(self.node("p-beta")).to_be_visible()
        self.assertEqual(dict(self.fixtures.requests), before)
        await expect(self.page.locator("#search-match-count")).to_have_text(
            "1 match in classes"
        )

    async def test_reselecting_same_node_retries_details_without_history_entry(self):
        await self.open()
        self.fixtures.fail_next("/taxonomy/class-details/c-alpha")
        self.fixtures.fail_next("/taxonomy/tree/node/c-alpha")
        await self.search("alpha")
        await expect(self.page.locator("#class-details")).to_contain_text(
            "Unable to load details"
        )
        length = await self.page.evaluate("history.length")
        await self.choose("c-alpha")
        self.assertEqual(await self.page.evaluate("history.length"), length)

    async def test_history_restores_unequal_match_counts_and_highlighted_hits(self):
        original_search = self.fixtures.search

        def search(query, section):
            data = original_search(query, section)
            if query == "alpha" and section == "class":
                extra = original_search("beta", section)
                hit = iri("c-beta")
                data["matches"].extend(extra["matches"])
                data["tree"]["nodes"][hit] = extra["tree"]["nodes"][hit]
                data["tree"]["nodes"][iri("c-root")]["children"].append(hit)
            return data

        self.fixtures.search = search
        await self.open()

        async def assert_hits(query, count, names):
            await self.settled()
            await expect(self.page.locator("#explore-search-input")).to_have_value(
                query
            )
            await expect(self.page.locator("#search-match-count")).to_have_text(count)
            await expect(self.page.locator(".tree-node-match")).to_have_count(
                len(names)
            )
            for name in names:
                await expect(self.node(name)).to_have_class(
                    re.compile("tree-node-match")
                )
                await expect(
                    self.node(name).locator(":scope > .node-content")
                ).to_have_css("color", "rgb(255, 255, 255)")

        field = self.page.locator("#explore-search-input")
        await field.fill("alpha")
        await field.press("Enter")
        await self.selected("c-alpha")
        await assert_hits(
            "alpha",
            "3 matches (2 classes, 1 property)",
            ["c-alpha", "c-beta", "p-alpha"],
        )
        await self.search("beta")
        await self.page.go_back()
        await assert_hits(
            "alpha",
            "3 matches (2 classes, 1 property)",
            ["c-alpha", "c-beta", "p-alpha"],
        )
        await self.page.go_forward()
        await assert_hits(
            "beta", "2 matches (1 class, 1 property)", ["c-beta", "p-beta"]
        )
