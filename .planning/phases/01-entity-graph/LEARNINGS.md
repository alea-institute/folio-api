---
phase: 1
slug: entity-graph
status: complete
created: 2026-05-08
purpose: Hard-won lessons from Phase 1 execution + 5 Railway deploy attempts + 2 post-UAT bug fixes. Read before extending the entity graph or deploying any FastAPI app from this codebase.
---

# Phase 1 — Learnings

## The 5 Railway deploy attempts

Future agents deploying any FastAPI service in this codebase: don't repeat these.

| # | Failure mode | Root cause | Fix | Commit |
|---|---|---|---|---|
| 1 | Build error: `"/uv.lock": not found` | `uv.lock` was gitignored under "Package manager lock files" — that's a library-style convention, wrong for an app deployed via `uv sync --frozen` | Untrack `uv.lock`, commit it, document why in `.gitignore` | `713ebc7` |
| 2 | "1/1 replicas never became healthy" — 11 healthcheck attempts in 2 min | Default Railway healthcheck timeout (120s) too short for FOLIO cold-start (downloads ~80MB OWL from GitHub + parses 18,323 classes) | `healthcheckTimeout: 300` in `railway.json` | `af0075e` |
| 3 | Same healthcheck failures, no visible logs to diagnose | Python stdout block-buffered when piped (Docker default). Uvicorn `INFO: Started…` and any traceback never reached `railway logs` | `ENV PYTHONUNBUFFERED=1` in Dockerfile | `0216e90` |
| 4 | App crashed at startup with `ValueError: OpenAI API key not found` | `alea_llm_client.OpenAIModel.__init__` raises if no key resolves from init kwargs / env / key file. v1.1 tree+graph features have ZERO LLM dependency, but startup hard-required a key | Skip LLM client construction when no key is resolvable; pass `llm=None` to `FOLIO()`. `/search` fails at call time (correct), startup succeeds | `fc35f48` |
| 5 | (success) | — | — | — |

**Take-away:** for any FastAPI app in this repo, `railway.json` should set `healthcheckTimeout: 300` AND `Dockerfile` MUST have `PYTHONUNBUFFERED=1`. Verify uv.lock is tracked. Verify startup doesn't hard-depend on optional env vars.

## Post-UAT bugs found by the user (and what to learn)

### Bug: Deep-link URLs (`?node=<iri>`) didn't render the graph

**Symptom:** loading `/explore/tree?node=<iri>&type=class` populated the Details pane (server-side rendered card), but clicking the Entity Graph tab showed the empty state.

**Root cause:** Plan 12's `onTabActivated()` reads from `.tree-node.selected[data-id]` in the DOM. But when the page is hydrated from URL params, the existing server-side path renders the detail card without applying `.selected` to the tree node.

**Fix (Option C of three):** seed `state.lastSelectedIri` from `window.location.search` at module init AND on every `entity:selected` event. `onTabActivated` falls back to this state when DOM has no `.selected` marker. The URL is the canonical source of truth — same convention as the rest of folio-api's shareable entity URLs.

**Why not Option A** (modify `unified_tree.js` to apply `.selected` during URL hydration): puts coupling in the wrong layer. The tree's job is to render the tree; tracking "what entity is the graph centered on" is EntityGraph's concern.

**Why not Option B alone** (just listen to `entity:selected`): the event isn't dispatched during URL hydration, so it doesn't help deep-links.

Commit: `4417211`. CONTEXT.md decision log updated implicitly via this LEARNINGS.md.

### Bug: Single linear ancestor chain (vs. multi-path + seeAlso)

**Symptom:** Maritime Negligence rendered a 5-node single-path chain. Folio-mapper and folio-enrich render multiple ancestor branches converging on the selected entity, with `rdfs:seeAlso` edges as dashed cross-links.

**Discovery:** 832 of 18,323 FOLIO classes have **multiple** parents (multi-inheritance via `sub_class_of`). 1,941 classes carry **rdfs:seeAlso** relationships (a list of IRIs). The v1.1 endpoint walked `sub_class_of[0]` only and ignored `see_also` entirely.

**Fix:** new `_walk_entity_graph` BFS that:
1. Walks ALL parents (multi-inheritance)
2. For each visited node, expands `see_also` targets and walks UP from those too
3. Caps at 50 nodes
4. Returns `nodes[]` + `edges[]` with `relationship: "subClassOf" | "seeAlso"`

Frontend renders `seeAlso` edges with `.graph-edge--seealso` (Tailwind purple-500, dashed `6 4`, opacity 0.85). Multiple ROOT badges supported (Maritime Negligence has 6: Area of Law, Industry and Market, Objectives, Asset Type, Service, Forums and Venues).

**Backward compat:** legacy `ancestors[]` field retained in API response so existing tests still pass and any cached frontend keeps working.

Commit: `a287b16`.

### Bug: Tabs were tiny

**Symptom:** `Details | Entity Graph` tabs auto-sized to label width; the "Full screen" button (visible on Graph tab) ate the rest of the strip.

**Fix:** tab strip container `flex` → `grid grid-cols-2` (deterministic 50/50 regardless of fullscreen button visibility). Fullscreen button moved to absolute positioning at `right-2 top-1/2 -translate-y-1/2`.

Commit: `a287b16` (same as above).

## FOLIO data model gotchas

- **`sub_class_of` is a list, not a scalar** — class can have multiple parents. The Phase 1 endpoint took `[0]` only, which lost ~5% of classes' ancestry.
- **`owl:Thing`** terminates upward walks for classes; **`owl:topObjectProperty`** for properties. Constants in `folio_api/routes/explore.py`.
- **`see_also`** exists on classes; **does NOT** exist on properties. The new walker only traverses see_also for `etype == "class"`.
- **`parent_class_of`** is the canonical child-list attribute on a class. **Don't** scan all `folio.classes` looking for inverse `sub_class_of`; that's O(N²). Existing reverse index for properties is at `app.state.property_children` (built once at startup).
- **`folio.classes`** is iterable (not `folio._classes`). Don't use the underscore-prefixed internal name.
- **`folio[iri]`** returns a class; **`folio.get_property(iri)`** returns a property.

## Codebase patterns worth preserving

- **IRI resolution is 4-strategy** (full IRI, last segment, with/without prefix). Pattern lives in `routes/properties.py:30-57` and `routes/taxonomy.py:1190-1216`. New endpoints should reuse this — never hash IRIs.
- **Endpoint URL convention:** `{iri:path}` (FastAPI path converter), not `{iri_hash}`. The Plan 04 executor noticed and corrected this; future plans should not regress.
- **Static assets via FastAPI's StaticFiles mount** — no build step, no bundler. `entity_graph.js` is plain ES5/ES6 hand-written. Keep it that way unless the user asks for a build pipeline.
- **`config.json` interpolation does NOT happen** — `load_config()` is just `json.load()`. `${OPENAI_API_KEY}` placeholders pass through as literal strings unless caller code substitutes. v1.1 added defensive `${...}` detection in `initialize_folio()`.

## Frontend gotchas

- **ELK doesn't reliably preserve custom edge fields** through `layout()`. Use a sidecar map (`state.edgeRelationships[edgeId]`) keyed by edge id.
- **Selected glow** lives on `.graph-node-selected > div` (the inner styled wrapper), NOT on the outer `.graph-node` element. Don't waste time inspecting the outer element wondering why border is 0px.
- **Browser cache is aggressive** for static assets. After deploying new JS/CSS, hard-reload (`Ctrl+Shift+R`) or version-bust the URLs. The 301 redirect from `/` to `/docs` was particularly persistent in browser caches; switching to 302 fixed future-proofness.
- **`PYTHONUNBUFFERED=1`** is essential for diagnosing container startup failures. Without it, you see only build logs and the healthcheck-failure message — no app stdout, no traceback.

## Test infrastructure

- **`tests/` was empty before Plan 01-01** — pyproject.toml had pytest configured but no scaffolding. Wave 0 created `tests/__init__.py`, `tests/conftest.py` (with `folio` + `client` + `property_children` fixtures), `tests/routes/__init__.py`, and a smoke test.
- **No JS test framework** — manual UAT script is the JS coverage strategy. Don't add jest/vitest without explicit user request.
- **Coverage:** `uv run pytest --cov` is the default config. Backend endpoint at 85% (the 15% gap is defensive error paths).

## Performance

- **Backend `/explore/api/entity-graph/{iri}`**: 3ms locally (in-memory FOLIO traversal, no I/O).
- **Frontend `eg:total` (fetch + ELK layout + render)**: p50 = 33ms across 5 trials (entities depth 0–3) on local; under the 500ms budget by 15× margin. On Railway (network latency adds ~50–100ms), still well under budget.
- **ELK layout time** scales with node count. The 50-node hard cap prevents pathologically dense seeAlso subgraphs from blowing up. If perf matters more later, consider `elk.algorithm: 'force'` or precomputed layouts.
- **The 1.6 MB elk.bundled.js** is lazy-loaded only on tree pages (Plan 03 design). 1-time cost; cached forever after first load. Don't move to non-vendor without solving the CSP issue (cdnjs returns 404; unpkg/jsdelivr aren't in folio-api's CSP).

## Deferred items (NOT done in v1.1)

- Pan/zoom button controls + minimap UI
- Edge labels (`subClassOf`, `seeAlso`) drawn ON the edges (folio-mapper does this)
- Mobile gesture support for full-screen modal
- Server-side caching of `/api/entity-graph/{iri}` (premature; folio-python is in-memory)
- JS unit tests (jest/vitest)
- Add `OPENAI_API_KEY` on Railway so `/search` works on preview
- Vendor Tailwind (currently CDN; fixes production warning)
- Click graph node to re-root WITHOUT changing tree selection (currently click delegates to selectNodeByIri, which is the right behavior per D-15 but might warrant a separate "explore from here" affordance)
