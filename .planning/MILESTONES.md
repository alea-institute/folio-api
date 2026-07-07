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

## v1.1 — Entity Graph ✓

**Shipped:** 2026-07-03 to production (`folio.openlegalstandard.org`) — PRs #18 (entity graph) + #19 (static cache-busting)
**Theme:** Ancestor-rooted, interactive entity graph on `/explore/tree`, ported from folio-enrich (elkjs + cubic-bezier SVG), plus a static-asset cache-busting fix so deploys never serve stale JS/CSS.

**What shipped:**
- **Entity Graph tab** on `/explore/tree` — ancestor-rooted hierarchical graph (elkjs layout, cubic-bezier SVG edges), lazy-loaded on tab activation (GRAPH-01…05).
- Full-screen pop-out modal with preserved state; click-a-node to select the IRI in the left tree; `+N Children` expansion merging into the live graph.
- Multi-path ancestry + `rdfs:seeAlso` edges; 50/50 detail|graph tab split; node drag-to-rearrange with live edge redraws.
- **Static-asset cache-busting** (PR #19, `d03b226`): `?v=<newest-mtime>` URL stamping + `CachedStaticFiles` sending `Cache-Control: public, max-age=3600, must-revalidate`; regression tests in `tests/test_static_cache.py`. Also folded prod deploy drift into the repo (XAI_API_KEY in compose, `soli.openlegalstandard.org` Caddy block; dropped the `rate_limit` directive that required an absent Caddy plugin).

**Prod deploy mechanism (bare-metal EC2):** `13.59.153.110:/home/ubuntu/src/folio-api` — SSH (key `soli-api.pem`), preserve server-local drift, `git fetch origin && git reset --hard origin/main`, re-apply drift, `docker compose up -d --build` (`./run.sh prod`). Documented in `docs/plans/2026-07-02-001-chore-deploy-entity-graph-to-prod-plan.md`. Cache-busting verified live on both prod and dev 2026-07-07 (versioned URLs + Cache-Control headers present).

**Archived plans:** `.planning/archive/v1.1/01-entity-graph/`

**Key learnings carried forward:**
- Starlette `StaticFiles` sends no `Cache-Control` by default → heuristic browser freshness serves stale JS after deploys. Version-stamp asset URLs AND set explicit `Cache-Control` together.
- FastAPI-on-Hetzner/EC2 deploys carry server-local drift (LLM provider config, extra vhosts, env vars). Folding that drift into the repo (as PR #19 began) removes a recurring manual re-apply step and deploy risk.

---
