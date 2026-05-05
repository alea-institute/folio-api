# Milestone 001 — Tree page UX polish

## Goal

Tighten the chrome and tree controls on the three tree pages (`/explore/tree`, `/properties/tree`, `/taxonomy/tree`) so they match folio-enrich's expand/collapse UX and feel more compact.

## Decisions (locked via Q&A)

| # | Decision | Choice |
|---|---|---|
| 1 | Scope | All three tree pages (header globally, controls per-page) |
| 2 | Expand-one-level semantics | Depth-N from root |
| 3 | Depth N | 2 (sections + top branches + direct children visible) |
| 4 | "Explore FOLIO" h2 | Pure removal |
| 5 | Help-text line | Keep as-is |
| 6 | Button visual style | Match folio-api Tailwind blue palette |
| 7 | Process | One focused milestone |

## Changes

### 1. Compact header (3 templates)

`explore/tree.html:12`, `properties/tree.html:12`, `taxonomy/tree.html:12`:
- `py-6` → `py-3` on `<header>`
- Reduce title from `text-3xl` → `text-2xl` if it still feels tall after the padding cut

### 2. Remove redundant 'Explore FOLIO' h2

`explore/tree.html:155-157` — delete the `<h2>Explore FOLIO</h2>` and its wrapping `<div class="flex justify-between ...">`. Audit other two for any analogous redundant headings (preliminary scan: properties and taxonomy use just the search field, no extra h2 — confirm during edit).

### 3. Segmented expand/collapse buttons

Replace the two-button bar:
```html
<button id="expand-all-tree">Expand All</button>
<button id="collapse-all-tree">Collapse All</button>
```
With folio-enrich's segmented two-group pattern:
```
[ ▼ Expand ][ ▼▼ ]    [ ▶▶ Collapse ][ ▶ ]
   depth-2    all-of    all-collapse  one-level
```

Re-skin to folio-api's blue/white Tailwind palette:
- Group container: `inline-flex border border-blue-200 rounded overflow-hidden`
- Buttons: `bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs px-2 py-0.5`
- Icon-only second button: `border-l border-blue-200 px-1.5`

Apply to all three templates. Wire up new JS:
- `expandToDepth(n)` — expand all nodes whose ancestor-count < n-1, collapse the rest
- `collapseOneLevel()` — find deepest expanded depth, collapse nodes at that depth
- Existing `expandAllNodes()` / `collapseAllNodes()` reused for the secondary buttons

Add to all three: `unified_tree.js`, `property_tree.js`, `taxonomy_tree.js`.

## Verification

Boot dev server. Use chrome-devtools MCP to navigate to each tree page; screenshot; verify:
- Header appears compact (~24px vertical padding instead of 48px)
- "Explore FOLIO" no longer present on `/explore/tree`
- New segmented buttons render in folio-api blue palette
- Click `▼ Expand` once → tree expands to depth 2 (sections + top branches + their direct children visible)
- Click `▼▼` → fully expands
- Click `▶▶ Collapse` → fully collapses
- Click `▶` → collapses just the deepest expanded layer

## Status

Active.
