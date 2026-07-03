# Milestones

Record of shipped milestones. Active milestone is tracked in `STATE.md` and `ROADMAP.md`.

---

## v1.0 — Tree page UX polish ✓

**Shipped:** 2026-05-05 (PRs #14, #15, #16)
**Theme:** Tighten the chrome and tree controls on the explore tree to match the folio-enrich UX.

**What shipped:**
- Compact header on `/explore/tree` (`py-6` → `py-3`, `text-3xl` → `text-2xl`)
- Removed redundant "Explore FOLIO" h2 heading
- Segmented expand/collapse buttons (`▼ Expand to depth 2`, `▼▼ Expand all`, `▶▶ Collapse all`, `▶ Collapse one level`) — Tailwind blue palette
- Hotfix: pinned Docker deps via uv.lock to avoid Starlette 1.0 breakage (`5190bd8`)
- Removed deprecated `/properties/tree` and `/taxonomy/tree` templates and JS (`e28c82c`)
- Fix: exclude non-English translations from Alternative Labels (PR #16, `8f1f9b6`)

**Donor pattern reused:** folio-enrich's segmented expand/collapse (`frontend/index.html` ~line 8062).

**Archived plan:** `.planning/archive/v1.0/001-tree-ux-polish/PLAN.md`

**Key learnings carried forward:**
- folio-enrich is the right donor for FOLIO-tree UX patterns — same stack, copy-paste-friendly.
- Removing the legacy `/properties/tree` and `/taxonomy/tree` routes was the right call; `/explore/tree` is sufficient.

---

## v1.1 — Entity Graph (active)

**Status:** Defining — see `REQUIREMENTS.md`, `ROADMAP.md`, and `phases/01-entity-graph/CONTEXT.md`.
