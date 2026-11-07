# Deploy receipt: PR #31 MCP public hosts to PROD

**Date:** 2026-11-07
**Deployed:** `beebde3` (main; PR #31)
**Previous:** `36a0e97`
**Target:** folio.openlegalstandard.org; deploy dir `/home/ubuntu/src/folio-api`

## Rollback point

- **Prior image:** tagged on the box as `folio-api-api:pre-beebde3-20261107`.
- **Config:** Caddyfile and `.env`, plus a host-local diff, in a dated backup dir in the ubuntu home (`prod-backup-20261107T073031Z`).
- **Rollback:** `git checkout 36a0e97`, retag the saved image as `folio-api-api:latest`, then `sudo -n docker compose up -d --no-deps api`.

## Recipe as run

1. **Backup and tag:** as above.
2. **Update:** `git fetch && git merge --ff-only origin/main`. The range touches only `config.json.example`, so the host-local `config.json` (grok `llm` block) is unchanged.
3. **Rebuild:** `sudo -n docker compose build api && sudo -n docker compose up -d --no-deps api`, leaving Caddy untouched. Healthy after 50 s.

## Verification

| Check | Result |
|---|---|
| `POST /mcp` initialize (Host folio.openlegalstandard.org) | was 421 "Invalid Host header"; now **200**, serverInfo "FOLIO Legal Ontology" |
| `tools/list` | 12 tools (search_concepts, get_concept, get_taxonomy_branch, ...) |
| `tools/call search_concepts` "breach of contract" | returns Breach of Contract |
| `POST /mcp` on soli.openlegalstandard.org | 200 |
| `Origin: https://evil.example` | 403 (DNS-rebinding protection still on) |
| `/info/health`, `/explore/tree`, `/search/label` | 200 |
| Container logs, 5 min | 0 errors or tracebacks |
| `llm` block / `rate_limit.enabled` | grok / true, intact |

## Not done

- **DEV preview:** folio-api.dev.openlegalstandard.org still answers 421. It is a Coolify app, and the Coolify API token on the box is rejected (401), so the app could not be redeployed. Damien has a decision filed on minting a new token.
