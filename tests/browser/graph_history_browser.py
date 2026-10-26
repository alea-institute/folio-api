"""Entity Graph follows real tree navigation and native history traversal."""

import re
from urllib.parse import unquote

from playwright.async_api import expect
from support import ExplorerBrowserCase, iri


class GraphHistoryBrowserTests(ExplorerBrowserCase):
    async def settled(self):
        await expect(self.page.locator("#explore-tree")).to_have_attribute(
            "aria-busy", "false"
        )

    async def graph_selected(self, name):
        await expect(self.page.locator(".graph-node-selected")).to_have_count(1)
        await expect(self.page.locator(".graph-node-selected")).to_have_attribute(
            "data-iri", iri(name)
        )
        await expect(self.page.locator("#graph-svg")).to_have_attribute(
            "aria-label",
            re.compile("Entity graph for " + self.fixtures.nodes[iri(name)]["label"]),
        )

    async def release_response(self, barrier):
        async with self.page.expect_response(
            lambda response: barrier.contains in unquote(response.url)
        ):
            barrier.release()
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )

    async def test_active_and_lazy_graph_follow_both_selection_types(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        await self.node("p-alpha").locator(":scope > .node-content").click()
        await self.graph_selected("p-alpha")
        await self.page.go_back()
        await self.settled()
        await self.graph_selected("c-alpha")
        await self.page.go_forward()
        await self.settled()
        await self.graph_selected("p-alpha")
        await self.page.locator("#tab-details").click()
        await self.page.go_back()
        await self.settled()
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")

    async def test_clear_and_initial_entry_clear_active_and_remembered_graph(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        await self.page.locator("#explore-search-clear").click()
        await self.settled()
        await expect(self.page.locator("#entity-graph-pane")).to_contain_text(
            "No entity selected"
        )
        await expect(self.page.locator(".graph-node")).to_have_count(0)
        await self.page.locator("#tab-details").click()
        await self.page.locator("#tab-graph").click()
        await expect(self.page.locator("#entity-graph-pane")).to_contain_text(
            "No entity selected"
        )
        await self.page.go_back()
        await self.settled()
        await self.graph_selected("c-alpha")
        await self.page.go_back()
        await self.settled()
        await expect(self.page.locator("#entity-graph-pane")).to_contain_text(
            "No entity selected"
        )
        await expect(self.page.locator(".graph-node")).to_have_count(0)

    async def test_late_graph_fetch_cannot_replace_current_or_empty_graph(self):
        await self.open()
        await self.search("alpha")
        barrier = self.fixtures.hold("/explore/api/entity-graph/" + iri("c-alpha"))
        await self.page.locator("#tab-graph").click()
        await barrier.wait()
        await self.search("beta")
        await self.graph_selected("c-beta")
        await self.release_response(barrier)
        await self.graph_selected("c-beta")
        barrier = self.fixtures.hold("/explore/api/entity-graph/" + iri("p-beta"))
        await self.node("p-beta").locator(":scope > .node-content").click()
        await barrier.wait()
        await self.page.locator("#explore-search-clear").click()
        await self.settled()
        await self.release_response(barrier)
        await expect(self.page.locator("#entity-graph-pane")).to_contain_text(
            "No entity selected"
        )
        await expect(self.page.locator(".graph-node")).to_have_count(0)

    async def test_late_children_response_cannot_change_current_graph(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        self.fixtures.nodes[iri("c-alpha")]["children"] = [iri("c-context")]
        barrier = self.fixtures.hold(
            "/explore/api/entity-graph/" + iri("c-alpha") + "?mode=children"
        )
        await self.page.locator(".graph-node-selected .graph-node-children-btn").click()
        await barrier.wait()
        await self.search("beta")
        await self.graph_selected("c-beta")
        await self.release_response(barrier)
        await self.graph_selected("c-beta")
        await expect(
            self.page.locator('.graph-node[data-iri="' + iri("c-context") + '"]')
        ).to_have_count(0)

    async def test_late_real_layout_cannot_paint_over_new_selection(self):
        await self.open()
        await self.page.evaluate("EntityGraph.loadELK()")
        await self.page.evaluate(
            """() => {
            const RealELK = window.ELK;
            let held = false;
            window.ELK = function(...args) {
                const elk = new RealELK(...args);
                const layout = elk.layout.bind(elk);
                elk.layout = spec => layout(spec).then(result => {
                    if (!held && spec.children.some(node => node.id.endsWith('/c-alpha'))) {
                        held = true;
                        document.documentElement.dataset.layoutStarted = 'true';
                        return new Promise(resolve => { window.releaseLayout = () => resolve(result); });
                    }
                    return result;
                });
                return elk;
            };
        }"""
        )
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await expect(self.page.locator("html")).to_have_attribute(
            "data-layout-started", "true"
        )
        await self.search("beta")
        await self.graph_selected("c-beta")
        await self.page.evaluate("window.releaseLayout()")
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        await self.graph_selected("c-beta")
        await expect(
            self.page.locator('.graph-node[data-iri="' + iri("c-alpha") + '"]')
        ).to_have_count(0)

    async def test_graph_click_selects_through_tree_with_one_history_entry(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        length = await self.page.evaluate("history.length")
        await self.page.locator(
            '.graph-node[data-iri="' + iri("c-root") + '"] .graph-node-label'
        ).click()
        await self.selected("c-root")
        await self.graph_selected("c-root")
        self.assertEqual(await self.page.evaluate("history.length"), length + 1)
        await self.page.go_back()
        await self.settled()
        await self.selected("c-alpha")
        await self.graph_selected("c-alpha")

    async def test_cleared_selection_is_not_revived_on_first_graph_activation(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#explore-search-clear").click()
        await self.settled()
        await self.page.locator("#tab-graph").click()
        await expect(self.page.locator("#entity-graph-pane")).to_contain_text(
            "No entity selected"
        )
        self.assertEqual(
            sum(
                count
                for key, count in self.fixtures.requests.items()
                if key.startswith("/explore/api/entity-graph/")
            ),
            0,
        )

    async def test_queued_render_cannot_mount_after_selection_changes(self):
        await self.open()
        await self.page.evaluate(
            """() => {
            const schedule = window.requestAnimationFrame;
            let held = false;
            window.requestAnimationFrame = callback => {
                const data = window.EntityGraph.state.graphData;
                if (!held && data?.selected?.iri.endsWith('/c-alpha') && data.layout) {
                    held = true;
                    document.documentElement.dataset.frameHeld = 'true';
                    window.releaseGraphFrame = () => callback(performance.now());
                    return 0;
                }
                return schedule(callback);
            };
        }"""
        )
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await expect(self.page.locator("html")).to_have_attribute(
            "data-frame-held", "true"
        )
        await self.search("beta")
        await self.graph_selected("c-beta")
        await self.page.evaluate("window.releaseGraphFrame()")
        await self.graph_selected("c-beta")
        await expect(
            self.page.locator('.graph-node[data-iri="' + iri("c-alpha") + '"]')
        ).to_have_count(0)

    async def test_late_child_layout_cannot_paint_over_new_selection(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        await self.page.evaluate(
            """() => {
            const RealELK = window.ELK;
            let held = false;
            window.ELK = function(...args) {
                const elk = new RealELK(...args);
                const layout = elk.layout.bind(elk);
                elk.layout = spec => layout(spec).then(result => {
                    if (!held && spec.children.some(node => node.id.endsWith('/c-context'))) {
                        held = true;
                        document.documentElement.dataset.childLayoutStarted = 'true';
                        return new Promise(resolve => { window.releaseChildLayout = () => resolve(result); });
                    }
                    return result;
                });
                return elk;
            };
        }"""
        )
        self.fixtures.nodes[iri("c-alpha")]["children"] = [iri("c-context")]
        await self.page.locator(".graph-node-selected .graph-node-children-btn").click()
        await expect(self.page.locator("html")).to_have_attribute(
            "data-child-layout-started", "true"
        )
        await self.search("beta")
        await self.graph_selected("c-beta")
        await self.page.evaluate("window.releaseChildLayout()")
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        await self.graph_selected("c-beta")
        await expect(
            self.page.locator('.graph-node[data-iri="' + iri("c-context") + '"]')
        ).to_have_count(0)

    async def test_failed_search_resumes_pending_graph_for_retained_selection(self):
        await self.open()
        await self.search("alpha")
        barrier = self.fixtures.hold("/explore/api/entity-graph/" + iri("c-alpha"))
        await self.page.locator("#tab-graph").click()
        await barrier.wait()
        self.fixtures.fail_next("/taxonomy/tree/search?query=beta")
        await self.page.locator("#explore-search-input").fill("beta")
        await self.page.locator("#explore-search-input").press("Enter")
        await expect(self.page.locator("#tree-history-notice")).to_contain_text(
            "Search could not be loaded"
        )
        await self.graph_selected("c-alpha")
        await self.release_response(barrier)
        await self.graph_selected("c-alpha")
