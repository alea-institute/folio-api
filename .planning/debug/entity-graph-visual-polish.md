---
status: resolved
trigger: |
  BUG 1: The graph is ugly. [Image #9] Not nearly as beautiful as folio-enrich [Image #10] or folio-mapper [Image #11]. Can you please make this entity graph as beautiful. Use as much code from folio-enrich and folio-mapper as you'd like. Both repos are on this machine. BUG 2: The webpage does NOT use the page's full width, with wide wasted white space on each side. [Image #12] Please allow the system to utilize 100% of the horizontal space.
created: 2026-05-08T14:25:00Z
updated: 2026-05-08T10:10:00Z
---

## Current Focus

hypothesis: Two distinct issues sharing the `/explore/tree` page — both confirmed and fixed.
test: null
expecting: null
next_action: null
reasoning_checkpoint: null
tdd_checkpoint: null

## Symptoms

expected: |
  Entity Graph tab renders with the same level of visual polish as folio-enrich's
  graph (Image #10): bold node labels, descendant-count badges (e.g. "+13"),
  legend at bottom, minimap, focus highlight (red ring on the focused entity),
  dotted/grid background, clean blue subClassOf arrows, dashed purple seeAlso
  edges with labels. Page also expands to use the full viewport width — no
  wasted whitespace on left/right.

actual: |
  Entity Graph tab renders with: thin/small node labels, no badges, no legend,
  no minimap, no focus highlight, plain white background, hairline edges.
  Page has substantial left + right whitespace gutters even on a wide screen,
  visible in Image #9 / #12 (folio-api preview).

errors: none — purely visual

reproduction: |
  Open https://folio-api-preview-production.up.railway.app/explore/tree, click
  any node (e.g. Maritime Negligence), then click the "Entity Graph" tab in the
  right pane. Observe styling vs folio-enrich (enrich.openlegalstandard.org)
  and folio-mapper (mapper.openlegalstandard.org).

started: |
  Always — Phase 1 of milestone v1.1 shipped a functional but visually minimal
  entity graph. Reference implementations have been on enrich/mapper for some
  time. User explicitly compared the two on 2026-05-08 in this session.

## Eliminated
- All JS logic (ELK layout, pan/zoom, expand, tab switching) is intact — purely CSS/DOM visual gap
- Backend entity-graph API is correct — returns proper nodes/edges/branch_root_type data

## Evidence

- timestamp: 2026-05-08T10:00:00Z
  finding: |
    BUG 2 ROOT CAUSE: base.html line 59 wraps `<main>` with Tailwind class `container mx-auto px-4
    max-w-[1600px]`. Tree template used `-mx-4` on the content div to negate horizontal padding
    but NOT the `container` max-width constraint. Result: left/right gutters at wide viewports.
    Fix: add `max-width: none !important; padding-left: 0 !important; padding-right: 0 !important;`
    to the `main {}` override block in tree.html's `<style>` tag, and remove `-mx-4`.

- timestamp: 2026-05-08T10:00:00Z
  finding: |
    BUG 1 ROOT CAUSE (delta inventory from comparing folio-api vs folio-enrich/folio-mapper):
    1. Edges: folio-api used gray-400 (#9CA3AF) hairline edges with NO arrowheads.
       Reference: blue (#3b82f6) edges with SVG `<marker>` arrowheads on subClassOf.
    2. Node borders: folio-api used border-gray-300 for all non-selected nodes.
       Reference: red 3px for ultimate-root, gray 3px for ancillary-root, blue 2px for selected.
    3. Background: folio-api plain white. Reference: dotted grid (radial-gradient dots).
    4. Minimap: entirely missing. Reference: canvas-based minimap bottom-right corner.
    5. Legend bar: entirely missing. Reference: bottom strip with subClassOf/seeAlso/Focus/
       Ultimate Ancestor/Ancillary Ancestor items + "Click to expand..." hint.
    6. Selected glow only (box-shadow). Reference: blue border + blue tinted bg.
    7. No ancillary-root detection. Reference: gray 3px border for ancillary ancestors.
    8. Hover badge font: was small/light. Reference: bold.
    9. Node label: was text-sm. Reference: text-xs bold for roots, text-xs semibold for selected.

## Resolution

root_cause: |
  BUG 1: entity_graph.js rendered graph with gray hairline edges, no arrowheads, plain white
  background, no minimap, no legend, and minimal node border differentiation. The Phase 1 ship
  deferred these visual items (noted in LEARNINGS.md).
  BUG 2: base.html `<main class="container mx-auto px-4 py-4 max-w-[1600px]">` imposed a
  max-width constraint that the tree template's `-mx-4` only partially negated (removed padding
  but not container max-width).

fix: |
  BUG 1 fixes in entity_graph.js + styles.css:
  - Blue (#3b82f6) subClassOf edges with SVG arrowhead marker (#arrow-sub)
  - Red 3px border for ultimate-root nodes (.graph-node-root > div)
  - Gray 3px border for ancillary-root nodes (.graph-node-ancillary > div)
  - Blue border + bg tint for selected node (.graph-node-selected > div)
  - Dotted grid background on #entity-graph-pane (radial-gradient dots)
  - Canvas-based minimap (#graph-minimap, 140x90) at bottom-right corner
  - Legend bar (#graph-legend) with subClassOf/seeAlso/Focus/Root/Ancillary items + hint strip
  - Grabbing cursor class (graph-grabbing) on pan start/end
  - Bold/semibold node label typography upgrade
  - title tooltip on truncated labels
  BUG 2 fix in tree.html: added max-width: none !important + padding-left/right: 0 !important
  to the main{} override block; removed -mx-4 from content container.

files_changed:
  - folio_api/static/css/styles.css
  - folio_api/static/js/entity_graph.js
  - folio_api/templates/jinja2/explore/tree.html

verification: |
  - 13/13 tests pass (uv run pytest tests/ -q)
  - 10/10 entity_graph route tests pass
  - Screenshot confirms full-width layout (no gutters at 1400px viewport)
  - CSS served correctly: dotted bg, blue edges, red root borders, minimap, legend
  - JS served correctly: arrow-sub marker, renderMinimap, ancillary root detection, grabbing cursor
