# Deploy receipt — PR #22 MCP mount fix to PROD

**Date:** 2026-11-04
**Deployed:** `49b5a29` (main; PR #22 MCP mount fix `631e9d1` plus CI/test/docs commits)
**Previous:** `fccd305`
**Target:** folio.openlegalstandard.org, deploy dir `/home/ubuntu/src/folio-api`

## Access

Port 22 now accepts only the static Hetzner DEV IP (Mike, 2026-11-04). The `folio-prod`
SSH alias jumps through `hetzner-dev`; a rotating home IP no longer matters.

## Rollback point

- **Prior HEAD:** `fccd305`
- **Prior image:** tagged on the box as `folio-api-api:pre-49b5a29-20261104` (`e9316a727b28`)
- **Config/Caddyfile/.env + host-local diff:** dated backup dir in the ubuntu home
  (`prod-backup-20261105T005759Z`).
- **Rollback:** `git checkout fccd305`, retag the saved image as `folio-api-api:latest`,
  `sudo -n docker compose up -d --no-deps api`.

## Recipe as run

1. Backup and image tag (above).
2. `git fetch && git merge --ff-only origin/main`. This replaces the earlier `git reset --hard`
   step: the deployed range does not touch `config.json`, so the fast-forward keeps the
   host-local `llm` block (grok) and the untracked files intact with no restore step.
3. `sudo -n docker compose build api && sudo -n docker compose up -d --no-deps api`
   (Caddy untouched). Healthy after about 2 minutes.

## Verification

| Check | Result |
|---|---|
| `/info/health` | 200 |
| `/explore/tree` | 200 |
| Taxonomy search `deontic` | `tree.hidden_root_count` 22 (matches 2026-09-20) |
| `/search/label` | 200 |
| `llm` block | `grok` / `grok-4-fast-non-reasoning`, intact |
| `rate_limit.enabled` | true |
| Container logs, 10 min | no errors or tracebacks |
| `POST /mcp` | was 405, now **421 "Invalid Host header"** |

## Follow-up: MCP still unreachable publicly

The mount fix works: requests now reach the MCP app. The MCP SDK's DNS-rebinding guard
then rejects the public Host header (`transport_security.py: Invalid Host header`). Fix in
`folio-mcp`: pass `TransportSecuritySettings` allowing `folio.openlegalstandard.org`
(or disable rebinding protection behind Caddy). Not a regression: MCP never answered on
PROD before this deploy either.
