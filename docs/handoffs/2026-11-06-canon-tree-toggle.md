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
  - Wave 1 committed (`25d6399`): Canon test snapshot, ontology registry, background Canon loader on a dedicated low-priority thread, shared selector and resolvers. Suite: 115 passed.
  - Wave 2 running in parallel worktrees: tree data routes (`wip/canon-routes`) and page, templates, and client script (`wip/canon-page`). Interface between them: detail templates receive `ontology_key` and `in_ontology`.
  - Then: full suite, Playwright UAT, code review, PR, merge, PROD deploy with memory receipt.

## Key facts a cold reader needs

- Baseline suite on `main`: 88 passed.
- The Canon shares 14,407 bare IDs with FOLIO; every tree lookup must stay inside the selected ontology.
- The Canon declares four of its seven visible top-level branches with no parent; root detection must accept "no parent or only owl:Thing".
- Damien directed that the Canon load in the background after FOLIO, in stages, so it never slows FOLIO.

## Resume

Resume `ce-work` on the plan path above from the branch tip; progress lives in the branch's commits.
