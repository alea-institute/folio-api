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
        await expect(self.page.locator("#graph-controls")).to_have_count(1)
        await expect(self.page.locator("#graph-minimap")).to_have_count(1)
        await self.page.evaluate(
            "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
        )

    async def camera_and_overview(self):
        return await self.page.evaluate(
            """() => ({
                camera: {...EntityGraph.state.transform},
                pixels: document.querySelector('#graph-minimap').toDataURL(),
                summary: document.querySelector('#graph-view-summary').textContent,
                positions: structuredClone(EntityGraph.state.nodePositions)
            })"""
        )

    async def test_pending_navigation_suspends_controls_and_resumes_cached_mount(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        zoom = self.page.get_by_role("button", name="Zoom in", exact=True)
        await zoom.press("Enter")
        await self.page.evaluate(
            "window.retainedViewport = document.querySelector('#graph-viewport')"
        )
        before = await self.camera_and_overview()
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=beta")
        self.fixtures.fail_next("/taxonomy/tree/search?query=beta")
        await self.page.locator("#explore-search-input").fill("beta")
        await self.page.locator("#explore-search-input").press("Enter")
        await barrier.wait()
        try:
            for button in await self.page.locator("#graph-controls button").all():
                await expect(button).to_have_attribute("aria-disabled", "true")
                await button.focus()
                await self.page.keyboard.press("Enter")
                await self.page.keyboard.press("Space")
            await self.page.locator("#graph-viewport").hover()
            await self.page.mouse.wheel(0, -120)
            await self.page.evaluate("EntityGraph.fitGraph()")
            await self.page.set_viewport_size({"width": 1200, "height": 900})
            await self.page.evaluate(
                "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
            )
            self.assertEqual(await self.camera_and_overview(), before)
            await self.page.locator("#explore-search-input").focus()
            await self.release_response(barrier)
            await expect(self.page.locator("#tree-history-notice")).to_contain_text(
                "Search could not be loaded"
            )
            await self.graph_selected("c-alpha")
            self.assertTrue(
                await self.page.evaluate(
                    "retainedViewport === document.querySelector('#graph-viewport')"
                )
            )
            self.assertEqual(
                (await self.camera_and_overview())["camera"], before["camera"]
            )
            await expect(self.page.locator("#explore-search-input")).to_be_focused()
            await expect(zoom).to_have_attribute("aria-disabled", "false")
            await zoom.press("Space")
            self.assertGreater(
                (await self.camera_and_overview())["camera"]["scale"],
                before["camera"]["scale"],
            )
            self.assertNotEqual(
                (await self.camera_and_overview())["pixels"], before["pixels"]
            )
        finally:
            barrier.release()

    async def test_queued_observer_cannot_mutate_pending_or_reaccepted_mount(self):
        await self.open()
        await self.page.evaluate(
            """() => {
                window.graphObservers = [];
                const RealObserver = window.ResizeObserver;
                window.ResizeObserver = class extends RealObserver {
                    constructor(callback) {
                        super(callback);
                        window.graphObservers.push(callback);
                    }
                };
            }"""
        )
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        await self.page.get_by_role("button", name="Zoom in", exact=True).press("Enter")
        await self.page.evaluate(
            "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
        )
        await self.page.evaluate(
            """() => {
                const schedule = window.requestAnimationFrame;
                window.requestAnimationFrame = callback => {
                    window.releaseObserverFrame = () => callback(performance.now());
                    return 0;
                };
                window.graphObservers.at(-1)();
                window.requestAnimationFrame = schedule;
                if (!window.releaseObserverFrame) throw new Error('Observer frame was not captured');
            }"""
        )
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=beta")
        self.fixtures.fail_next("/taxonomy/tree/search?query=beta")
        await self.page.locator("#explore-search-input").fill("beta")
        await self.page.locator("#explore-search-input").press("Enter")
        await barrier.wait()
        try:
            before = await self.camera_and_overview()
            await self.page.set_viewport_size({"width": 1100, "height": 850})
            await self.page.evaluate("window.releaseObserverFrame()")
            self.assertEqual(await self.camera_and_overview(), before)
            await self.release_response(barrier)
            await self.graph_selected("c-alpha")
            resumed = await self.camera_and_overview()
            await self.page.evaluate("window.releaseObserverFrame()")
            self.assertEqual(await self.camera_and_overview(), resumed)
            self.assertEqual(resumed["camera"], before["camera"])
            self.assertNotEqual(resumed["pixels"], before["pixels"])
        finally:
            barrier.release()

    async def test_queued_expansion_cannot_restore_focus_after_navigation(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        await self.page.evaluate(
            """() => {
                const schedule = window.requestAnimationFrame;
                window.requestAnimationFrame = callback => {
                    if (!document.querySelector('#graph-controls')) {
                        window.requestAnimationFrame = schedule;
                        window.releaseExpansionFrame = () => callback(performance.now());
                        document.documentElement.dataset.expansionFrameHeld = 'true';
                        return 0;
                    }
                    return schedule(callback);
                };
            }"""
        )
        await self.page.locator(".graph-node-selected .graph-node-children-btn").press(
            "Enter"
        )
        await expect(self.page.locator("html")).to_have_attribute(
            "data-expansion-frame-held", "true"
        )
        await self.search("beta")
        await self.graph_selected("c-beta")
        await self.page.locator("#explore-search-input").focus()
        before = await self.camera_and_overview()
        await self.page.evaluate("window.releaseExpansionFrame()")
        await self.graph_selected("c-beta")
        self.assertEqual(await self.camera_and_overview(), before)
        await expect(self.page.locator("#explore-search-input")).to_be_focused()

    async def test_back_forward_replaces_suspended_controls_and_overview(self):
        await self.open()
        await self.search("alpha")
        await self.page.locator("#tab-graph").click()
        await self.graph_selected("c-alpha")
        await self.search("beta")
        await self.graph_selected("c-beta")
        await self.page.evaluate(
            """() => {
                window.oldGraphButton = document.querySelector('[data-graph-action=right]');
                window.oldGraphCanvas = document.querySelector('#graph-minimap');
            }"""
        )
        length = await self.page.evaluate("history.length")
        barrier = self.fixtures.hold("/taxonomy/tree/search?query=alpha")
        await self.page.go_back()
        await barrier.wait()
        try:
            before = await self.camera_and_overview()
            await self.page.get_by_role("button", name="Pan right", exact=True).focus()
            await self.page.keyboard.press("Enter")
            self.assertEqual(await self.camera_and_overview(), before)
            await self.release_response(barrier)
            await self.selected("c-alpha")
            await self.graph_selected("c-alpha")
            await expect(
                self.page.get_by_role("button", name="Pan right", exact=True)
            ).to_have_attribute("aria-disabled", "false")
            current = await self.camera_and_overview()
            await self.page.evaluate("window.oldGraphButton.click()")
            self.assertEqual(await self.camera_and_overview(), current)
            self.assertEqual(
                await self.page.evaluate("oldGraphCanvas.toDataURL()"), before["pixels"]
            )
            for name, navigate in (
                ("c-beta", self.page.go_forward),
                ("c-alpha", self.page.go_back),
            ):
                await navigate()
                await self.selected(name)
                await self.graph_selected(name)
                right = self.page.get_by_role("button", name="Pan right", exact=True)
                await expect(right).to_have_attribute("aria-disabled", "false")
                current = await self.camera_and_overview()
                await right.press("Space")
                moved = await self.camera_and_overview()
                self.assertEqual(moved["camera"]["x"], current["camera"]["x"] - 80)
                self.assertNotEqual(moved["pixels"], current["pixels"])
                self.assertEqual(await self.page.evaluate("history.length"), length)
        finally:
            barrier.release()

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

    async def test_hidden_graph_reselection_finishes_fit_and_preserves_user_zoom(self):
        await self.open()
        await self.search("alpha")
        for index in range(11):
            parent = iri(f"c-wide-parent-{index}")
            self.fixtures.nodes[parent] = {
                "id": parent,
                "label": f"Wide parent {index}",
                "type": "class",
                "parents": [],
                "children": [iri("c-alpha")],
            }
            self.fixtures.nodes[iri("c-alpha")]["parents"].append(parent)
        barrier = self.fixtures.hold("/explore/api/entity-graph/" + iri("c-alpha"))
        await self.page.locator("#tab-graph").click()
        await barrier.wait()
        await self.page.locator("#tab-details").click()
        await self.release_response(barrier)
        await self.graph_selected("c-alpha")
        await self.node("c-alpha").locator(":scope > .node-content").click()
        await self.selected("c-alpha")
        await self.page.locator("#tab-graph").click()
        selected = self.page.locator(".graph-node-selected")
        await expect(selected).to_be_in_viewport(ratio=1)
        await self.screenshot("fa-5-graph-history-refit.png")

        transform = self.page.locator("#graph-transform")
        fitted = await transform.get_attribute("style")
        viewport = self.page.locator("#graph-viewport")
        await viewport.hover()
        await self.page.mouse.wheel(0, -120)
        await expect(transform).not_to_have_attribute("style", fitted)
        zoomed = await transform.get_attribute("style")
        await self.page.locator("#tab-details").click()
        await self.node("c-alpha").locator(":scope > .node-content").click()
        await self.selected("c-alpha")
        await self.page.locator("#tab-graph").click()
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        await expect(transform).to_have_attribute("style", zoomed)

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
        await expect(
            self.page.locator("#graph-controls, #graph-minimap")
        ).to_have_count(0)
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
        await expect(
            self.page.locator("#graph-controls, #graph-minimap")
        ).to_have_count(0)

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
        await expect(
            self.page.locator("#graph-controls, #graph-minimap")
        ).to_have_count(0)

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

    async def test_pending_navigation_cannot_start_graph_drags(self):
        for gesture in ("pan", "node"):
            with self.subTest(gesture=gesture):
                await self.open()
                await self.search("alpha")
                await self.page.locator("#tab-graph").click()
                await self.graph_selected("c-alpha")
                viewport = self.page.locator("#graph-viewport")
                target = (
                    viewport
                    if gesture == "pan"
                    else self.page.locator(".graph-node-selected")
                )
                box = await target.bounding_box()
                x = box["x"] + (box["width"] - 5 if gesture == "pan" else 10)
                y = box["y"] + (box["height"] - 5 if gesture == "pan" else 10)
                barrier = self.fixtures.hold("/taxonomy/tree/search?query=beta")
                await self.page.locator("#explore-search-input").fill("beta")
                await self.page.locator("#explore-search-input").press("Enter")
                await barrier.wait()
                try:
                    await self.page.mouse.move(x, y)
                    await self.page.mouse.down()
                    await expect(viewport).not_to_have_class(
                        re.compile("graph-grabbing")
                    )
                    await expect(self.page.locator("body")).not_to_have_css(
                        "cursor", "grabbing"
                    )
                    await self.release_response(barrier)
                    await self.graph_selected("c-beta")
                    transform = self.page.locator("#graph-transform")
                    await expect(transform).to_have_attribute(
                        "style", re.compile("transform: translate")
                    )
                    before = await transform.get_attribute("style")
                    await self.page.mouse.move(x - 40, y - 40)
                    await expect(transform).to_have_attribute("style", before)
                    await self.graph_selected("c-beta")
                finally:
                    barrier.release()
                    await self.page.mouse.up()

                target = (
                    viewport
                    if gesture == "pan"
                    else self.page.locator(".graph-node-selected")
                )
                box = await target.bounding_box()
                x = box["x"] + (box["width"] - 5 if gesture == "pan" else 10)
                y = box["y"] + (box["height"] - 5 if gesture == "pan" else 10)
                await self.page.mouse.move(x, y)
                await self.page.mouse.down()
                try:
                    if gesture == "pan":
                        await expect(viewport).to_have_class(
                            re.compile("graph-grabbing")
                        )
                    else:
                        await expect(self.page.locator("body")).to_have_css(
                            "cursor", "grabbing"
                        )
                finally:
                    await self.page.mouse.up()
