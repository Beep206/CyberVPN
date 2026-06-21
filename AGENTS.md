# CyberVPN Autonomous Codex Operating Contract

## Mission

CyberVPN is a production polyglot VPN-business monorepo. Work autonomously,
finish the requested scope end to end, and prove the result. Do not stop after
analysis or a plan. Do not ask for routine permission to edit files, install
dependencies, run Docker, start local services, generate code, create
migrations, or execute validation.

The CLI runs with full filesystem/network access and no approval prompts. Use
that access to complete the task, not to reduce engineering discipline.

## Repository surfaces

- `backend/`: FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Redis.
- `frontend/`: customer Next.js application.
- `admin/`: administrative Next.js application.
- `partner/`: partner Next.js application.
- `cybervpn_mobile/`: Flutter mobile client.
- `apps/desktop-client/`: Tauri/Rust desktop client.
- `apps/browser-extension/`: browser extension.
- `services/`: Python and Rust services, bots, workers and controllers.
- `packages/`: shared TypeScript/Rust/Flutter packages and Verta protocol.
- `infra/`: local and deployment infrastructure.

Read the nearest nested `AGENTS.md` before editing a surface. Nested rules add
surface-specific requirements but never weaken this completion contract.

## Source-of-truth order

1. The current user request and numbered acceptance criteria.
2. Governing specifications, ADRs, OpenAPI, database constraints and approved
   product contracts.
3. Observable production behavior and persisted state.
4. Automated tests, runtime smoke evidence and generated-artifact checks.
5. Implementation code.
6. README files, plans, screenshots, QA reports, evidence folders and task
   tracker statuses.

Documentation, a successful build, a DTO, a schema, a mocked response, a
rendered page or a generated evidence report does not independently prove that
a feature works.

## Autonomous execution protocol

For every non-trivial implementation, fix, refactor or release task:

1. Inspect `git status`, the current branch and the merge base.
2. Read the full task and applicable instructions/specifications.
3. Trace the existing production path before editing.
4. Create or refresh `.codex/current-task.json` using
   `scripts/codex/init-task.sh` or the bundled template.
5. Convert the request into atomic, numbered, observable acceptance criteria.
6. Map affected applications, services, contracts, migrations, generated
   clients, workers and deployment surfaces.
7. Identify mocks, placeholders, silent fallbacks, hard-coded data, TODOs,
   swallowed errors and untested branches.
8. Spawn `repo_mapper` and `requirements_auditor` for broad or cross-surface
   work. Wait for both before finalizing the implementation matrix.
9. Produce a concise plan, then continue implementation in the same turn.
10. Use the narrowest specialist agents. Only one agent writes a shared file
    set at a time unless separate git worktrees provide isolation.
11. Install missing dependencies autonomously. Prefer reproducible project
    tooling; use `sudo -n` for required WSL system packages.
12. Add tests that prove resulting state, response, side effect, artifact or
    user interaction. Include negative and failure paths.
13. Run targeted checks first, then every gate for each affected surface.
14. Spawn `verifier` and `adversarial_reviewer` after implementation. Resolve
    every actionable finding and rerun affected checks.
15. Review the complete diff against the original request, not merely the plan.
16. Finish with the exact status/evidence format below.

Do not pause for confirmation when a reasonable implementation can be derived
from code, specifications and established patterns. When ambiguity remains,
choose the most compatible, secure and reversible option and record the
assumption in the task contract.

## Completion states

Use exactly one final marker:

- `TASK_STATUS: VERIFIED` — every required criterion and validation passed.
- `TASK_STATUS: PARTIAL` — useful work exists but one or more criteria remain.
- `TASK_STATUS: BLOCKED` — an external dependency, unavailable environment,
  permission, credential or unresolved product decision prevents completion.

Never say Done, Complete, Finished, Fully implemented or an equivalent claim
unless the marker is `TASK_STATUS: VERIFIED`.

A task may be VERIFIED only when all of the following are true:

- Every acceptance criterion is `pass` in `.codex/current-task.json`.
- Each criterion has implementation and test/runtime evidence.
- The complete production execution path is connected.
- Success, loading, empty, error, permission and retry behavior is correct when
  relevant.
- Tests assert business results, not merely rendering, invocation, mocks or an
  HTTP status code.
- All affected surfaces pass lint, typecheck, tests and production build.
- Backend changes pass Ruff, format check, mypy and pytest.
- API changes regenerate all affected clients and a second regeneration leaves
  no diff.
- Migrations have upgrade, downgrade and data/backfill verification.
- Security-sensitive changes include negative authorization, tenant-isolation,
  replay/idempotency and sensitive-logging tests where relevant.
- No required validation is skipped.
- The final diff contains no unrelated changes.
- Independent verification and adversarial review found no unresolved defect.

## Prohibited shortcuts

- Do not use `git commit --no-verify`.
- Do not bypass or weaken tests, hooks, type checks, migrations or generated
  drift checks to obtain green output.
- Do not manually patch generated clients when a generator exists.
- Do not replace implementation with documentation, diagnostics, screenshots,
  fixtures or evidence files.
- Do not treat a successful compile/build as proof of runtime behavior.
- Do not silently omit difficult acceptance criteria.
- Do not return successful business responses for operations that did not
  commit their intended state.
- Do not swallow unexpected exceptions or convert failures to empty success.
- Do not call a failure “pre-existing” unless it is reproduced on the clean
  merge base with the same command and environment.
- Do not push directly to `main` or deploy production unless the current task
  explicitly requires that action. Branch creation, commits, local services,
  migrations and test environments are autonomous by default.
- Never expose passwords, cookies, JWTs, refresh tokens, raw Telegram initData,
  VPN configuration links, provider tokens, private keys or customer PII in
  source, logs, task contracts, screenshots or final responses.

## Validation matrix

### Web workspaces (`frontend`, `admin`, `partner`)

Run for every affected workspace:

```bash
npm run prepare:i18n -w <workspace>
npm run lint -w <workspace>
npm exec -w <workspace> -- tsc --noEmit
npm run test:run -w <workspace>
NEXT_TELEMETRY_DISABLED=1 npm run build -w <workspace>
```

Verify loading, empty, success, error, retry, permission, responsive, keyboard,
a11y and localization behavior affected by the task.

### Backend

Use the project venv when present. Install dev dependencies and mypy when
missing, then run:

```bash
cd backend
python -m ruff check .
python -m ruff format --check .
python -m mypy src --ignore-missing-imports --no-strict-optional
python -m pytest tests -v --tb=short
```

Add focused unit/integration/e2e tests before the full suite.

### API/OpenAPI changes

Export the current OpenAPI document, regenerate clients in `frontend`, `admin`
and `partner`, run affected typechecks/tests/builds, then regenerate once more
and require `git diff --exit-code` for generated artifacts.

### Database migrations

Apply to a clean database, verify schema/data, downgrade, verify rollback, then
reapply. Test idempotency and concurrent uniqueness constraints when relevant.

### Rust

Run formatting, clippy with warnings denied, tests and affected smoke commands
for the nearest workspace:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
```

Verta work remains governed by `packages/verta-protocol/AGENTS.md` and its
normative specifications.

### Flutter

```bash
dart format --output=none --set-exit-if-changed .
flutter analyze --fatal-warnings
flutter test
```

Run platform/integration tests when platform channels, VPN lifecycle,
permissions, background services, deep links or secure storage change.

### Infrastructure and shell

Run `shellcheck` for changed shell scripts, `docker compose config` for changed
Compose definitions, and the relevant Terraform/Helm/Kubernetes validators for
changed infrastructure.

`scripts/codex/verify-changed.sh` provides an autonomous changed-surface gate;
it does not replace task-specific runtime validation.

## Debugging

- Python: add focused `print()` or structured logs while diagnosing; include
  identifiers and state transitions but never secrets. Remove noisy temporary
  output after the defect is understood.
- JavaScript/TypeScript: use `console.log()` and `console.trace()` for focused
  diagnosis; remove temporary noisy or sensitive diagnostics before VERIFIED.
- Preserve existing commented code unless the task explicitly makes it stale.
- Prefer deterministic reproduction scripts over speculative fixes.

## Final response format

The final response must begin with one exact status marker and then contain:

```text
TASK_STATUS: VERIFIED|PARTIAL|BLOCKED

## Acceptance criteria
| AC | Status | Implementation evidence | Test/runtime evidence |

## Validation
| Command | Exit code | Result | Evidence |

## Review
| Finding | Agent/reviewer | Resolution |

## Unresolved
Exact list, or None.

## Changed files
Production, tests, migrations, generated artifacts and docs grouped separately.
```
