# fa-3 isolated API CI build evidence

Plan: `docs/plans/2026-10-27-2056-chore-fa-3-isolated-api-ci-plan.md`.
Item: fa-3 (hygiene), branch `drawdown/fa-3`.

## Starting state and scope

The build reverified a clean branch at `07eeda7`, containing only the plan above
baseline `39aeca1`. No repository `AGENTS.md` or `CLAUDE.md` was present. The chief
campaign plan and common mandate were unavailable here; the supplied campaign
rules governed the build. The controller must reconcile their Goal Capsule and
cited R11, R15-R17, R19 and R20 before accepting the branch.

U1 is committed in `a6e21ca`; U2 in `2097349`. U3 adds contributor instructions
and this receipt. Application code, all preexisting test modules, dependency
versions and the lockfile are unchanged. No frontend, production, deployment,
migration, data rewrite, package release or outside service work was performed.

The only supporting changes outside the plan's named file list are ignoring
generated `test-results/` and exempting exactly `tests/fixtures/folio.owl.gz` from
the existing large-file hook. The full public snapshot is about 3.7 MB and its
raw SHA-256 matches the plan. All other large files remain subject to the hook.

## Local execution evidence

Runtime: CPython 3.12.12, uv 0.9.22, pytest 8.4.2; dependencies installed from the
unchanged lock. TestClient and asyncio worked in this session. No socket,
event-loop or logging-handler workaround was used.

| Check | Result |
|---|---|
| `uv sync --locked --dev --python 3.12` | Passed; 93 packages installed |
| Isolation tests before implementation, with `--noconftest --no-cov` | Expected collection failure: missing `tests.support`; runtime configuration was not imported |
| `uv run --no-sync pytest tests/test_test_environment.py -ra` | 18 passed; includes fresh-process collection, digest failure cases, HTTPX/provider guards, shutdown errors and real startup |
| `uv run --no-sync pytest tests/test_app_starts.py tests/routes -ra` | 22 passed, zero skips, 43.28 seconds |
| Report tests before implementation | Expected collection failure: missing checker module |
| `uv run --no-sync pytest tests/test_ci_results.py -q --no-cov` | 24 passed |
| `uv run --no-sync pytest tests -ra --junitxml=test-results/pytest.xml` | 88 passed, zero skips/failures/errors, 53.57 seconds; 16 existing application/dependency deprecation warnings |
| `uv run --no-sync python scripts/check_pytest_results.py test-results/pytest.xml` | Accepted 88 testcase records |
| Black check of all five changed Python files | Passed |
| `actionlint .github/workflows/api-tests.yml` | Passed with actionlint 1.7.12, downloaded archive verified against its published SHA-256 |
| `git diff --check` | Passed |

The full suite retains the 46 existing tests and adds 42 isolation/report cases.
Coverage is 46% of existing application statements; this change introduces no
coverage threshold. JUnit and coverage XML are generated locally and ignored.

## Workflow checks and provenance

The workflow uses ordinary pull requests, pushes to `main`, and
`merge_group.checks_requested`; stable job name `API tests`; read-only contents;
checkout credentials not persisted; workflow/ref concurrency; a 15-minute job
timeout and an 8-minute pytest timeout. Pytest, report validation and upload are
separate steps, with no tolerated failure. Status-aware conditions retain reports
after ordinary failures. Only JUnit and coverage XML are uploaded for seven days.
No dependency, home, configuration or ontology cache is restored.

Action tags were resolved through their public repository APIs and their pinned
`action.yml` files inspected:

- [checkout v7.0.1](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1)
- [setup-uv v10.3.2](https://github.com/astral-sh/setup-uv/tree/07a047e608db84b3d8c06cd9a7c7dcc9c355c18e)
- [upload-artifact v7.0.2](https://github.com/actions/upload-artifact/tree/cf430e030ddbb5b0abf93d22962f4752f3646cd9)

The pinned uv version is the version used for local verification. Setup and sync
follow the [official uv Actions guide](https://docs.astral.sh/uv/guides/integration/github/).

## Acceptance remaining with the controller

This clone intentionally has no remote or GitHub login. No push, PR, hosted CI
run, merge or production access was attempted. The controller publishes the
branch and obtains a successful `API tests` run on the reviewed commit, including
its first cold-runner install and retained reports. A local pass is not evidence
that the hosted workflow, cancellation behavior or artifact service has run.
Campaign Astra/Fable reviews remain the controller's merge prerequisites.
