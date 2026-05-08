---
purpose: Orient a fresh agent after /clear or new-session. Read this FIRST.
last_updated: 2026-05-08
status: phase-1-complete-pending-milestone-close
---

# CONTINUATION — Read this first

You are continuing work on **folio-api** (FastAPI + Jinja2 + jQuery + vanilla JS + Tailwind CDN). Milestone **v1.1 (Entity Graph)** Phase 1 is **functionally complete and deployed to a Railway preview**. The user is remote and tested via the public URL.

## Where to read for full context (in order)

1. **This file** — overview
2. `.planning/STATE.md` — current GSD position
3. `.planning/PROJECT.md` — Core Value, Active/Validated requirements, Key Decisions
4. `.planning/phases/01-entity-graph/CONTEXT.md` — 30 locked design decisions (D-01..D-30)
5. `.planning/phases/01-entity-graph/01-UI-SPEC.md` — 6-pillar design contract (APPROVED)
6. `.planning/phases/01-entity-graph/01-RESEARCH.md` — donor mechanics, codebase patterns, validation architecture
7. `.planning/phases/01-entity-graph/LEARNINGS.md` — gotchas discovered during execution + deploy
8. `.planning/phases/01-entity-graph/01-UAT.md` — 17/18 PASS verification

## Current state (live URLs)

| Resource | Where |
|---|---|
| **Live preview** | https://folio-api-preview-production.up.railway.app (302 → /explore/tree) |
| **GitHub branch** | https://github.com/alea-institute/folio-api/tree/feat/v1.1-entity-graph |
| **Railway project** | https://railway.com/project/86aee6fc-52fe-4c1f-b21c-83dc66652775 |
| **Local server** | `uv run uvicorn folio_api.api:app --host 127.0.0.1 --port 9596` (config in `.claude/bootup.json`) |
| **Latest commit** | `a287b16` fix(entity-graph): multi-path ancestry + seeAlso, 50/50 tabs |

## What's done

### Phase 1 — Entity Graph (15 plans across 5 waves) ✓

All plans executed via parallel `gsd-executor` agents in worktrees, merged to `main` (then pushed to `feat/v1.1-entity-graph` on origin):

- **Wave 0**: pytest scaffold · vendor `elk.bundled.js` (1.6 MB, SHA-384 pinned) · `entity_graph.js` skeleton
- **Wave 1**: `GET /explore/api/entity-graph/{iri:path}` endpoint + 10 TDD tests · `Details | Entity Graph` tab strip + `entity:selected` event · UI state renderers (showEmpty/Skeleton/Error) + Heroicons inline SVG
- **Wave 2**: `buildELKGraph` + `runLayout` · `renderGraph` + `buildEdgePath` (verbatim cubic-bezier from folio-enrich:8976–8990) · visual styling (icons, glow, ROOT badge)
- **Wave 3**: pan/zoom + auto-fit · `+N Children` button + hover badge + real `expand()` · lazy-fetch lifecycle + click-to-tree-select · full-screen DOM-swap modal
- **Wave 4**: `performance.mark` instrumentation · accessibility audit (added `role="img"` + aria-label on graph SVG)

### Post-execution work (NOT in any GSD plan, all on the branch)

These are real changes the user requested after Phase 1's UAT passed. They live as separate commits on `feat/v1.1-entity-graph`:

| Commit | What |
|---|---|
| `680ed6e` | `railway.json` + Dockerfile config baking + `${...}` placeholder fix |
| `713ebc7` | Track `uv.lock` so Docker/Railway builds resolve `--frozen` |
| `af0075e` | Extend Railway healthcheck timeout to 300s for FOLIO cold start |
| `0216e90` | `PYTHONUNBUFFERED=1` so container logs surface stdout |
| `fc35f48` | Make app boot without `OPENAI_API_KEY` (entity graph has no LLM dep) |
| `4417211` | Deep-link URLs render the graph on tab activation (state.lastSelectedIri) |
| `4deb673` | Default `/` to `/explore/tree` (was `/docs`); 302 (was 301) |
| `a287b16` | Multi-path ancestry + seeAlso edges + 50/50 tabs |

The user accepted **5 Railway deploy attempts** before deploy #5 succeeded. See `LEARNINGS.md` for what each one fixed.

### UAT (chrome-devtools MCP, 17/18 PASS)

User auto-confirmed all 17 verifiable items via chrome-devtools (1 was N/A — skeleton too fast to capture on local). Verdict: **APPROVED for milestone close**.

## What's NOT done

1. **PR not opened** — `gh pr create --repo alea-institute/folio-api --base main --head feat/v1.1-entity-graph`
2. **Milestone v1.1 not closed** — `/gsd-complete-milestone` would tag v1.1, archive `phases/01-entity-graph/` to `archive/v1.1/`, update MILESTONES.md, reset STATE.md for next milestone, and move GRAPH-01..GRAPH-20 from PROJECT.md Active → Validated
3. **Open question with the user**: open the PR now, or hold off?

## What might come next from the user

User has been iterating bug-by-bug. Plausible next requests:
- Open the PR (one command: `gh pr create ...`)
- Close the milestone (`/gsd-complete-milestone`)
- More UI polish (the entity graph is now much richer; might surface visual issues at scale)
- Add `OPENAI_API_KEY` to Railway so /search works on the preview
- Vendor Tailwind to fix the `cdn.tailwindcss.com` console warning
- Sketch a v1.2 milestone (+N expand on ancestors? Click-to-re-root? Edge labels?)

## Operating instructions for this project

- **Auto-commit is enabled** — see `~/.claude/projects/-home-damienriehl-Coding-Projects-folio-api/memory/feedback_auto_commit.md`. The user opted in; commit work without asking, but still NEVER `git push`, `git reset --hard`, `--no-verify`, etc. without per-action approval.
- **Push protocol**: feature branches go to `origin/feat/<slug>`. Local `main` is dev — push commits there to `origin/feat/v1.1-entity-graph` (NOT origin/main).
- **Visual verification = chrome-devtools MCP only.** No headless Chromium fallback. Screenshots go to `/tmp/`.
- **Dev server port = 9596** (deterministic per CLAUDE.md formula: `8700 + (sum(ord(c) for c in 'folio-api') % 1300)`).
- **Railway deploy** = `railway up --detach`. CLI is logged in as Damien Riehl. Project ID is in the table above.
- **GSD slash commands** are the default workflow (per global CLAUDE.md). Use `/gsd-progress` to orient, `/gsd-resume-work` to pick up.

## Common pitfalls (don't repeat these)

- **Don't echo `OPENAI_API_KEY` value in any diagnostic command** — leaked into chat once already; use `bool(os.getenv(...))`. (User has rotated the key.)
- **Don't pass `model="inherit"` to Task** — omit the parameter to inherit. Same for any GSD subagent spawn.
- **Don't run multiple `Task(isolation="worktree")` in one message** — `.git/config.lock` contention. Use `run_in_background: true` and dispatch one Task per message.
- **Don't bypass the user's CLAUDE.md preference for chrome-devtools MCP** — never fall back to headless chromium CLI.

## Session-resume command

When a fresh session opens:

```
/gsd-progress
```

That'll read STATE.md, find we're at "Phase 1 complete, awaiting milestone close", and surface the right next step.
