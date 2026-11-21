"""Invoke explicitly: pytest -o addopts='' browser_tests/entity_graph_controls.py."""

from urllib.parse import urlencode

import pytest
from playwright.sync_api import expect


def camera(page):
    return page.evaluate("({...EntityGraph.state.transform})")


def settled(page):
    page.evaluate(
        "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
    )


def test_existing_wheel_pan_expansion_and_fullscreen(graph_page):
    page, requests = graph_page
    vp = page.locator("#graph-viewport").bounding_box()
    x, y = vp["x"] + 12, vp["y"] + 12
    before = camera(page)
    point = ((12 - before["x"]) / before["scale"], (12 - before["y"]) / before["scale"])
    page.mouse.move(x, y)
    page.mouse.wheel(0, -80)
    page.wait_for_function(
        "s => EntityGraph.state.transform.scale !== s", arg=before["scale"]
    )
    after = camera(page)
    assert (12 - after["x"]) / after["scale"] == pytest.approx(point[0], abs=1)
    assert (12 - after["y"]) / after["scale"] == pytest.approx(point[1], abs=1)
    page.mouse.down()
    page.mouse.move(x + 30, y + 20)
    page.mouse.up()
    assert camera(page)["x"] == pytest.approx(after["x"] + 30)
    assert camera(page)["y"] == pytest.approx(after["y"] + 20)
    before = camera(page)
    page.get_by_role("button", name="Show 3 children").click()
    expect(page.locator(".graph-node")).to_have_count(6)
    assert camera(page) == before
    assert len(requests) == 2
    page.evaluate("window.originalPane = document.querySelector('#entity-graph-pane')")
    page.get_by_role("button", name="Open graph in full screen").click()
    expect(page.get_by_role("dialog")).to_be_visible()
    assert camera(page) == before
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    expect(page.locator("#tab-fullscreen")).to_be_focused()
    assert camera(page) == before
    assert page.evaluate(
        "window.originalPane === document.querySelector('#entity-graph-pane')"
    )


@pytest.mark.parametrize(
    "kind,endpoint", [("class", "taxonomy"), ("property", "properties")]
)
def test_live_deep_link_and_node_selection(page, kind, endpoint):
    # No interception: real ontology, graph response, tree selection and layout.
    roots = page.request.get(f"/{endpoint}/tree/data?node_id=%23").json()
    assert roots
    iri = next(root["id"] for root in roots if root["children"])
    page.goto("/explore/tree?" + urlencode({"node": iri, "type": kind}))
    page.locator("#tab-graph").click()
    expect(page.locator(".graph-node-selected")).to_have_attribute("data-iri", iri)
    page.wait_for_function("() => EntityGraph.state.transform.scale > 0")
    child_button = page.locator(".graph-node-children-btn")
    expect(child_button).to_be_visible()
    child_button.click()
    page.wait_for_function("() => document.querySelectorAll('.graph-node').length > 1")
    other = page.locator(".graph-node:not(.graph-node-selected)").first
    target = other.get_attribute("data-iri")
    page.get_by_role("button", name="Open graph in full screen").click()
    other.locator(".graph-node-label").click()
    expect(page.locator(".graph-node-selected")).to_have_attribute("data-iri", target)
    assert page.evaluate("EntityGraph.state.currentType") == kind


def test_empty_and_http_error(page):
    page.goto("/explore/tree")
    page.locator("#tab-graph").click()
    expect(page.get_by_text("No entity selected", exact=True)).to_be_visible()
    expect(page.locator("#graph-controls")).to_have_count(0)
    page.route(
        "**/explore/api/entity-graph/**", lambda r: r.fulfill(status=503, json={})
    )
    page.locator("#class-tree-root .node-label").first.click()
    expect(page.get_by_role("alert")).to_contain_text("Couldn’t load graph")
    expect(page.locator("#graph-controls")).to_have_count(0)
    expect(page.get_by_role("button", name="Retry")).to_be_visible()


def test_native_controls_pan_zoom_and_fit(graph_page):
    page, requests = graph_page
    before = camera(page)
    page.get_by_role("button", name="Pan right", exact=True).focus()
    page.keyboard.press("Enter")
    assert camera(page)["x"] == pytest.approx(before["x"] - 80)
    page.keyboard.press("Space")
    assert camera(page)["x"] == pytest.approx(before["x"] - 160)
    expect(page.get_by_role("button", name="Pan right", exact=True)).to_be_focused()
    for name, axis, delta in [
        ("Pan left", "x", 80),
        ("Pan up", "y", 80),
        ("Pan down", "y", -80),
    ]:
        before = camera(page)
        page.get_by_role("button", name=name, exact=True).click()
        assert camera(page)[axis] == pytest.approx(before[axis] + delta)
    before = camera(page)
    vp = page.locator("#graph-viewport").bounding_box()
    center = (vp["width"] / 2, vp["height"] / 2)
    page.get_by_role("button", name="Zoom in", exact=True).click()
    after = camera(page)
    assert after["scale"] == pytest.approx(before["scale"] * 1.12)
    for axis, c in zip(("x", "y"), center):
        assert (c - after[axis]) / after["scale"] == pytest.approx(
            (c - before[axis]) / before["scale"]
        )
    page.get_by_role("button", name="Fit graph", exact=True).click()
    assert camera(page)["scale"] <= 1
    assert len(requests) == 1
    expect(page.locator(".graph-node")).to_have_count(3)


def minimap_geometry(page):
    """Read rendered pixels and DOM bounds, independently of the projection code."""
    return page.evaluate(
        """() => {
        const canvas = document.querySelector('#graph-minimap');
        const ctx = canvas.getContext('2d');
        const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const box = color => {
            let xs = [], ys = [];
            for (let y = 0; y < canvas.height; y++) for (let x = 0; x < canvas.width; x++) {
                const i = (y * canvas.width + x) * 4;
                if (data[i] === color[0] && data[i+1] === color[1] && data[i+2] === color[2] && data[i+3] > 200) {
                    xs.push(x); ys.push(y);
                }
            }
            return xs.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : null;
        };
        return { blue: box([37,99,235]), view: box([17,24,39]),
            width: canvas.width, height: canvas.height, cw: canvas.clientWidth, ch: canvas.clientHeight,
            ratio: devicePixelRatio, pixels: canvas.toDataURL(), matrix: [...['a','b','c','d','e','f'].map(k => ctx.getTransform()[k])] };
    }"""
    )


def assert_map_contains_graph_and_view(page):
    drawing = minimap_geometry(page)
    assert drawing["blue"] is not None
    assert drawing["view"] is not None
    for box in (drawing["blue"], drawing["view"]):
        assert 0 < box[0] <= box[2] < drawing["width"] - 1
        assert 0 < box[1] <= box[3] < drawing["height"] - 1
    # Pixel outline matches a projection derived independently from DOM geometry.
    geometry = page.evaluate(
        """() => {
        const v = document.querySelector('#graph-viewport').getBoundingClientRect();
        return { viewport: {x: v.x, y: v.y, w: v.width, h: v.height},
            nodes: [...document.querySelectorAll('.graph-node')].map(n => {
                const r = n.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height};
            }) };
    }"""
    )
    v = geometry["viewport"]
    nodes = geometry["nodes"]
    left = min(v["x"], *(n["x"] for n in nodes))
    top = min(v["y"], *(n["y"] for n in nodes))
    right = max(v["x"] + v["w"], *(n["x"] + n["w"] for n in nodes))
    bottom = max(v["y"] + v["h"], *(n["y"] + n["h"] for n in nodes))
    scale = min(
        (drawing["cw"] - 12) / (right - left), (drawing["ch"] - 12) / (bottom - top)
    )
    ox, oy = (
        (drawing["cw"] - (right - left) * scale) / 2,
        (drawing["ch"] - (bottom - top) * scale) / 2,
    )
    expected = [
        ox + (v["x"] - left) * scale,
        oy + (v["y"] - top) * scale,
        ox + (v["x"] + v["w"] - left) * scale,
        oy + (v["y"] + v["h"] - top) * scale,
    ]
    assert [p / drawing["ratio"] for p in drawing["view"]] == pytest.approx(
        expected, abs=2
    )
    return drawing


def test_zoom_limits_native_tab_order_and_input_isolation(graph_page):
    page, requests = graph_page
    names = [
        "Pan left",
        "Pan up",
        "Pan down",
        "Pan right",
        "Zoom out",
        "Zoom in",
        "Fit graph",
    ]
    page.locator("#tab-fullscreen").focus()
    for name in names:
        page.keyboard.press("Tab")
        expect(page.get_by_role("button", name=name, exact=True)).to_be_focused()
    for name, limit in [("Zoom out", 0.2), ("Zoom in", 4)]:
        button = page.get_by_role("button", name=name, exact=True)
        button.focus()
        for _ in range(32):
            page.keyboard.press("Enter")
        assert camera(page)["scale"] == limit
        expect(button).to_have_attribute("aria-disabled", "true")
        before = camera(page)
        page.keyboard.press("Space")
        button.dispatch_event("click")  # Pointer activation is guarded too.
        assert camera(page) == before
        expect(button).to_be_focused()
    button = page.get_by_role("button", name="Pan left", exact=True)
    box = button.bounding_box()
    before = camera(page)
    page.mouse.move(box["x"] + 10, box["y"] + 10)
    page.mouse.wheel(0, 100)
    settled(page)
    assert camera(page) == before
    page.mouse.down()
    page.mouse.move(box["x"] + 120, box["y"] + 10)
    page.mouse.up()
    assert camera(page) == before
    assert len(requests) == 1
    page.locator("#tab-graph").focus()
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#tab-details")).to_be_focused()
    expect(page.locator("#tab-panel-graph")).to_be_hidden()
    search = page.get_by_role("searchbox")
    search.fill("law")
    expect(search).to_have_value("law")


def test_offscreen_overview_and_discrete_announcements(graph_page):
    page, _ = graph_page
    initial = assert_map_contains_graph_and_view(page)
    page.get_by_role("button", name="Pan right", exact=True).focus()
    for _ in range(20):
        page.keyboard.press("Enter")
    expect(page.locator("#graph-view-summary")).to_contain_text("0 of 3 nodes visible")
    expect(page.locator("#graph-view-summary")).to_contain_text("Use Fit graph")
    offscreen = assert_map_contains_graph_and_view(page)
    assert offscreen["pixels"] != initial["pixels"]
    live = page.locator("#graph-view-announcement")
    expect(live).to_have_attribute("role", "status")
    expect(live).to_have_attribute("aria-live", "polite")
    expect(live).to_contain_text("Pan right. 0 of 3 nodes visible")
    announcement = live.inner_text()
    v = page.locator("#graph-viewport").bounding_box()
    page.mouse.move(v["x"] + 10, v["y"] + 10)
    page.mouse.wheel(0, -90)
    settled(page)
    assert page.locator("#graph-view-announcement").inner_text() == announcement
    page.get_by_role("button", name="Fit graph", exact=True).click()
    expect(page.locator("#graph-view-summary")).to_contain_text("3 of 3 nodes visible")
    expect(live).to_contain_text("Fit graph. 3 of 3 nodes visible")
    assert_map_contains_graph_and_view(page)


def drag_node(page, node, dx, dy):
    box = node.locator(".graph-node-label").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(
        box["x"] + box["width"] / 2 + dx, box["y"] + box["height"] / 2 + dy, steps=8
    )
    page.mouse.up()
    settled(page)


def test_fit_and_overview_use_dragged_nodes_and_full_selected_height(graph_page):
    page, _ = graph_page
    page.get_by_role("button", name="Open graph in full screen").click()
    page.get_by_role("button", name="Fit graph", exact=True).click()
    selected = page.locator(".graph-node-selected")
    assert selected.evaluate("n => n.offsetHeight") > 36
    drag_node(page, page.locator(".graph-node").first, -450, -220)
    assert (
        min(
            page.evaluate(
                "Object.values(EntityGraph.state.nodePositions).map(n => n.x)"
            )
        )
        < 0
    )
    drag_node(page, selected, 250, 150)
    page.get_by_role("button", name="Fit graph", exact=True).click()
    v = page.locator("#graph-viewport").bounding_box()
    for node in page.locator(".graph-node").all():
        n = node.bounding_box()
        assert n["x"] >= v["x"] + 15
        assert n["y"] >= v["y"] + 15
        assert n["x"] + n["width"] <= v["x"] + v["width"] - 15
        assert n["y"] + n["height"] <= v["y"] + v["height"] - 15
    assert_map_contains_graph_and_view(page)
    # Leave only the selected node's child-button area intersecting the view.
    # The public camera API sets up this precise geometry; the real overview renders it.
    page.evaluate(
        """() => {
        const node = document.querySelector('.graph-node-selected');
        const p = EntityGraph.state.nodePositions[node.dataset.iri];
        EntityGraph.state.transform = {x: -p.x + 10, y: -(p.y + node.offsetHeight - 5), scale: 1};
        EntityGraph.applyTransform();
    }"""
    )
    expect(page.locator("#graph-view-summary")).to_contain_text("1 of 3 nodes visible")
    assert_map_contains_graph_and_view(page)
    # Oversized live geometry centers at the supported floor; it cannot all fit.
    page.get_by_role("button", name="Fit graph", exact=True).click()
    drag_node(page, selected, 15000, 0)
    page.get_by_role("button", name="Fit graph", exact=True).click()
    assert camera(page)["scale"] == 0.2
    expect(page.locator("#graph-view-summary")).not_to_contain_text(
        "3 of 3 nodes visible"
    )
    assert_map_contains_graph_and_view(page)


def test_resize_hide_and_fullscreen_preserve_camera_and_expansion(graph_page):
    page, requests = graph_page
    page.get_by_role("button", name="Show 3 children").click()
    expect(page.locator(".graph-node")).to_have_count(6)
    page.get_by_role("button", name="Zoom in", exact=True).click()
    before = camera(page)
    drawing = assert_map_contains_graph_and_view(page)
    handle = page.locator(".split-handle").bounding_box()
    page.mouse.move(handle["x"] + handle["width"] / 2, handle["y"] + 60)
    page.mouse.down()
    page.mouse.move(handle["x"] + 200, handle["y"] + 60)
    page.mouse.up()
    settled(page)
    assert camera(page) == before
    assert assert_map_contains_graph_and_view(page)["pixels"] != drawing["pixels"]
    page.locator("#tab-details").click()
    page.set_viewport_size({"width": 1100, "height": 850})
    settled(page)
    page.locator("#tab-graph").click()
    settled(page)
    assert camera(page) == before
    assert_map_contains_graph_and_view(page)
    page.get_by_role("button", name="Open graph in full screen").click()
    settled(page)
    assert camera(page) == before
    assert_map_contains_graph_and_view(page)
    page.keyboard.press("Escape")
    settled(page)
    assert camera(page) == before
    assert len(requests) == 2
    expect(page.locator(".graph-node")).to_have_count(6)


def test_expansion_restores_focus_without_stealing_it(graph_page):
    page, _ = graph_page
    expand = page.get_by_role("button", name="Show 3 children")
    expand.focus()
    page.keyboard.press("Enter")
    expect(page.locator(".graph-node")).to_have_count(6)
    expect(expand).to_be_focused()
    # A fresh graph and a held response let focus move before expansion completes.
    page.locator("#class-tree-root > .tree-node .node-label").nth(1).click()
    expect(page.locator(".graph-node")).to_have_count(3)
    held = []
    page.route(
        "**/explore/api/entity-graph/**?mode=children", lambda route: held.append(route)
    )
    expand.focus()
    page.keyboard.press("Space")
    expect(expand).to_be_focused()  # also pumps browser events so the route can arrive
    page.locator("#tab-details").click()
    page.locator("#tab-details").focus()
    assert held
    held[0].fulfill(
        json={
            "children": [
                {
                    "iri": "https://example.org/later",
                    "label": "Later child",
                    "child_count": 0,
                }
            ]
        }
    )
    page.wait_for_function(
        "() => document.querySelectorAll('.graph-node').length === 4"
    )
    expect(page.locator("#tab-details")).to_be_focused()


def test_dialog_trap_close_and_backdrop(graph_page):
    page, _ = graph_page
    trigger = page.get_by_role("button", name="Open graph in full screen")
    trigger.click()
    close = page.get_by_role("button", name="Close full-screen graph")
    expect(close).to_be_focused()
    page.keyboard.press("Shift+Tab")
    assert page.locator("#graph-modal-panel").evaluate(
        "p => p.contains(document.activeElement)"
    )
    page.keyboard.press("Tab")
    expect(close).to_be_focused()
    for _ in range(12):
        page.keyboard.press("Tab")
        assert page.locator("#graph-modal-panel").evaluate(
            "p => p.contains(document.activeElement)"
        )
    close.click()
    expect(trigger).to_be_focused()
    trigger.click()
    page.locator("#graph-modal-scrim").click(position={"x": 2, "y": 2})
    expect(trigger).to_be_focused()


@pytest.mark.parametrize("ratio", [1, 2])
def test_canvas_resolution_and_repeated_drawing(
    browser, browser_context_args, graph_payload, ratio
):
    # Real page and graph at each backing resolution, using an actual tree root.
    with browser.new_context(
        **{**browser_context_args, "device_scale_factor": ratio}
    ) as context:
        page = context.new_page()
        page.goto("/explore/tree")
        page.locator("#class-tree-root .node-label").first.click()
        page.locator("#tab-graph").click()
        expect(page.locator("#graph-minimap")).to_be_visible()
        settled(page)
        drawing = minimap_geometry(page)
        assert drawing["width"] == round(drawing["cw"] * ratio)
        assert drawing["height"] == round(drawing["ch"] * ratio)
        assert drawing["matrix"] == [ratio, 0, 0, ratio, 0, 0]
        page.evaluate(
            "() => { for (let i = 0; i < 5; i++) EntityGraph.renderMinimap(); }"
        )
        assert minimap_geometry(page)["pixels"] == drawing["pixels"]


def test_missing_canvas_context_keeps_controls_working(graph_page):
    page, _ = graph_page
    # Model an unavailable browser canvas capability, not a fake renderer.
    page.locator("#graph-minimap").evaluate("c => { c.getContext = () => null; }")
    before = camera(page)
    page.get_by_role("button", name="Pan down", exact=True).click()
    assert camera(page)["y"] == before["y"] - 80
    expect(page.locator("#graph-view-summary")).to_contain_text("nodes visible")


def test_replaced_hidden_and_loading_mounts_are_disposed(graph_page):
    page, _ = graph_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.evaluate(
        """() => {
        window.observers = new Set();
        const RealObserver = window.ResizeObserver;
        window.ResizeObserver = class extends RealObserver {
            constructor(callback) { super(callback); window.observers.add(this); }
            disconnect() { window.observers.delete(this); super.disconnect(); }
        };
        window.oldCanvas = document.querySelector('#graph-minimap');
        window.oldImage = window.oldCanvas.toDataURL();
        window.oldButton = document.querySelector('[data-graph-action=right]');
    }"""
    )
    for index in range(1, 5):
        page.locator("#class-tree-root > .tree-node > .node-content > .node-label").nth(
            index
        ).click()
        page.wait_for_function(
            "iri => EntityGraph.state.currentIri === iri",
            arg=page.locator("#class-tree-root > .tree-node")
            .nth(index)
            .get_attribute("data-id"),
        )
        expect(page.locator("#graph-minimap")).to_be_visible()
        settled(page)
        assert page.evaluate("window.observers.size") == 1
    assert page.evaluate("window.oldCanvas.toDataURL() === window.oldImage")
    before = camera(page)
    page.evaluate("window.oldButton.click()")
    assert camera(page) == before
    page.get_by_role("button", name="Pan right", exact=True).click()
    assert camera(page)["x"] == before["x"] - 80
    page.locator("#tab-details").click()
    page.set_viewport_size({"width": 1000, "height": 800})
    settled(page)
    assert page.evaluate(
        "Object.values(EntityGraph.state.transform).every(Number.isFinite)"
    )
    page.locator("#tab-graph").click()
    settled(page)
    assert_map_contains_graph_and_view(page)
    page.evaluate("EntityGraph.showSkeleton()")
    expect(page.locator("#entity-graph-pane")).to_have_attribute("aria-busy", "true")
    expect(page.locator("#graph-controls")).to_have_count(0)
    assert page.evaluate("window.observers.size") == 0
    page.evaluate("EntityGraph.showEmpty()")
    settled(page)
    expect(page.get_by_text("No entity selected", exact=True)).to_be_visible()
    assert not errors


def assert_controls_usable(page):
    if not page.evaluate("EntityGraph.state.isFullscreen"):
        tab = page.locator("#tab-graph").bounding_box()
        trigger = page.locator("#tab-fullscreen").bounding_box()
        assert tab["x"] + tab["width"] <= trigger["x"]
    controls = page.locator("#graph-controls")
    bounds = controls.bounding_box()
    buttons = controls.get_by_role("button")
    assert buttons.count() == 7
    for button in buttons.all():
        expect(button).to_be_visible()
        box = button.bounding_box()
        assert box["width"] >= 36 and box["height"] >= 36
        assert box["x"] >= bounds["x"] + 4
        assert box["y"] >= bounds["y"] + 4
        assert box["x"] + box["width"] <= bounds["x"] + bounds["width"] - 4
        assert box["y"] + box["height"] <= bounds["y"] + bounds["height"] - 4
    button = page.get_by_role("button", name="Pan left", exact=True)
    page.get_by_role("button", name="Fit graph", exact=True).focus()
    for _ in range(6):
        page.keyboard.press("Shift+Tab")
    expect(button).to_be_focused()
    assert button.evaluate("b => getComputedStyle(b).outlineWidth") == "3px"
    viewport = page.locator("#graph-viewport").bounding_box()
    assert viewport["height"] >= 180
    assert viewport["y"] >= bounds["y"] + bounds["height"] - 1
    overview = page.locator(".graph-overview").bounding_box()
    assert overview["y"] >= viewport["y"] + viewport["height"] - 1


def test_visual_evidence_narrow_and_enlarged_text(graph_page, pytestconfig):
    from pathlib import Path

    page, _ = graph_page
    output = pytestconfig.getoption("--graph-evidence-dir")
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)

    def screenshot(name):
        if output:
            page.screenshot(path=str(Path(output) / f"fa-2-graph-controls-{name}.png"))

    page.get_by_role("button", name="Show 3 children").click()
    expect(page.locator(".graph-node")).to_have_count(6)
    page.get_by_role("button", name="Fit graph", exact=True).click()
    assert_controls_usable(page)
    assert_map_contains_graph_and_view(page)
    screenshot("embedded")
    page.get_by_role("button", name="Open graph in full screen").click()
    settled(page)
    page.get_by_role("button", name="Fit graph", exact=True).click()
    assert_controls_usable(page)
    screenshot("fullscreen")
    page.keyboard.press("Escape")
    # A narrow desktop split-pane: resize the real divider to its upper limit.
    page.set_viewport_size({"width": 900, "height": 1000})
    handle = page.locator(".split-handle").bounding_box()
    page.mouse.move(handle["x"] + 2, handle["y"] + 50)
    page.mouse.down()
    page.mouse.move(550, handle["y"] + 50)
    page.mouse.up()
    settled(page)
    page.get_by_role("button", name="Fit graph", exact=True).click()
    assert_controls_usable(page)
    screenshot("narrow")
    # Stacked mobile layout and 200% text enlargement; no forced motion.
    page.set_viewport_size({"width": 390, "height": 844})
    page.emulate_media(reduced_motion="reduce")
    page.evaluate("document.documentElement.style.fontSize = '32px'")
    settled(page)
    page.locator("#graph-controls").scroll_into_view_if_needed()
    assert_controls_usable(page)
    page.get_by_role("button", name="Open graph in full screen").click()
    settled(page)
    assert_controls_usable(page)
    page.get_by_role("button", name="Pan left", exact=True).press("Enter")
    assert (
        page.locator(".graph-view-button").first.evaluate(
            "b => getComputedStyle(b).transitionDuration"
        )
        == "0s"
    )


def test_short_desktop_scroll_reveals_overview(graph_page):
    page, _ = graph_page
    page.set_viewport_size({"width": 1280, "height": 500})
    settled(page)
    controls = page.locator("#graph-controls").bounding_box()
    page.mouse.move(controls["x"] + 20, controls["y"] + 20)
    page.mouse.wheel(0, 600)
    page.wait_for_function(
        "() => document.querySelector('#tab-panel-graph').scrollTop > 0"
    )
    for selector in ("#graph-minimap", "#graph-view-summary"):
        assert page.locator(selector).evaluate("""el => {
            const r = el.getBoundingClientRect();
            const host = document.querySelector('#tab-panel-graph').getBoundingClientRect();
            const hit = document.elementFromPoint(r.x + r.width/2, r.y + r.height/2);
            return r.top >= host.top && r.bottom <= host.bottom && el.parentElement.contains(hit);
        }""")


def test_repeated_keyboard_expansion_keeps_focus(graph_page, graph_payload):
    page, _ = graph_page
    held = []

    def release_together(route):
        held.append(route)
        if len(held) == 2:
            for pending in held:
                pending.fulfill(json={"children": graph_payload["expansion"]})

    page.route("**/explore/api/entity-graph/**?mode=children", release_together)
    for attempt in range(8):
        if attempt:
            page.reload()
            page.locator("#tab-graph").click()
            expect(page.locator(".graph-node")).to_have_count(3)
        expand = page.get_by_role("button", name="Show 3 children")
        expand.focus()
        with page.expect_request("**/explore/api/entity-graph/**?mode=children"):
            page.keyboard.press("Enter")
        with page.expect_request("**/explore/api/entity-graph/**?mode=children"):
            page.keyboard.press("Enter")
        expect(page.locator(".graph-node")).to_have_count(6)
        settled(page)
        assert len(held) == 2
        expect(expand).to_be_focused()
        held.clear()


def test_first_fit_waits_for_hidden_graph_to_be_shown(page, graph_payload):
    held = []
    page.route("**/explore/api/entity-graph/**", lambda route: held.append(route))
    page.goto("/explore/tree")
    selected = page.locator("#class-tree-root > .tree-node").first
    expect(selected).to_be_visible()
    graph_payload["selected"]["iri"] = selected.get_attribute("data-id")
    for edge in graph_payload["edges"]:
        edge["target"] = graph_payload["selected"]["iri"]
    selected.locator(".node-label").first.click()
    with page.expect_request("**/explore/api/entity-graph/**"):
        page.locator("#tab-graph").click()
    page.locator("#tab-details").click()
    held[0].fulfill(json=graph_payload)
    expect(page.locator(".graph-node")).to_have_count(3)
    settled(page)
    assert camera(page) == {"x": 0, "y": 0, "scale": 1}
    page.locator("#tab-graph").click()
    expect(page.locator("#graph-view-summary")).to_contain_text("3 of 3 nodes visible")
    before = camera(page)
    assert before != {"x": 0, "y": 0, "scale": 1}
    page.set_viewport_size({"width": 1200, "height": 850})
    settled(page)
    assert camera(page) == before
    assert_map_contains_graph_and_view(page)


def test_offscreen_child_focus_cannot_scroll_the_camera(graph_page):
    page, _ = graph_page
    page.get_by_role("button", name="Open graph in full screen").click()
    for _ in range(20):
        page.get_by_role("button", name="Pan left", exact=True).click()
    before = camera(page)
    expect(page.locator("#graph-view-summary")).to_contain_text("0 of 3 nodes visible")
    close = page.get_by_role("button", name="Close full-screen graph")
    close.focus()
    page.keyboard.press("Shift+Tab")
    expect(page.get_by_role("button", name="Fit graph", exact=True)).to_be_focused()
    assert page.locator("#graph-viewport").evaluate(
        "v => v.scrollLeft === 0 && v.scrollTop === 0"
    )
    assert camera(page) == before
    assert_map_contains_graph_and_view(page)
    page.keyboard.press("Tab")
    expect(close).to_be_focused()
    page.keyboard.press("Escape")
    page.get_by_role("button", name="Fit graph", exact=True).focus()
    page.keyboard.press("Tab")
    assert not page.evaluate("document.activeElement.closest('.graph-node') !== null")
    assert page.locator("#graph-viewport").evaluate(
        "v => v.scrollLeft === 0 && v.scrollTop === 0"
    )
    page.get_by_role("button", name="Fit graph", exact=True).click()
    expect(page.locator(".graph-node-children-btn")).to_have_attribute("tabindex", "0")
