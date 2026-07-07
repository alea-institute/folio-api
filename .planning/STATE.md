---
gsd_state_version: 1.0
milestone: none
milestone_name: null
status: milestone-closed
stopped_at: v1.1 (Entity Graph) shipped to production 2026-07-03; milestone closed 2026-07-07
last_updated: "2026-07-07T12:30:00Z"
last_activity: 2026-07-07 — Verified static cache-busting (PR #19) live on prod + dev (versioned ?v= URLs + Cache-Control: public, max-age=3600, must-revalidate). Test suite green (16 passed). Closed v1.1 milestone — requirements moved Active→Validated, phase archived to archive/v1.1/, tag v1.1 created.
preview_url: https://folio-api.dev.openlegalstandard.org
prod_url: https://folio.openlegalstandard.org
github_branch: main (alea-institute/folio-api)
must_read_first: .planning/PROJECT.md
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: `.planning/PROJECT.md`

**Core value:** The taxonomy must be browsable, searchable, and visually clear — users come here to find and understand legal concepts in their hierarchy.
**Current focus:** None — between milestones. v1.1 (Entity Graph) shipped to production 2026-07-03; milestone closed.

## Current Position

No active milestone. v1.0 and v1.1 both shipped to production and closed (see `MILESTONES.md`).

Latest: v1.1 Entity Graph (PRs #18, #19) live at https://folio.openlegalstandard.org.

## Suggested next steps

1. **Define next milestone** when scope is chosen. Part II improvement backlog for folio-api (see portfolio plan II.5): semantic search (pgvector), API keys + usage analytics, SPARQL endpoint, OpenAPI polish + versioned dataset downloads.
2. **Deploy hygiene:** the PR #19 drift-folding is partial — `config.json` (Grok LLM) and `docker/Dockerfile` drift still live only on the prod box. Folding those into the repo (behind env/config) would make prod deploys fully drift-free.
3. **Security note (open):** prod Caddy rate-limiting was dropped in PR #19 (the `rate_limit` directive needs a Caddy plugin absent from `caddy:latest`). Re-introducing rate limiting via a Caddy build with the plugin, or app-level limiting, is a follow-up — logged to the QA queue 2026-07-07.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| UX | Pan/zoom button controls + minimap | Future milestone | v1.1 planning |
| UX | Edge labels (`subClassOf`, `sub_property_of`) | Future milestone | v1.1 planning |
| UX | Mobile gesture support for full-screen | Future milestone | v1.1 planning |
| Perf | Server-side caching of `/api/entity-graph/*` | Future milestone | v1.1 planning |
| Ops | Fold `config.json` (Grok) + `Dockerfile` prod drift into repo | Future milestone | v1.1 close |
| Security | Re-introduce prod rate limiting (Caddy plugin or app-level) | QA queue | v1.1 close |

## Session Continuity

Last session: 2026-07-07T12:30:00Z
Stopped at: v1.1 milestone closed; static cache-busting verified live on prod + dev.
