"""Opt-in browser fixtures, deliberately outside the API conftest ancestry."""

import copy
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect


def pytest_addoption(parser):
    parser.addoption(
        "--graph-evidence-dir", help="Save the three fa-2 screenshots here"
    )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, base_url):
    if not base_url:
        raise pytest.UsageError(
            "Start the local app and supply --base-url http://127.0.0.1:9616"
        )
    return {**browser_context_args, "viewport": {"width": 1440, "height": 1000}}


@pytest.fixture
def graph_payload():
    return json.loads(
        (Path(__file__).parent / "fixtures/entity_graph.json").read_text()
    )


@pytest.fixture
def graph_page(page, graph_payload):
    """Real page/tree/assets/ELK, with deterministic graph API data only."""
    requests = []

    def respond(route):
        requests.append(route.request.url)
        data = copy.deepcopy(graph_payload)
        if "mode=children" in route.request.url:
            data["children"] = data.pop("expansion")
        else:
            data.pop("expansion")
        route.fulfill(json=data)

    page.route("**/explore/api/entity-graph/**", respond)
    page.goto("/explore/tree")
    expect(
        page.locator("#class-tree-root > .tree-node .node-label").first
    ).to_be_visible()
    # Match the fixture's focus to a real tree selection without replacing the tree.
    selected = page.locator("#class-tree-root > .tree-node").first
    graph_payload["selected"]["iri"] = selected.get_attribute("data-id")
    graph_payload["selected"]["label"] = selected.locator(
        ".node-label"
    ).first.inner_text()
    for edge in graph_payload["edges"]:
        edge["target"] = graph_payload["selected"]["iri"]
    selected.locator(".node-label").first.click()
    page.locator("#tab-graph").click()
    expect(page.locator(".graph-node")).to_have_count(3)
    page.wait_for_function(
        "() => EntityGraph.state.transform.scale > 0 && document.querySelector('#graph-viewport').clientHeight > 0"
    )
    # Ensure normal Tailwind styling has arrived; an unstyled page is not evidence.
    page.wait_for_function(
        "() => getComputedStyle(document.querySelector('#tab-graph')).fontWeight === '600'"
    )
    page.evaluate(
        "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
    )
    return page, requests
