---
phase: 01-entity-graph
plan: 13
subsystem: frontend
tags: [frontend, modal, fullscreen, accessibility, dom-swap]
requires:
  - 01-03  # entity_graph.js skeleton + state.isFullscreen + ICONS
  - 01-05  # #detail-tabs + #tab-panel-graph + wireDetailTabs activate()
  - 01-06  # tree.html template scaffold the modal lives in
  - 01-08  # SVG/DIV scaffold (#graph-viewport, #graph-transform) — must survive swap
  - 01-10  # pan/zoom transform tracking + applyTransform — must persist across swap
provides:
  - "Real toggleFullscreen() — replaces Plan 03 stub"
  - "DOM-swap state preservation: #entity-graph-pane moves between in-pane and modal hosts via appendChild"
  - "ESC + scrim + X-button modal dismissal"
  - "Focus trap inside modal panel; focus returns to Full screen button on close"
  - "Modal animation (200 ms ease-out-quint) with prefers-reduced-motion override"
affects:
  - "folio_api/static/js/unified_tree.js wireDetailTabs activate(): toggles #tab-fullscreen visibility per tab"
tech-stack:
  added: []           # No new deps — pure DOM/Tailwind/CSS work
  patterns: ["DOM-Swap State Preservation (RESEARCH Pattern 2)", "Focus trap (sentinel-free Tab cycling)", "Modal scrim + panel layered z-50"]
key-files:
  created: []
  modified:
    - folio_api/templates/jinja2/explore/tree.html
    - folio_api/static/js/entity_graph.js
    - folio_api/static/js/unified_tree.js
    - folio_api/static/css/styles.css
decisions:
  - "DOM-swap via appendChild() preserves the SAME nodes — pan/zoom transform, expanded children, SVG, and event listeners all survive without manual re-wiring (D-07 + RESEARCH Pattern 2)."
  - "Per D-26, after the swap we re-call applyTransform() rather than fitGraph(): fullscreen toggle is a viewport size change but the user's zoom level is preserved. fitGraph is reserved for fresh entity selections."
  - "Focus trap uses a panel-scoped keydown listener (not sentinel divs). The two-focusable case (close button + graph host) is sufficient for v1.1 because graph nodes are not individually tab-focusable per UI-SPEC §Interaction Contract."
  - "The Full screen button lives in the tab strip with ml-auto so it pins to the right edge; visibility is toggled by wireDetailTabs activate() — hidden on Details, visible on Entity Graph."
  - "Idempotent listener wiring via dataset flags (fsWired, fsEscWired, fsTrapWired) so re-init is safe."
metrics:
  duration: ~10 min
  completed: 2026-05-06
  tasks: 3
  files: 4
---

# Phase 1 Plan 13: Full-Screen Graph Modal Summary

**One-liner:** Real `toggleFullscreen()` replaces the Plan 03 stub — `#entity-graph-pane` is `appendChild()`-swapped between `#tab-panel-graph` (in-pane) and `#graph-modal-host` (modal), preserving pan/zoom/expanded children because the SAME DOM nodes move; ESC + scrim + X-button dismiss; focus is trapped while open and returns to the Full screen button on close.

## What Was Built

### tree.html (Task 1)
- **Full screen button** appended to `#detail-tabs` after the Entity Graph tab. Hidden by default (Tailwind `hidden` class); revealed by `wireDetailTabs` when the Graph tab is active. Carries `aria-label="Open graph in full screen"`, an `arrows-pointing-out` Heroicon hydrated at runtime, and a visible "Full screen" text label.
- **Modal shell** (`#graph-modal-root`) appended just before `{% block scripts %}`: hidden by default (`hidden`, `aria-hidden="true"`), `z-50`, `fixed inset-0`. Contains `#graph-modal-scrim` (dark backdrop), `#graph-modal-panel` (`role=dialog` + `aria-modal=true` + `aria-labelledby`), header with `#graph-modal-title` ("Entity Graph") and `#graph-modal-close` (X icon), and the destination host `#graph-modal-host`.

### entity_graph.js (Task 2)
- **`toggleFullscreen()`** — replaces the Plan 03 stub. Branches on `state.isFullscreen`:
  - **Open:** `modalHost.appendChild(pane)` → unhides modal → focuses close button → re-applies transform.
  - **Close:** `inPaneHost.appendChild(pane)` → hides modal → returns focus to Full screen button → re-applies transform.
- **`_wireFullscreenChrome()`** — called from `init()`. Hydrates icons in the Full screen and X buttons, binds clicks on both + scrim, attaches a global `keydown`/Escape listener (cheap when modal is closed thanks to the `state.isFullscreen` guard), and a panel-scoped Tab handler for focus trapping. Idempotent via `dataset.fsWired` / `dataset.fsEscWired` / `dataset.fsTrapWired` flags.

### unified_tree.js wireDetailTabs (Task 2 cont.)
- `activate()` now toggles `.hidden` on `#tab-fullscreen` based on `detailsActive` — Details hides it, Graph shows it.

### styles.css (Task 3)
- `#graph-modal-root.hidden { display: none; }`
- 200 ms `cubic-bezier(0.16, 1, 0.3, 1)` opacity transition on `#graph-modal-scrim`
- 200 ms ease-out-quint opacity + transform transition on `#graph-modal-panel`
- `prefers-reduced-motion: reduce` zeroes both transitions

## DOM-Swap State Preservation (D-07)

The pattern is the headline correctness property of this plan:

```
[Before open]                    [After open]
#tab-panel-graph                 #tab-panel-graph
└── #entity-graph-pane           └── (empty)
    └── #graph-viewport
        └── #graph-transform     #graph-modal-host
            ├── #graph-svg       └── #entity-graph-pane          ← SAME NODE
            └── .graph-nodes         └── #graph-viewport         ← same children
                                         └── #graph-transform    ← transform preserved
                                             ├── #graph-svg      ← all event listeners intact
                                             └── .graph-nodes
```

`appendChild(existingNode)` in DOM semantics detaches the node from its current parent and reattaches it to the new parent **without cloning**. Result:
- The pan/zoom transform on `#graph-transform` survives unchanged.
- The wheel + mousedown listeners on `#graph-viewport` survive unchanged.
- The delegated click listener on `.graph-nodes` survives unchanged.
- `state.expandedIris` and `state.transform` (closure-scoped, not DOM-bound) are independent of the swap.

## Verification

- `node --check folio_api/static/js/entity_graph.js` — exit 0
- `node --check folio_api/static/js/unified_tree.js` — exit 0
- `uv run pytest --no-cov` — **13/13 passed**
- All grep markers found in target files (`tab-fullscreen`, `graph-modal-root`, `graph-modal-host`, `graph-modal-close`, `function toggleFullscreen`, `Escape`, `isFullscreen`, `graph-modal-scrim`, `graph-modal-panel`, `cubic-bezier(0.16`)

## Manual UAT Plan (for verifier)

1. Open `/explore/tree`, click any tree entity, click **Entity Graph** tab → graph renders.
2. Pan + zoom + click `+N Children` to expand a child → confirm the graph reflects all three.
3. Click **Full screen** (top-right of tab strip) → modal opens with the same graph state (pan/zoom/expansions intact).
4. Press **ESC** → modal closes; in-pane graph still shows the same state; focus is back on the Full screen button.
5. Click **Full screen** again → modal opens; click the **scrim** (dark area outside the panel) → modal closes.
6. Click **Full screen** again → modal opens; press **Tab** repeatedly → focus cycles within the panel; press **Shift+Tab** at the first focusable → wraps to the last.
7. Click **X** → modal closes; focus returns to the Full screen button.
8. Switch to **Details** tab → Full screen button hides. Switch back to **Entity Graph** → it reappears.

## Deviations from Plan

None — plan executed exactly as written. The plan's optional Task 2 update to wireDetailTabs (in `unified_tree.js`) was applied.

## Commits

| Task | Commit  | Title                                                                  |
| ---- | ------- | ---------------------------------------------------------------------- |
| 1    | 04cf499 | feat(01-13): Full screen button + modal shell in tree.html             |
| 2    | 3c378d9 | feat(01-13): real toggleFullscreen — DOM-swap + ESC + scrim + focus trap |
| 3    | e5393bf | feat(01-13): modal scrim + panel transitions + reduced-motion override |

## Self-Check: PASSED

- `folio_api/templates/jinja2/explore/tree.html` — FOUND, contains `tab-fullscreen` + `graph-modal-root` + `graph-modal-host` + `graph-modal-close`
- `folio_api/static/js/entity_graph.js` — FOUND, `function toggleFullscreen` real impl + `_wireFullscreenChrome` + `Escape` handler + `isFullscreen` state branch
- `folio_api/static/js/unified_tree.js` — FOUND, `tab-fullscreen` visibility toggle in `activate()`
- `folio_api/static/css/styles.css` — FOUND, `#graph-modal-scrim` + `#graph-modal-panel` + `cubic-bezier(0.16` + reduced-motion override
- Commits 04cf499, 3c378d9, e5393bf — all FOUND in `git log`
- pytest --no-cov — 13/13 passed
- `node --check` on both JS files — exit 0
