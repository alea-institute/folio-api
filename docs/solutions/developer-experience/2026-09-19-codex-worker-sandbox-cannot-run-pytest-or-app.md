---
title: "Codex workers cannot run pytest or boot the app in their sandbox — verify on the host"
date: 2026-09-19
category: developer-experience
module: folio_api
problem_type: developer_experience
component: development_workflow
severity: medium
applies_when:
  - "Dispatching a Codex worker (agents/worker-wrapper.sh or codex exec) into this repo with a task that says to run pytest, import folio_api, or start uvicorn"
  - "Reading a worker report that says the literal test or import command was BLOCKED with a read-only filesystem error"
tags: [codex, worker-sandbox, pytest, folio-cache, orchestration, verification]
---

# Codex workers cannot run pytest or boot the app in their sandbox — verify on the host

## Context

During the navigable-search-results feature (PR #23, 2026-09-19), every Codex worker that was asked to run `pytest`, import the route modules, or start `uvicorn` reported the same class of failure. Each worker burned time diagnosing it independently and one built an in-memory monkeypatch wrapper to get a red/green run at all. The orchestrator's host runs of the same commands passed on the first try.

## Guidance

- Codex runs with `sandbox_mode = "workspace-write"` (see `~/.codex/config.toml` as configured on this box). Writes outside the repo are refused, and this repo's dependencies write outside the repo at import or startup time. As reported by the workers (not re-verified against dependency source here):
  - Importing `folio_api.routes.*` pulls in the `alea` LLM client, which opens `~/.alea/logs/alea_llm_client.log` for writing on import. In the sandbox that raises `OSError: [Errno 30] Read-only file system` before any test runs.
  - Booting the app (`uvicorn folio_api.api:app`) makes the FOLIO library try to rewrite its cached OWL under `~/.folio/cache/github/`, which fails the same way, so the server exits immediately.
  - `TestClient` also stalled for one worker because local socket-pair sends raised `EPERM`, so even a patched import did not give a normal test run.
- Therefore: write task packets that say "run `node --check` / static self-review only; the orchestrator runs pytest and the browser smoke". Do not ask a worker for a red/green pytest run or a server smoke in this repo unless the sandbox has been changed to allow those paths.
- The orchestrator (Claude session, host shell) runs `.venv/bin/pytest -q -p no:cacheprovider` and the app on the project's deterministic port (9616 for this repo name) after each worker lands, before committing that unit.
- If a worker's report claims a pytest pass, check how it ran: one worker's report showed a stdin wrapper that monkeypatched `logging.FileHandler`, `socket.connect`, and the selector loop to get 9 passing tests. Treat that as a hint, not as the authoritative run.

## Why This Matters

Without this note, each new orchestrator will keep writing "run pytest" into worker packets, each worker will spend its first minutes failing on the same two home-directory writes, and reports will come back either "BLOCKED" or with home-grown wrappers whose results are hard to trust. Host verification is fast here (full suite about 50s with the ontology cache warm) and is what the plan's Verification Contract already assigns to the orchestrator.

## When to Apply

- Any Codex-dispatched unit in this repo that touches Python or needs the running app.
- Reviewing a worker report: a claimed test or server result that could not have happened in the sandbox is a report-quality flag, not a code-quality flag.
- Deciding sandbox policy: if hands-off worker verification is wanted, the fix is on the environment side (an allowlisted writable path for the two home-directory writes), not in the workers' prompts.

## Examples

Worker report excerpt (U1 backend, 2026-09-19): "The literal requested pytest and import commands cannot succeed in this sandbox: the dependency opens a home-directory log on import. TestClient also stalls because local socket-pair sends raise EPERM." Host run of the same command a minute later: `9 passed in 4.81s`.

Worker report excerpt (U3/U4 frontend): "Startup failed immediately (exit 3): FOLIO attempted to rewrite its cached OWL under `~/.folio/cache/github/`, which is read-only in this sandbox."

## Related

- `docs/plans/2026-09-19-1408-feat-search-results-navigable-tree-plan.md` (Verification Contract assigns pytest and the browser smoke to the orchestrator; KTD9 records that no JavaScript test runner exists)
- Cockpit `CLAUDE.md`, "How to launch work" (worker-wrapper dispatch and the no-polling rule that shaped this workflow)
