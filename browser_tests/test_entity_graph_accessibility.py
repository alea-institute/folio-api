"""Keyboard and rendered-overview regressions for the replacement graph PR."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from browser_tests.entity_graph_controls import (
    assert_controls_usable,
    assert_map_contains_graph_and_view,
    camera,
    settled,
)

CONTROLS = (
    "Pan left",
    "Pan up",
    "Pan down",
    "Pan right",
    "Zoom out",
    "Zoom in",
    "Fit graph",
)


def tab_to_control(page, name, *, backwards=False):
    """Enter through the pane's preceding focus target, then use native Tab."""
    anchor = (
        "#graph-modal-close"
        if page.get_by_role("dialog").is_visible()
        else "#tab-fullscreen"
    )
    page.locator(anchor).focus()
    steps = len(CONTROLS) if backwards else CONTROLS.index(name) + 1
    for _ in range(steps):
        page.keyboard.press("Tab")
    if backwards:
        for _ in range(len(CONTROLS) - 1 - CONTROLS.index(name)):
            page.keyboard.press("Shift+Tab")
    button = page.get_by_role("button", name=name, exact=True)
    expect(button).to_be_focused()
    assert button.evaluate("b => b.matches(':focus-visible')")
    return button


def keyboard_fullscreen(page, key="Enter"):
    page.locator("#tab-graph").focus()
    page.keyboard.press("Tab")
    expect(page.get_by_role("button", name="Open graph in full screen")).to_be_focused()
    page.keyboard.press(key)
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.get_by_role("button", name="Close full-screen graph")).to_be_focused()
    settled(page)


def expand_by_keyboard(page, key="Enter"):
    tab_to_control(page, "Fit graph")
    page.keyboard.press("Tab")
    expand = page.get_by_role("button", name="Show 3 children")
    expect(expand).to_be_focused()
    page.keyboard.press(key)
    expect(page.locator(".graph-node")).to_have_count(6)
    settled(page)
    expect(expand).to_be_focused()


def assert_nodes_fit(page):
    viewport = page.locator("#graph-viewport").bounding_box()
    for node in page.locator(".graph-node").all():
        box = node.bounding_box()
        assert box["x"] >= viewport["x"]
        assert box["y"] >= viewport["y"]
        assert box["x"] + box["width"] <= viewport["x"] + viewport["width"]
        assert box["y"] + box["height"] <= viewport["y"] + viewport["height"]


@pytest.mark.parametrize("fullscreen", [False, True], ids=["embedded", "fullscreen"])
@pytest.mark.parametrize("key", ["Enter", "Space"])
@pytest.mark.parametrize("name", CONTROLS)
def test_every_control_with_native_keyboard(graph_page, fullscreen, key, name):
    page, requests = graph_page
    expand_by_keyboard(page)
    if fullscreen:
        keyboard_fullscreen(page)
    tab_to_control(page, "Fit graph").press("Enter")
    selected = page.locator(".graph-node-selected").get_attribute("data-iri")
    expanded = page.evaluate("[...EntityGraph.state.expandedIris]")
    assert expanded
    if name == "Fit graph":
        tab_to_control(page, "Pan right").press("Enter")
        for _ in range(19):
            page.keyboard.press("Enter")
        expect(page.locator("#graph-view-summary")).to_contain_text(
            "0 of 6 nodes visible"
        )
    button = tab_to_control(page, name, backwards=key == "Space")
    before = camera(page)
    node_before = page.locator(".graph-node-selected").bounding_box()
    button.press(key)
    settled(page)
    after = camera(page)
    node_after = page.locator(".graph-node-selected").bounding_box()
    if name.startswith("Pan"):
        axis, delta = {
            "Pan left": ("x", 80),
            "Pan up": ("y", 80),
            "Pan down": ("y", -80),
            "Pan right": ("x", -80),
        }[name]
        assert after == {**before, axis: pytest.approx(before[axis] + delta)}
        assert node_after[axis] == pytest.approx(node_before[axis] + delta, abs=1)
    elif name.startswith("Zoom"):
        factor = 1.12 if name == "Zoom in" else 1 / 1.12
        assert after["scale"] == pytest.approx(before["scale"] * factor)
        assert node_after["width"] == pytest.approx(
            node_before["width"] * factor, abs=1
        )
    else:
        assert after != before
        assert_nodes_fit(page)
        expect(page.locator("#graph-view-summary")).to_contain_text(
            "6 of 6 nodes visible"
        )
    expect(button).to_be_focused()
    expect(page.locator(".graph-node-selected")).to_have_attribute("data-iri", selected)
    expect(page.locator(".graph-node")).to_have_count(6)
    assert page.evaluate("[...EntityGraph.state.expandedIris]") == expanded
    assert len(requests) == 2
    announcement = page.get_by_role("status")
    expect(page.locator("#graph-view-announcement")).to_have_attribute(
        "aria-live", "polite"
    )
    expect(announcement.filter(has_text=name + ".")).to_have_text(
        name + ". " + page.locator("#graph-view-summary").inner_text()
    )
    assert_map_contains_graph_and_view(page)


@pytest.mark.parametrize("key", ["Enter", "Space"])
def test_fullscreen_keyboard_round_trip(graph_page, key):
    page, requests = graph_page
    expand_by_keyboard(page)
    pane = page.locator("#entity-graph-pane").element_handle()
    before = camera(page)
    keyboard_fullscreen(page, key)
    assert camera(page) == before
    tab_to_control(page, "Pan down").press(key)
    moved = camera(page)
    assert moved["y"] == before["y"] - 80
    # Shift+Tab from the first control reaches the dialog's close button.
    tab_to_control(page, "Pan left")
    page.keyboard.press("Shift+Tab")
    expect(page.get_by_role("button", name="Close full-screen graph")).to_be_focused()
    page.keyboard.press(key)
    expect(page.get_by_role("dialog")).to_be_hidden()
    expect(page.locator("#tab-fullscreen")).to_be_focused()
    settled(page)
    assert camera(page) == moved
    assert pane.evaluate("p => p === document.querySelector('#entity-graph-pane')")
    page.keyboard.press("Tab")
    expect(page.get_by_role("button", name="Pan left", exact=True)).to_be_focused()
    page.keyboard.press(key)
    assert camera(page)["x"] == moved["x"] + 80
    expect(page.locator(".graph-node")).to_have_count(6)
    assert len(requests) == 2


@pytest.mark.parametrize("key", ["Enter", "Space"])
def test_keyboard_expansion_immediately_updates_minimap(graph_page, key):
    page, requests = graph_page
    before_camera = camera(page)
    before_drawing = assert_map_contains_graph_and_view(page)
    selected = page.locator(".graph-node-selected").get_attribute("data-iri")
    expand_by_keyboard(page, key)
    # No Fit, resize, or pan may rescue a stale overview after the remount.
    assert camera(page) == before_camera
    expect(page.locator(".graph-node-selected")).to_have_attribute("data-iri", selected)
    drawing = assert_map_contains_graph_and_view(page)
    assert drawing["pixels"] != before_drawing["pixels"]
    visible = page.locator(".graph-node").evaluate_all(
        """nodes => {
        const v = document.querySelector('#graph-viewport').getBoundingClientRect();
        return nodes.filter(node => {
            const r = node.getBoundingClientRect();
            return r.right >= v.left && r.left <= v.right && r.bottom >= v.top && r.top <= v.bottom;
        }).length;
    }"""
    )
    expect(page.locator("#graph-view-summary")).to_have_text(
        f"{visible} of 6 nodes visible · {round(before_camera['scale'] * 100)}% zoom."
    )
    assert len(requests) == 2


def test_passive_minimap_exposes_readable_summary_without_tab_stop(graph_page):
    page, _ = graph_page
    canvas = page.locator("#graph-minimap")
    expect(canvas).to_have_attribute("aria-hidden", "true")
    assert canvas.evaluate("c => c.tabIndex") == -1
    summary = page.locator("#graph-view-summary")
    expect(summary).to_be_visible()
    expect(summary).to_contain_text("3 of 3 nodes visible")
    assert "3 of 3 nodes visible" in page.locator(".graph-overview").aria_snapshot()
    assert canvas.aria_snapshot() == ""
    keyboard_fullscreen(page)
    tab_to_control(page, "Fit graph")
    page.keyboard.press("Tab")
    expect(page.get_by_role("button", name="Show 3 children")).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.get_by_role("button", name="Close full-screen graph")).to_be_focused()


def test_isolated_server_serves_both_ontologies(page):
    health = page.request.get("/info/health")
    assert health.ok
    assert health.json()["folio_graph"]["num_classes"] > 0
    for ontology in ("folio", "canon"):
        response = page.request.get(
            f"/taxonomy/tree/data?node_id=%23&ontology={ontology}"
        )
        assert response.ok
        assert response.json()


def test_replacement_visual_evidence(graph_page, pytestconfig):
    page, _ = graph_page
    output = pytestconfig.getoption("--fa6-evidence-dir")
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)

    def capture(name):
        tab_to_control(page, "Fit graph").press("Enter")
        settled(page)
        assert_controls_usable(page)
        assert_map_contains_graph_and_view(page)
        expect(page.locator("#graph-view-summary")).to_contain_text(
            "6 of 6 nodes visible"
        )
        if output:
            page.screenshot(path=str(Path(output) / f"fa-6-graph-controls-{name}.png"))

    expand_by_keyboard(page)
    capture("embedded")
    keyboard_fullscreen(page)
    capture("fullscreen")
    page.keyboard.press("Escape")
    page.set_viewport_size({"width": 900, "height": 1000})
    handle = page.locator(".split-handle").bounding_box()
    page.mouse.move(handle["x"] + 2, handle["y"] + 50)
    page.mouse.down()
    page.mouse.move(550, handle["y"] + 50)
    page.mouse.up()
    settled(page)
    capture("narrow")
