---
topic: canon-tree-toggle
session: "880440c3-8c9f-5694-8ef5-a7cf37a536cf"
written_at: "2026-11-06T14:08:01.833Z"
head: "6ec3531cfdcdc08b88bbf21ef5d2afe9c21121ab"
worktree: "/home/damienriehl/Coding Projects/folio-api"
branch: "feat/canon-tree-toggle"
---

# Handoff — Canon toggle on the FOLIO tree

## Where it stands

- **Plan:** `docs/plans/2026-11-06-0735-feat-canon-tree-toggle-plan.md` (requirements, technical decisions, five units, verification contract). Doc-reviewed; no open items.
- **Branch:** `feat/canon-tree-toggle`, based on `main` plus the three plan commits.
- **Framing decision:** Cockpit ask `folio-api-2026-11-06-1326-canon-tree-framing`, qid `canon-framing` = plain toggle, no note.
- **Execution:** `ce-work` running. Workers are Codex via `codex-run.sh`; the orchestrator runs pytest and browser UAT on the host and makes the canonical commits.
  - Wave 1 (fixture, registry, background Canon loader, shared selector/resolver) dispatched.
  - Wave 2 next: tree data routes in parallel with page, templates, and client script.
  - Then: full suite, Playwright UAT, code review, PR, merge, PROD deploy with memory receipt.

## Key facts a cold reader needs

- Baseline suite on `main`: 88 passed.
- The Canon shares 14,407 bare IDs with FOLIO; every tree lookup must stay inside the selected ontology.
- The Canon declares four of its seven visible top-level branches with no parent; root detection must accept "no parent or only owl:Thing".
- Damien directed that the Canon load in the background after FOLIO, in stages, so it never slows FOLIO.

## Resume

Resume `ce-work` on the plan path above from the branch tip; progress lives in the branch's commits.
