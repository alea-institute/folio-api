"""Recovery, retry, and cancellation through native browser history."""

import re
from urllib.parse import quote

from playwright.async_api import expect
from support import ExplorerBrowserCase, iri


class TreeHistoryRecoveryBrowserTests(ExplorerBrowserCase):
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

    async def test_new_search_failure_during_restore_retains_destination(self):
        await self.open()
        await self.search("alpha")
        saved = await self.page.evaluate("history.state")
        await self.search("beta")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=alpha")
        await self.page.go_back()
        await barrier.wait()
        self.fixtures.fail_next("/taxonomy/tree/search?query=shared")
        await self.page.locator("#explore-search-input").fill("shared")
        await self.page.locator("#explore-search-input").press("Enter")
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "Search could not be loaded"
        )
        await self.selected("c-alpha")
        await self.release_response(barrier)
        self.assertEqual(await self.page.evaluate("history.state"), saved)

    async def test_canceled_expansion_does_not_stick_or_save_loading_state(self):
        await self.open()
        await self.search("alpha")
        barrier = self.fixtures.hold(
            "/taxonomy/tree/data?node_id=" + quote(iri("c-alpha"), safe="")
        )
        await self.expand("c-alpha")
        await barrier.wait()
        await self.choose("p-alpha")
        saved = await self.page.evaluate("history.state")
        await self.release_response(barrier)
        self.assertEqual(await self.page.evaluate("history.state"), saved)
        await self.expand("c-alpha")
        await expect(self.node("c-alpha-child")).to_be_visible()
        await self.search("beta")
        await self.page.go_back()
        await self.settled()
        await self.selected("p-alpha")
        await expect(self.node("c-alpha-child")).to_be_visible()
        await expect(self.page.locator(".loading-indicator")).to_have_count(0)

    async def test_canceled_branch_controls_retry_before_old_response(self):
        for prefix, other, endpoint in (
            ("c", "p", "/taxonomy/tree/data"),
            ("p", "c", "/properties/tree/data"),
        ):
            for action in ("expand", "siblings"):
                with self.subTest(section=prefix, action=action):
                    await self.open()
                    await self.search("alpha")
                    await self.choose(prefix + "-alpha")
                    if action == "expand":
                        parent = prefix + "-alpha"
                        control = self.node(parent).locator(
                            ":scope > .node-content > .expand-icon"
                        )
                        child = prefix + "-alpha-child"
                    else:
                        parent = prefix + "-root"
                        control = self.node(parent).locator(
                            ":scope > .children-container > .siblings-row > button"
                        )
                        child = prefix + "-context"
                    key = endpoint + "?node_id=" + quote(iri(parent), safe="")
                    requests_before = self.fixtures.requests[key]
                    obsolete = self.fixtures.hold(key)
                    await control.click()
                    await obsolete.wait()
                    await self.choose(other + "-alpha")
                    await expect(self.page.locator(".loading-indicator")).to_have_count(
                        0
                    )
                    current = self.fixtures.hold(key)
                    await control.click()
                    await current.wait()
                    await self.release_response(obsolete)
                    if action == "expand":
                        await control.click()
                    else:
                        await expect(control).to_be_disabled()
                    await self.release_response(current)
                    await expect(self.node(child)).to_be_visible()
                    await self.selected(other + "-alpha")
                    await expect(self.page.locator(".loading-indicator")).to_have_count(
                        0
                    )
                    self.assertEqual(self.fixtures.requests[key], requests_before + 2)

    async def test_pending_search_blocks_old_view_gestures(self):
        await self.open()
        await self.search("alpha")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=beta")
        await self.page.locator("#explore-search-input").fill("beta")
        await self.page.locator("#explore-search-input").press("Enter")
        await barrier.wait()
        await expect(self.page.locator("#explore-tree")).to_have_attribute("inert", "")
        before = dict(self.fixtures.requests)
        await self.page.locator("#expand-all-tree").click()
        await self.page.locator(
            "#class-tree-root > .siblings-row > button"
        ).dispatch_event("click")
        await self.node("c-alpha").locator(
            ":scope > .node-content > .expand-icon"
        ).dispatch_event("click")
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        self.assertEqual(dict(self.fixtures.requests), before)
        barrier.release()
        await self.selected("c-beta")
        await self.settled()
        await expect(
            self.page.locator("#class-tree-root > .tree-node-context")
        ).to_have_count(0)
        await expect(self.page.locator("#explore-tree")).not_to_have_attribute(
            "inert", ""
        )

    async def test_branch_retry_still_works_after_selection_changes(self):
        await self.open()
        await self.search("alpha")
        self.fixtures.fail_next(
            "/taxonomy/tree/data?node_id=" + quote(iri("c-alpha"), safe="")
        )
        await self.expand("c-alpha")
        retry = self.node("c-alpha").locator(".tree-retry")
        await expect(retry).to_be_visible()
        await self.choose("p-alpha")
        length = await self.page.evaluate("history.length")
        await retry.click()
        await expect(self.node("c-alpha-child")).to_be_visible()
        await self.selected("p-alpha")
        self.assertEqual(await self.page.evaluate("history.length"), length)
        await expect(self.page.locator("#search-match-count")).to_have_text(
            "2 matches (1 class, 1 property)"
        )

    async def test_failed_clear_and_zero_results_preserve_committed_view(self):
        await self.open()
        for action in ("clear", "zero"):
            with self.subTest(action=action):
                await self.search("alpha")
                await self.selected("c-alpha")
                saved = await self.page.evaluate("history.state")
                self.fixtures.fail_next("/taxonomy/tree/data?node_id=%23")
                if action == "clear":
                    await self.page.locator("#explore-search-clear").click()
                    message = "The full tree could not be loaded"
                else:
                    await self.page.locator("#explore-search-input").fill("no matches")
                    await self.page.locator("#explore-search-input").press("Enter")
                    message = "Search could not be loaded"
                await expect(self.page.locator("#tree-history-notice")).to_contain_text(
                    message
                )
                await self.selected("c-alpha")
                await expect(self.node("c-alpha")).to_be_visible()
                self.assertEqual(await self.page.evaluate("history.state"), saved)
                await self.choose("p-alpha")
                await self.page.go_back()
                await self.settled()
                await self.selected("c-alpha")
                await expect(self.page.locator("#explore-search-input")).to_have_value(
                    "alpha"
                )
                self.assertEqual(await self.page.evaluate("history.state"), saved)

    async def test_legacy_details_failure_has_destination_retry(self):
        for legacy in (None, {"nodeId": iri("c-alpha"), "type": "class"}):
            with self.subTest(state=legacy):
                await self.open()
                await self.page.evaluate(
                    "state => { history.replaceState(state, '', '/explore/tree?node=c-alpha&type=class'); history.pushState({}, '', '/explore/tree?node=c-beta'); }",
                    legacy,
                )
                length = await self.page.evaluate("history.length")
                self.fixtures.fail_next("/taxonomy/class-details/c-alpha")
                self.fixtures.fail_next("/taxonomy/tree/node/c-alpha")
                await self.page.go_back()
                await expect(self.page.locator("#tree-history-notice")).to_contain_text(
                    "could not be restored"
                )
                self.assertEqual(await self.page.evaluate("history.state"), legacy)
                await self.page.get_by_role("button", name="Retry", exact=True).click()
                await self.settled()
                await self.selected("c-alpha")
                self.assertEqual(await self.page.evaluate("history.state"), legacy)
                self.assertEqual(await self.page.evaluate("history.length"), length)

    async def test_completed_gesture_survives_abandoned_branch_load(self):
        await self.open()
        await self.search("alpha")
        barrier = self.fixtures.hold(
            "/taxonomy/tree/data?node_id=" + quote(iri("c-alpha"), safe="")
        )
        await self.expand("c-alpha")
        await barrier.wait()
        await self.page.locator('.section-header[data-section="property"]').click()
        await self.choose("c-root")
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")
        await expect(self.page.locator("#property-tree-root")).to_be_hidden()
        await self.release_response(barrier)
        await expect(self.node("c-alpha")).to_have_class(re.compile("collapsed"))
        await expect(self.page.locator(".loading-indicator")).to_have_count(0)

    async def test_completed_gesture_is_saved_before_native_traversal_during_load(self):
        await self.open()
        await self.search("alpha")
        barrier = self.fixtures.hold(
            "/taxonomy/tree/data?node_id=" + quote(iri("c-alpha"), safe="")
        )
        await self.expand("c-alpha")
        await barrier.wait()
        await self.page.locator('.section-header[data-section="property"]').click()
        await self.page.go_back()
        await self.settled()
        await self.page.go_forward()
        await self.settled()
        await self.selected("c-alpha")
        await expect(self.page.locator("#property-tree-root")).to_be_hidden()
        await self.release_response(barrier)
        await expect(self.node("c-alpha")).to_have_class(re.compile("collapsed"))

    async def test_pending_clear_retains_both_sections_until_roots_settle(self):
        await self.open()
        await self.search("alpha")
        barrier = self.fixtures.hold("/properties/tree/data?node_id=%23")
        length = await self.page.evaluate("history.length")
        await self.page.locator("#explore-search-clear").click()
        await barrier.wait()
        await expect(self.page.locator("#explore-tree")).to_have_attribute("inert", "")
        await self.node("c-root").locator(":scope > .node-content").dispatch_event(
            "click"
        )
        barrier.release()
        await self.settled()
        for prefix in ("c", "p"):
            await expect(self.node(prefix + "-root")).to_be_visible()
            await expect(self.node(prefix + "-other")).to_be_visible()
        await expect(self.page.locator(".tree-node.selected")).to_have_count(0)
        self.assertEqual(await self.page.evaluate("history.length"), length + 1)
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")

    async def test_failed_clear_during_restore_retains_destination(self):
        await self.open()
        await self.search("alpha")
        saved = await self.page.evaluate("history.state")
        await self.search("beta")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=alpha")
        await self.page.go_back()
        await barrier.wait()
        self.fixtures.fail_next("/taxonomy/tree/data?node_id=%23")
        await self.page.locator("#explore-search-clear").click()
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "The full tree could not be loaded"
        )
        await self.selected("c-alpha")
        await self.settled()
        await self.release_response(barrier)
        self.assertEqual(await self.page.evaluate("history.state"), saved)
        await expect(self.page.locator("#explore-search-input")).to_have_value("alpha")
        await self.page.locator('.section-header[data-section="property"]').click()
        await self.search("beta")
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")
        await expect(self.page.locator("#property-tree-root")).to_be_hidden()

    async def test_failed_clear_recovery_keeps_restoration_retry(self):
        await self.open()
        await self.search("alpha")
        saved = await self.page.evaluate("history.state")
        await self.search("beta")
        length = await self.page.evaluate("history.length")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=alpha")
        await self.page.go_back()
        await barrier.wait()
        self.fixtures.fail_next("/taxonomy/tree/data?node_id=%23")
        self.fixtures.fail_next("/taxonomy/tree/search?query=alpha")
        await self.page.locator("#explore-search-clear").click()
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "could not be restored"
        )
        await expect(self.page.locator("#explore-tree")).to_have_attribute("inert", "")
        self.assertEqual(await self.page.evaluate("history.state"), saved)
        await self.release_response(barrier)
        await self.page.get_by_role("button", name="Retry", exact=True).click()
        await self.settled()
        await self.selected("c-alpha")
        self.assertEqual(await self.page.evaluate("history.state"), saved)
        self.assertEqual(await self.page.evaluate("history.length"), length)

    async def test_completed_gesture_is_saved_before_next_browser_task(self):
        await self.open()
        await self.search("alpha")
        opened = await self.page.evaluate(
            """async () => {
            document.querySelector('.section-header[data-section="property"]').click();
            await Promise.resolve();
            return history.state.folioExplorer.sections.property.open;
        }"""
        )
        self.assertFalse(opened)
        await self.page.go_back()
        await self.settled()
        await self.page.go_forward()
        await self.settled()
        await self.selected("c-alpha")
        await expect(self.page.locator("#property-tree-root")).to_be_hidden()
