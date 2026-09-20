# Deploy receipt — PR #23 navigable search results to PROD

**Date:** 2026-09-20
**Deployed:** `fccd305` (PR #23 merged as `f2ab510`, plus docs commits)
**Previous:** `864d1dc` (PR #21, app-level rate limiting)
**Target:** folio.openlegalstandard.org — EC2 us-east-2, deploy dir `/home/ubuntu/src/folio-api`

## Rollback point

- **Prior HEAD:** `864d1dc32f220203aef2a1bf999f54bd682ec1f1`
- **Prior image:** tagged on the box as `folio-api-api:pre-pr23-20260920` (id `3a868207e2bf`)
- **Config/Caddyfile/.env backup:** `/home/ubuntu/prod-backup-20260920T133213Z/` (machine-local)
- **Rollback:** `git reset --hard 864d1dc`, restore `config.json` from the backup dir,
  `sudo ./run.sh prod`. Or retag the saved image if a rebuild is undesirable.

## Recipe as actually run

1. `git fetch origin && git reset --hard origin/main`
2. Restore the host-local `config.json` from the backup (only real drift is the
   `llm` block: `grok` / `grok-4-fast-non-reasoning`). Verified unchanged upstream
   in the deployed range, so restoring the whole file is lossless.
3. `sudo -n ./run.sh prod` → `docker compose up -d --build`
4. Cold start ~2 min this time (ontology parse), not the ~300s the older plan assumed.

## Corrections to the documented recipe

- **Docker needs `sudo`.** The `ubuntu` user is in `sudo` but NOT in `docker`, so a bare
  `./run.sh prod` fails with a docker.sock permission error. Passwordless sudo works.
- **Drift is wider than `config.json` alone,** but harmlessly so: untracked `.env~`,
  `analytics.py`, `folio_api/x` (empty), and `logs/` predate this work and survive
  `git reset --hard` because reset does not remove untracked files.
- **The `?v=` cache-bust token is the newest static-asset mtime,** not a build stamp.
  It does not advance when a release touches no static file, so it is not a reliable
  indicator of the deployed commit. It DID advance here (1783043069 → 1789911200)
  because PR #23 modifies `unified_tree.js`.

## Verification

| Check | Result |
|---|---|
| `tree.hidden_root_count` in taxonomy search | 22 |
| `child_count` on search tree nodes | present, 5 nodes (13/9/7/6/5) |
| Properties tree search | 200, serving |
| `/explore/tree` | HTTP 200 |
| Containers | `folio-api` healthy, `folio-caddy` up |
| Grok `llm` block after reset | intact |
| `rate_limit.enabled` | true |
| Browser check, query "deontic" | 3 matches; sibling rows +12/+5/+4/+22/+77; details panel Parent(s) + Children 9 with links |
| Console errors/warnings | none |

## Note

An earlier probe in this session fired ~12 rapid search requests and tripped the
app-level rate limiter, which briefly blocked this machine's IP. That was the limiter
working as designed, not an outage. Do not load-test PROD to confirm a feature exists.
