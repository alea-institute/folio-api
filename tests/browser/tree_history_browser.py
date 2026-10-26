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
        await self.open()
        await self.search("alpha")
        button = self.node("c-root").locator(
            ":scope > .children-container > .siblings-row > button"
        )
        await button.click()
        await self.node("c-context").locator(
            ":scope > .node-content > .expand-icon"
        ).click()
        await self.node("c-context-child").locator(":scope > .node-content").click()
        await self.selected("c-context-child")
        await self.search("beta")
        await self.selected("c-beta")
        await self.page.go_back()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await self.selected("c-context-child")
        await expect(self.node("c-context-child")).to_be_visible()
        await self.screenshot("fa-1-tree-history-back.png")
        await self.page.go_forward()
        await expect(self.page.locator("#explore-search-input")).to_have_value("beta")
        await self.selected("c-beta")
        await self.screenshot("fa-1-tree-history-forward.png")

    async def test_details_link_reveals_property_in_filtered_tree(self):
        await self.open()
        await self.search("alpha")
        await self.selected("c-alpha")
        await self.page.get_by_role("link", name="Related Beta Relation").click()
        await self.selected("p-beta")
        await expect(self.node("p-beta")).to_be_visible()
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")

    async def settled(self):
        await expect(self.page.locator("#explore-tree")).to_have_attribute(
            "aria-busy", "false"
        )

    async def choose(self, name, within=None):
        await self.node(name, within).locator(":scope > .node-content").click()
        await self.selected(name)

    async def expand(self, name, within=None):
        await self.node(name, within).locator(
            ":scope > .node-content > .expand-icon"
        ).click()

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

    async def test_restore_retry_preserves_snapshot_and_history(self):
        await self.open()
        await self.search("alpha")
        snapshot = await self.page.evaluate("history.state")
        await self.search("beta")
        length = await self.page.evaluate("history.length")
        self.fixtures.fail_next("/taxonomy/tree/search?query=alpha")
        await self.page.go_back()
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "could not be restored"
        )
        self.assertEqual(await self.page.evaluate("history.state"), snapshot)
        await self.page.get_by_role("button", name="Retry", exact=True).click()
        await self.selected("c-alpha")
        await self.settled()
        self.assertEqual(await self.page.evaluate("history.state"), snapshot)
        self.assertEqual(await self.page.evaluate("history.length"), length)

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

    async def test_failed_search_and_invalid_input_keep_committed_view(self):
        await self.open()
        await self.search("alpha")
        saved = await self.page.evaluate("history.state")
        length = await self.page.evaluate("history.length")
        self.page.once("dialog", lambda dialog: dialog.accept())
        await self.page.locator("#explore-search-input").fill("a")
        await self.page.locator("#explore-search-input").press("Enter")
        self.fixtures.fail_next("/taxonomy/tree/search?query=beta")
        await self.page.locator("#explore-search-input").fill("beta")
        await self.page.locator("#explore-search-input").press("Enter")
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "Search could not be loaded"
        )
        await self.selected("c-alpha")
        self.assertEqual(await self.page.evaluate("history.state"), saved)
        self.assertEqual(await self.page.evaluate("history.length"), length)

    async def test_history_write_failure_keeps_browsing_usable(self):
        await self.open()
        await self.page.evaluate(
            "() => { history.pushState = () => { throw new DOMException('fixture quota', 'QuotaExceededError'); }; }"
        )
        await self.search("alpha")
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "could not be saved"
        )
        await self.choose("p-alpha")
        await self.expand("p-alpha")
        await expect(self.node("p-alpha-child")).to_be_visible()

    async def release_response(self, barrier):
        async with self.page.expect_response(
            lambda response: barrier.contains in response.url
        ):
            barrier.release()
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )

    async def test_late_search_and_reveal_cannot_replace_history_destination(self):
        await self.open()
        await self.search("alpha")
        await self.search("beta")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=shared")
        await self.page.locator("#explore-search-input").fill("shared")
        await self.page.locator("#explore-search-input").press("Enter")
        await barrier.wait()
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")
        saved = await self.page.evaluate("history.state")
        await self.release_response(barrier)
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        self.assertEqual(await self.page.evaluate("history.state"), saved)
        barrier = self.fixtures.hold(
            "/taxonomy/tree/data?node_id=" + quote(iri("c-root"), safe="")
        )
        await self.node("c-root").locator(
            ":scope > .children-container > .siblings-row > button"
        ).click()
        await barrier.wait()
        await self.page.go_forward()
        await self.settled()
        await self.selected("c-beta")
        await self.release_response(barrier)
        await expect(self.node("c-context")).to_have_count(0)
        await self.selected("c-beta")

    async def test_late_details_and_json_fallback_cannot_overwrite_selection(self):
        await self.open()
        await self.search("alpha")
        for fallback in (False, True):
            if fallback:
                self.fixtures.fail_next("/properties/property-details/p-alpha")
            barrier = self.fixtures.hold(
                "/properties/tree/node/p-alpha"
                if fallback
                else "/properties/property-details/p-alpha"
            )
            await self.node("p-alpha").locator(":scope > .node-content").click()
            await barrier.wait()
            await self.choose("c-alpha")
            await self.release_response(barrier)
            await self.selected("c-alpha")

    async def test_rapid_back_forward_and_new_search_supersede_restore(self):
        await self.open()
        await self.search("alpha")
        await self.search("beta")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=alpha")
        await self.page.go_back()
        await barrier.wait()
        await self.page.go_forward()
        await self.settled()
        await self.selected("c-beta")
        await self.release_response(barrier)
        await self.selected("c-beta")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=alpha")
        await self.page.go_back()
        await barrier.wait()
        await self.search("shared")
        await self.settled()
        await self.release_response(barrier)
        await expect(self.page.locator("#explore-search-input")).to_have_value("shared")
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")

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

    async def test_restore_branch_and_details_failure_retry(self):
        await self.open()
        await self.search("alpha")
        await self.expand("c-alpha")
        await self.choose("c-alpha-child")
        saved = await self.page.evaluate("history.state")
        for kind in ("branch", "details"):
            await self.search("beta")
            if kind == "branch":
                self.fixtures.fail_next(
                    "/taxonomy/tree/data?node_id=" + quote(iri("c-alpha"), safe="")
                )
            else:
                self.fixtures.fail_next("/taxonomy/class-details/c-alpha-child")
                self.fixtures.fail_next("/taxonomy/tree/node/c-alpha-child")
            await self.page.go_back()
            await expect(self.page.locator("#tree-history-notice")).to_contain_text(
                "could not be restored"
            )
            self.assertEqual(await self.page.evaluate("history.state"), saved)
            await self.page.get_by_role("button", name="Retry", exact=True).click()
            await self.settled()
            await self.selected("c-alpha-child")
            self.assertEqual(await self.page.evaluate("history.state"), saved)

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

    async def test_delayed_restore_details_cannot_overwrite_forward_selection(self):
        await self.open()
        await self.search("alpha")
        await self.search("beta")
        barrier = self.fixtures.hold("/taxonomy/class-details/c-alpha")
        await self.page.go_back()
        await barrier.wait()
        await self.page.go_forward()
        await self.settled()
        await self.selected("c-beta")
        saved = await self.page.evaluate("history.state")
        await self.release_response(barrier)
        await self.selected("c-beta")
        self.assertEqual(await self.page.evaluate("history.state"), saved)
