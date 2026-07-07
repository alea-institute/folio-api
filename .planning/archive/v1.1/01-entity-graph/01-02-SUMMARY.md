---
phase: 01-entity-graph
plan: 02
subsystem: ui
tags: [vendor, elkjs, scaffold, supply-chain, sri]

# Dependency graph
requires:
  - phase: 01-entity-graph
    provides: "RESEARCH.md SHA-384 pin and unpkg source URL probed 2026-05-05"
provides:
  - "Vendored elkjs 0.11.1 layered-graph layout engine (folio_api/static/js/vendor/elk.bundled.js)"
  - "SHA-384 pin file for supply-chain audit (folio_api/static/js/vendor/elk.bundled.js.sha384)"
  - "Static asset served under CSP 'self' — no base.html CSP relaxation needed"
affects: [01-entity-graph-plan-03, 01-entity-graph-plan-07]

# Tech tracking
tech-stack:
  added:
    - "elkjs 0.11.1 (Eclipse Layout Kernel browser bundle, UMD, EPL 2.0 / EDL 1.0)"
  patterns:
    - "Vendor-with-SHA-384-pin: download once, verify integrity, commit alongside .sha384 sibling for drift detection"

key-files:
  created:
    - "folio_api/static/js/vendor/elk.bundled.js"
    - "folio_api/static/js/vendor/elk.bundled.js.sha384"
  modified: []

key-decisions:
  - "Vendor elkjs (not CDN) — cdnjs URL in UI-SPEC returns HTTP 404 and folio-api CSP script-src does not permit unpkg/jsdelivr; vendoring is cheaper than a CSP edit"
  - "Pin SHA-384 in a sibling .sha384 file with shasum-compatible first line plus comments for provenance"

patterns-established:
  - "Static vendor pattern: download upstream → verify SHA-384 against research-pinned hash → fail loudly on mismatch → record source URL + verify command in sibling pin file"

requirements-completed: []

# Metrics
duration: 1min
completed: 2026-05-06
---

# Phase 01 Plan 02: Vendor elkjs Summary

**elkjs 0.11.1 vendored at folio_api/static/js/vendor/elk.bundled.js (1,607,470 bytes) with SHA-384 pinned in a sibling .sha384 file — unblocks Plans 03 and 07 without touching base.html CSP**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-05-06T12:54:59Z
- **Completed:** 2026-05-06T12:55:59Z
- **Tasks:** 1 / 1
- **Files modified:** 2 (both created)

## Accomplishments
- Downloaded `elk.bundled.js` from `https://unpkg.com/elkjs@0.11.1/lib/elk.bundled.js`
- Verified actual SHA-384 matches research-pinned hash exactly: `k7OFwtsMfFyYU75zZhPkC8VRASnGrW1pxavUnozOiO2B5M5gv6PYGOkEYZTrVtvo`
- Verified actual byte size matches research expectation exactly: 1,607,470 bytes
- Confirmed file contains the `ELK` UMD export identifier (32 occurrences)
- Wrote `elk.bundled.js.sha384` with shasum-compatible first line plus provenance comments (source URL, vendored date, size, verify command, license)
- Confirmed `folio_api/templates/jinja2/layouts/base.html` is **unchanged** — no CSP relaxation, no script-src edit

## Task Commits

1. **Task 1: Download and SHA-384-verify elk.bundled.js into static/js/vendor/** — `f6b323a` (chore)

## Files Created/Modified
- `folio_api/static/js/vendor/elk.bundled.js` — Vendored elkjs 0.11.1 UMD bundle (created, 1,607,470 bytes)
- `folio_api/static/js/vendor/elk.bundled.js.sha384` — SHA-384 pin + provenance metadata for supply-chain audit (created)

## Decisions Made
- **Vendor instead of CDN.** UI-SPEC originally pointed at `cdnjs.cloudflare.com/ajax/libs/elkjs/0.11.1/elk.bundled.min.js` which returns HTTP 404 (RESEARCH.md Pitfall 1, verified 2026-05-05). The `script-src` directive in `base.html` does not whitelist unpkg or jsdelivr, so any CDN workaround would also require a CSP edit. CONTEXT.md "Claude's Discretion" explicitly authorizes vendoring when CDN reliability is in question. Vendoring is the cheaper, safer fix — zero new dependencies, zero CSP changes.
- **Enrich the .sha384 file with comments.** The plan's acceptance criteria specify the canonical first line `sha384-<hash>  elk.bundled.js` (shasum-compatible). To also satisfy the prompt's audit-trail requirement ("Document the source URL + verification command in a `.sha384` file"), comment lines (prefixed with `#`) are appended after the first line. `shasum -c` ignores comment lines, so the canonical format is preserved while the audit trail is captured in-band.

## Deviations from Plan

None — plan executed exactly as written. SHA-384 and byte size matched research expectations on the first download attempt.

## Issues Encountered

**Worktree branch was behind main.** When the agent started, the worktree branch was anchored at an older `main` (`9059e73`) that pre-dated the planning commits (`e746cbb`, `7f700fe`). The plan file `.planning/phases/01-entity-graph/01-02-PLAN.md` and `RESEARCH.md` did not exist in the worktree filesystem. Resolved by `git rebase 7f700fef8d08100c7a45aeff0ea2611b9e7547c0` (current main HEAD with planning files committed). After the rebase, all planning context was available and Task 1 proceeded normally. This is a worktree-setup concern, not a plan-execution concern — flagged here for the orchestrator's awareness in case future wave-0 worktrees were spawned similarly stale.

## User Setup Required

None — no external service configuration required. The vendored asset is served as a normal static file under the existing CSP `'self'` allowance.

## Next Phase Readiness

- **Plan 03** (entity_graph.js loader) can now reference `/static/js/vendor/elk.bundled.js` from a runtime `<script>` injection without 404 and without CSP violation.
- **Plan 07** (`new ELK()` layout call) can now construct the global once the bundle is loaded by Plan 03.
- **Drift detection:** Future maintainers can re-verify the bundle at any time with `openssl dgst -sha384 -binary folio_api/static/js/vendor/elk.bundled.js | openssl base64 -A` and compare against the first line of `elk.bundled.js.sha384`.

## Self-Check: PASSED

- `folio_api/static/js/vendor/elk.bundled.js` — FOUND (1,607,470 bytes)
- `folio_api/static/js/vendor/elk.bundled.js.sha384` — FOUND
- SHA-384 verification — `k7OFwtsMfFyYU75zZhPkC8VRASnGrW1pxavUnozOiO2B5M5gv6PYGOkEYZTrVtvo` matches exactly
- `base.html` — UNCHANGED (`git diff --exit-code` returns 0)
- Commit `f6b323a` — FOUND in `git log`

---
*Phase: 01-entity-graph*
*Plan: 02*
*Completed: 2026-05-06*
