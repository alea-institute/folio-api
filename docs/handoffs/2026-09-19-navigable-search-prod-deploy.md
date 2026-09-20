---
artifact_contract: "ce-handoff/v1"
created_at: "2026-09-20T00:02:40Z"
title: "Navigable search results shipped to main; PROD deploy pending access"
summary: "FOLIO Explorer tree search navigation (PR #23) is merged and verified; the PROD deploy is blocked on the SSH key and port 22 access, which only the user can supply."
keywords: ["folio-api", "explorer-tree", "search-results", "prod-deploy", "ssh-access", "pr-23"]
cwd: "<repo root>"
resume_focus: "Deploy main (f2ab510) to PROD once the SSH key and port 22 access are confirmed"
repository: "alea-institute/folio-api"
repo_root_sha: "5491c67f97f5ca81f57c31c07a53c683efd64f4d"
branch: "main"
head: "f2ab51031e857b0308b8501ec0b9c2c5eb9c46b8"
---

# Navigable search results: shipped to main, PROD deploy pending

## Objective and user intent
- **User's intent (stated):** add children / siblings / parents navigation to FOLIO Explorer tree search results; then, after the PR landed, "push to PROD" (user asked "can you?", which was taken as authorization to deploy main once access exists).
- **Where it stopped:** the deploy did not run. Two access blockers are the user's to lift (below). Nothing on PROD was changed.

## Work completed (all on GitHub)
- PR #23 merged into `main` at `f2ab510` (merge commit). Feature branch `feat/search-results-navigable-tree` still exists on origin.
- Plan (WHAT and HOW, doc-reviewed): `docs/plans/2026-09-19-1408-feat-search-results-navigable-tree-plan.md`. Read Goal Capsule, Key Decisions, Verification Contract.
- Implementation: `folio_api/routes/taxonomy.py` and `folio_api/routes/properties.py` (search payload gains `child_count` per node and `hidden_root_count` per tree); `folio_api/static/js/unified_tree.js` (lazy chevrons on hits, "+N siblings" native-button rows, details-panel links in search mode, generation tokens against stale async work); `tests/routes/test_tree_search.py` (9 route tests, runtime-picked IRIs).
- Code review receipt: ce-code-review run `20260919-151912-3d455072`, verdict "Ready with fixes", five P2s all applied in commit `82e0d12`. Four advisory items are listed in the PR body under "Unapplied review findings".
- Learning captured: `docs/solutions/developer-experience/2026-09-19-codex-worker-sandbox-cannot-run-pytest-or-app.md` (Codex workers cannot run pytest or boot the app in their sandbox; verify on the host).
- Railway preview: `main` pushed to `origin/feat/v1.1-entity-graph` per the user's standing note.

## Verification performed
- `pytest`: 46 passed at `main` (host run).
- Browser smoke pass (Chrome DevTools) of every acceptance example AE1 to AE11 in the plan, on both trees, light and dark, desktop and 400px, plus the three review-fix repros. Screenshots were deleted after inspection per the user's rule.

## Decisions (user-settled; do not reopen)
- Parents are covered by the existing ancestor chain (no parents control).
- Children expand lazily on the hit; siblings reveal through a "+N siblings" row at the end of the pruned branch (chosen over a pill on the ancestor or a button on the hit); revealed nodes interleave alphabetically; Expand in search mode drills hits/context nodes only, capped at 50 per click; no JavaScript test runner.

## Current state and fragile bits
- `main` = `f2ab510` locally and on origin; working tree clean except a `.planning/STATE.md` modification written by a harness hook (not part of the feature; left uncommitted) and the untracked `.claude/RESUME.md`.
- PROD (folio.openlegalstandard.org) is up and serving the previous release.

## Blockers for the PROD deploy (need the user)
1. The SSH private key for the PROD box is not at the path recorded in Claude's project memory, and no other candidate key exists under the home directory.
2. TCP 22 to the PROD host times out from this machine while HTTPS returns 200, which points at a security-group allowlist or SSH being off. No Tailscale peer or `~/.ssh/config` entry exists for it.
- The deploy recipe itself is known and documented: `docs/plans/2026-07-02-001-chore-deploy-entity-graph-to-prod-plan.md` (back up the host-local `config.json`, reset the deploy dir to `origin/main`, re-apply the Grok LLM block, `./run.sh prod`, allow ~300s cold start). Claude's project memory note "PROD deploy access & topology" carries the host details and was appended with this session's finding.

## Wrong paths already taken
- Asking Codex workers to run pytest, import the routes, or start uvicorn: fails in their sandbox (see the solutions doc). Verify on the host.
- Grepping for `sort\(` missed `sorted(` and produced a false "property children unsorted" plan item; the doc review caught it.
- The Chrome DevTools screenshot tool can only write inside the workspace roots, not `$HOME`.

## Next steps
- One path, once access exists: verify the key and port 22, then run the documented deploy recipe against `main`, confirm `/taxonomy/tree/search?query=deontic` returns `child_count` and the explorer page renders, take a screenshot, and record the rollback point (current HEAD and image on the box) as the receipt.
- Optional, separate: a second `/ce-compound` in a fresh session for the sibling-row placement rule (rows only on non-hit or expanded-hit containers; the merge helper owns the row).
