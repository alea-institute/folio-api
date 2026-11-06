# Deploy receipt — PR #27 Canon toggle to PROD

**Date:** 2026-11-06
**Deployed:** `cc450cb` (merge of PR #27, Canon toggle on the FOLIO tree explorer)
**Previous:** `49b5a29`
**Target:** folio.openlegalstandard.org, deploy dir `/home/ubuntu/src/folio-api`

## Rollback point

- **Prior HEAD:** `49b5a29`
- **Prior image:** tagged on the box as `folio-api-api:pre-cc450cb-20261106`
- **Config/Caddyfile + host-local diff:** dated backup dir in the ubuntu home (`prod-backup-20261106T160042Z`).
- **Rollback:** `git checkout 49b5a29`, retag the saved image as `folio-api-api:latest`, `sudo -n docker compose up -d --no-deps api`.
- **Canon-only off switch:** add `"canon": {"enabled": false}` to the host-local `config.json` and restart the api container; FOLIO is unaffected either way.

## Recipe as run

1. Backup and image tag (above).
2. `git fetch && git merge --ff-only origin/main`. The deployed range does not touch `config.json`, so the host-local `llm` block (grok) and untracked files stayed intact.
3. `sudo -n docker compose build api && sudo -n docker compose up -d --no-deps api` (Caddy untouched).

## Verification

All checks were single requests; no bursts against PROD.

| Check | Result |
|---|---|
| `/info/health` | 200 within the first poll after restart; container `healthy` |
| Canon readiness | toggle present on `/explore/tree` at the first poll; the Canon finished loading in the background without delaying health |
| FOLIO class tree roots (`/taxonomy/tree/data?node_id=%23`) | byte-identical to the pre-deploy sample |
| FOLIO property tree roots | byte-identical to the pre-deploy sample |
| FOLIO tree search `deontic` | same matches, `hidden_root_count` 22, and identical to the previous code's output on the same data when keys are sorted; the raw bytes differ only in JSON key order |
| Canon class roots (`?ontology=canon`) | the seven expected branches, no licensing or deprecated roots |
| Canon search `Sacrament` | 140 Canon IRIs, 0 FOLIO IRIs |
| `/explore/tree`, `/explore/tree?ontology=canon` | 200, 200 |
| `/taxonomy/tree` | 301 (redirect unchanged) |
| Unknown selector (`?ontology=bogus`) | 404 |
| `llm` block | `grok` / `grok-4-fast-non-reasoning`, intact |
| Container logs, first 20 min | 0 errors or tracebacks |

## Memory

| | Host used / available | `folio-api` container |
|---|---|---|
| Before (process up ~39 h, FOLIO only) | 1077 / 2754 MB of 3831 MB | 510 MiB |
| After (fresh process, FOLIO + Canon) | 1027 / 2804 MB of 3831 MB | 468 MiB |

The before/after pair compares a long-running process with a fresh one, so it does not isolate the Canon's cost; research measured about +135 MB resident for the Canon. Host headroom stays above 70% available.
