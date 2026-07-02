---
title: Ship Entity Graph (v1.1) from DEV to PROD
type: chore
status: active
date: 2026-07-02
---

# Ship Entity Graph (v1.1) from DEV → PROD

## Overview

The v1.1 **Entity Graph** milestone (78 commits, 15 plans across 5 waves + 8 post-UAT
commits) is live on the **DEV / Railway preview** but has **not reached PROD**
(`folio.openlegalstandard.org`). This plan verifies exactly what is un-shipped, confirms
DEV is current (it is), and lays out a safe path to promote everything to PROD **without
clobbering PROD's live server-local config drift** (Grok LLM, `soli.` subdomain, `XAI_API_KEY`,
rate-limiting).

**Bottom line up front:** DEV needs nothing — it is already at local `main` HEAD (`0b72716`).
The real work is a governed promotion of local `main` to PROD.

## Status Snapshot (verified 2026-07-02)

### Deployment topology

| Env | Target | Deploys from | Current SHA | State |
|---|---|---|---|---|
| **DEV** | `folio-api-preview-production.up.railway.app` (Railway, project `86aee6fc…`) | `origin/feat/v1.1-entity-graph` (alea-institute) | `0b72716` | ✅ **Current** — equals local `main` HEAD |
| **PROD** | `folio.openlegalstandard.org` (+ `soli.…`) — AWS EC2, us-east-2, Docker + Caddy | unknown remote/branch (recon needed) | `1fd309b` + uncommitted drift (snapshot 2026-05-19) | ❌ **Missing entire Entity Graph** |
| upstream `main` | `alea-institute/folio-api` `main` | — | `9059e73` | 78 commits behind local `main`; no open PR |

### Key facts established

- **Local `main` is a strict superset of PROD's committed code.** PROD-HEAD's parent
  `508e661` is an ancestor of local `main` (90 commits after it, 0 behind). The
  connections-route ordering fix that is PROD's tip commit `1fd309b` is **already present**
  in local `main` (`folio_api/api.py:302–303` registers `root.router` last, after
  `connections.router`). So promoting local `main` → PROD **regresses nothing** and adds the
  entire Entity Graph.
- **DEV requires no push.** `origin/feat/v1.1-entity-graph == local main == 0b72716`
  (confirmed post-`git fetch`). Working tree is clean (only untracked `.planning/` dirs).
- **PROD has uncommitted server-local drift** (captured in
  `.planning/prod-snapshot-2026-05-19/prod-uncommitted-tracked.diff`) that must be preserved:
  - `config.json`: LLM switched `openai/gpt-5.4` → **`grok / grok-4-fast-non-reasoning`**
  - `docker-compose.yml`: adds **`XAI_API_KEY`** env passthrough
  - `docker/Caddyfile`: adds **`soli.openlegalstandard.org`** reverse-proxy block + HSTS/XSS headers + rate-limiting on `/search/* /taxonomy/*`
  - stray 0-byte `folio_api/x` (harmless; ignore)
- **Entity Graph has zero LLM dependency** (LEARNINGS bug #4) — it renders on PROD regardless
  of which LLM key is set, so the graph ships safely even with PROD on Grok.

## Problem Statement / Motivation

The user built the Entity Graph, verified it on the Railway preview (17/18 UAT PASS), but the
public production site never received it. Two things block a clean ship:

1. **No governance path taken** — the feature branch was never PR'd or merged to
   `alea-institute/main`, so upstream `main` is 78 commits stale and PROD has no obvious ref to
   pull from.
2. **PROD config drift** — the production box carries uncommitted config (Grok, `soli`
   subdomain, rate-limiting). A naive `git pull`/`checkout` on the box would **silently destroy
   live production configuration**. This is the single biggest risk in this plan.

## Locked Decisions (2026-07-02)

- **Promotion path:** PR → merge → deploy. **PR #18 is OPEN**
  (`feat/v1.1-entity-graph → alea-institute/main`): https://github.com/alea-institute/folio-api/pull/18
- **PROD access — RESOLVED.** Prod is `ubuntu@13.59.153.110` (AWS EC2 us-east-2, hostname
  `ip-172-31-33-183` — matches the snapshot author), key `~/Coding Projects/soli-api.pem`.
  Read-only Phase 0 recon completed 2026-07-02.

## PROD Recon Findings (verified live 2026-07-02)

- **Live deploy dir:** `/home/ubuntu/src/folio-api` (docker-compose working dir for the healthy
  `folio-api` container + `folio-caddy`). Other repos on the box (`~/soli-api`, `~/src/soli-api`,
  `~/src/folio-mcp`) are unrelated to what serves `folio.openlegalstandard.org`.
- **Running container image built `2026-03-16`** — PROD has not been rebuilt since March. It is
  serving the pre-entity-graph app.
- **Git state:** remote `alea-institute/folio-api`, branch `main`, HEAD `1fd309b`
  (= `508e661` + the connections-route fix, 1 commit, **pushed nowhere**). That fix is **already
  present in local `main`/PR #18**, so `1fd309b` is redundant and safe to discard.
- **Drift is LIVE via read-only volume mounts** (survives image rebuild; captured to
  `.planning/prod-snapshot-2026-07-02/`):
  - `config.json` → **Grok** (`grok-4-fast-non-reasoning`), mounted `:/app/config.json:ro`
  - `docker/Caddyfile` → **`soli.` subdomain** + HSTS/XSS + rate-limiting, mounted `:/etc/caddy/Caddyfile:ro`
  - `docker-compose.yml` → adds `XAI_API_KEY` passthrough
  - `docker/Dockerfile` → drops `&& uv venv` from the `uv sync` line (prod-local build fix)
  - untracked prod-only: `analytics.py` (560-line standalone traffic tool, **not wired into the app** — backed up), `.env~`, `logs/`, `folio_api/x`
- **Deploy hazard confirmed:** those 4 modified tracked files will block/conflict a `git pull` or
  `git merge`. Must be stashed/preserved and reconciled (Phase 2/3).

## Proposed Solution (recommended path)

Promote local `main` to PROD through the canonical review gate, preserving config drift:

```
local main (0b72716)
   └─(1) PR: feat/v1.1-entity-graph → alea-institute/main
        └─(2) merge → origin/main advances to 0b72716-equiv
             └─(3) on PROD box: preserve drift → pull → rebuild → verify
```

### Phase 0 — PROD reconnaissance (blocking; read-only)

The 2026-05-19 snapshot proves drift but not the *pipeline*. Before touching PROD, establish:

- [ ] SSH access to the EC2 box (us-east-2, `ip-172-31-33-183` per patch author) — confirm reachable
- [ ] `git remote -v` and current branch on the box — **how does PROD receive code?**
  (pull from `alea-institute/main`? a fork? manual `scp`? image registry?)
- [ ] `git status` + `git stash list` on the box — re-confirm the 3 drifted files are still
  uncommitted and unchanged since the 2026-05-19 snapshot
- [ ] Whether PROD's tip `1fd309b` was ever pushed anywhere (it is in **no** known remote today)
- [ ] Confirm `run.sh` / `docker compose up -d --build` is still the deploy command in use

> If Phase 0 reveals PROD pulls from a remote that doesn't yet have the Entity Graph, Phase 1
> (PR + merge) is the prerequisite. If PROD is deployed by manual copy, Phase 1 is still
> recommended for provenance but is not strictly required to ship.

### Phase 1 — Promote to upstream `main` (governance)

- [ ] Open PR: `gh pr create --repo alea-institute/folio-api --base main --head feat/v1.1-entity-graph`
      (branch already at `0b72716`; body from `.planning/` milestone docs)
- [ ] Merge PR → `origin/main` fast-forwards to the Entity Graph HEAD
      (clean FF: `9059e73` is a direct ancestor of `0b72716`, 78 commits, no divergence)
- [ ] (optional) `/gsd-complete-milestone` to tag `v1.1` and archive the phase

### Phase 2 — Capture PROD config drift as real config (de-risk)

Decide per drift item (see Open Decisions): commit into the repo vs. keep server-local.
Recommended:

- [ ] Move LLM provider selection to **env/`.env`** (`FOLIO_LLM_TYPE`, model) so PROD's Grok
      choice is not a tracked-file edit that a pull can clobber — or commit a
      `config.prod.json` the box selects explicitly
- [ ] Commit the **`soli.openlegalstandard.org`** Caddy block + rate-limiting to
      `docker/Caddyfile` (this is real prod infra, not throwaway) — behind a review
- [ ] Ensure `XAI_API_KEY` passthrough exists in `docker-compose.yml` (committed), value
      supplied via the box's `.env` (never committed)

### Phase 3 — Deploy to PROD (careful, reversible)

Concrete, given the recon (all on `13.59.153.110:/home/ubuntu/src/folio-api`):

- [ ] Back up drift + prod-only files (already captured locally 2026-07-02; re-verify unchanged):
      `config.json`, `docker/Caddyfile`, `docker-compose.yml`, `docker/Dockerfile`, `analytics.py`
- [ ] Tag current image for rollback: `sudo docker tag folio-api-api folio-api-api:pre-v1.1`
- [ ] `git stash` the 4 tracked mods (or `git branch prod-drift-2026-07-02` to preserve them)
- [ ] `git fetch origin && git reset --hard origin/main` (discards redundant `1fd309b`; brings
      the entity graph). Needs explicit approval — `reset --hard` on prod.
- [ ] Restore live config to the working tree (mounted files must be present):
      re-apply `config.json` (Grok) + `docker/Caddyfile` (soli) + `docker-compose.yml` (XAI) +
      reconcile `docker/Dockerfile` against the branch's new Dockerfile
- [ ] `docker compose up -d --build` (via `./run.sh prod`)
- [ ] Watch cold-start: FOLIO downloads ~80 MB OWL + parses 18,323 classes — allow up to
      ~300 s before healthcheck panic (same cold-start that forced Railway's 300 s timeout)
- [ ] **Rollback if needed:** `git reset --hard 1fd309b` + restore drift +
      `docker compose up -d` with `folio-api-api:pre-v1.1`

> **Better long-term (Phase 2 done right):** land the `soli` Caddy block, `XAI_API_KEY` compose
> passthrough, and Dockerfile fix into the repo via a follow-up PR so prod's tree is clean and
> future deploys are a plain `git pull`. Keep `config.json` (Grok + key implications) host-local
> and gitignored.

### Phase 4 — Verify PROD live

- [ ] `https://folio.openlegalstandard.org/info/health` → 200
- [ ] `/` → 302 → `/explore/tree`
- [ ] Entity Graph tab renders on a known node (e.g. Maritime Negligence → **33 nodes /
      46 edges / 6 ROOT badges** per DEV UAT baseline) — verify via **chrome-devtools MCP**
- [ ] `/search` still works on Grok; `/connections` reachable (catch-all ordering)
- [ ] `soli.` subdomain still serves; rate-limiting intact

## System-Wide Impact

- **Interaction graph:** router registration order matters — `root.router`'s `/{iri}` catch-all
  must stay last (already true in local `main`). Verify no PROD-only route depends on the old
  order.
- **Error propagation:** startup must not hard-require a missing key. Local `main` already boots
  without `OPENAI_API_KEY` (commit `fc35f48`); PROD uses `XAI_API_KEY` for Grok — confirm the
  key-resolution path is provider-agnostic at startup.
- **State lifecycle risk:** the **only** irreversible risk is losing PROD's uncommitted config
  during pull/checkout. Phase 2 + the Phase 3 stash step neutralize it. Everything else is a
  container rebuild (reversible by redeploying the prior image/commit).
- **API surface parity:** DEV (Railway, single service) vs PROD (Docker+Caddy, `folio.` +
  `soli.` subdomains, rate-limiting) — PROD has infra DEV lacks; do not assume parity.

## Acceptance Criteria

- [ ] Confirmed how PROD receives code (Phase 0)
- [ ] Entity Graph merged to `alea-institute/main` via reviewed PR
- [ ] PROD's Grok / `soli` / `XAI` / rate-limit config preserved (verified post-deploy)
- [ ] `folio.openlegalstandard.org` serves the Entity Graph tab, verified via chrome-devtools MCP
- [ ] `/search`, `/connections`, `soli.` subdomain all still functional on PROD
- [ ] Documented rollback: redeploy prior commit/image

## Dependencies & Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Pull clobbers PROD's uncommitted Grok/`soli`/rate-limit config | **High** | Phase 2 commits it properly; Phase 3 stashes before pull |
| PROD deploy pipeline unknown / no SSH | **High (blocking)** | Phase 0 recon; may need user to run `!`-prefixed SSH commands |
| FOLIO cold-start exceeds healthcheck window | Medium | 300 s tolerance; `PYTHONUNBUFFERED=1` for visible logs |
| PROD tip `1fd309b` exists in no remote — provenance gap | Low | Already superseded by local `main`; document and move on |
| Merging 78 commits to upstream draws review scope-creep | Low | Milestone docs in `.planning/` justify the batch |

## Sources & References

- `.planning/STATE.md` — milestone `v1.1`, status `deployed-pending-pr-and-milestone-close`
- `.planning/CONTINUATION.md` — full context, live URLs, push protocol
- `.planning/prod-snapshot-2026-05-19/` — PROD drift evidence (`prod-uncommitted-tracked.diff`, `prod-git-log.txt`, connections patch `1fd309b`)
- `.planning/phases/01-entity-graph/LEARNINGS.md` — 5 Railway deploy attempts, cold-start + key gotchas
- `folio_api/api.py:296–303` — router registration order (catch-all last)
- `run.sh` / `docker-compose.yml` / `docker/Caddyfile` — PROD deploy mechanism
- Verified git facts: local `main` `0b72716` ⊇ PROD; `origin/feat/v1.1-entity-graph == main`; `origin/main` `9059e73` (78 behind); no open PRs on alea-institute
