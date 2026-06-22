# CyberVPN Engineering Contract for Codex

## Scope and instruction loading

This file governs the entire CyberVPN repository. A nested `AGENTS.md` adds
surface-specific rules and may be stricter, but it must not weaken this
contract.

Codex discovers project instructions only from the repository root down to the
directory where the session was started. When a session starts at the
repository root, nested files are not loaded automatically. Before editing any
surface, open its applicable instructions explicitly:

| Surface | Required local instructions |
| --- | --- |
| Backend API and migrations | `backend/AGENTS.md` |
| Customer web application | `frontend/AGENTS.md` |
| Admin web application | `admin/AGENTS.md` |
| Partner web application | `partner/AGENTS.md` |
| Flutter mobile client | `cybervpn_mobile/AGENTS.md` |
| Tauri desktop client | `apps/desktop-client/AGENTS.md` |
| Browser extension | `apps/browser-extension/AGENTS.md` |
| Services and workers | `services/AGENTS.md` plus the nearest service file |
| Shared packages | `packages/AGENTS.md` plus the nearest package file |
| Infrastructure | `infra/AGENTS.md` |
| Verta protocol | `packages/verta-protocol/AGENTS.md` and `docs/spec/` |

Use manifests and lockfiles as the source of truth for installed versions.
Do not copy version numbers from prose when `package.json`, `pyproject.toml`,
`Cargo.toml`, `pubspec.yaml`, or a lockfile says otherwise.

## Mission

Deliver the requested behavior end to end, with the smallest coherent patch
that satisfies the complete task. Use the configured autonomy to investigate,
install dependencies, run services, implement, test, and repair the result.
Autonomy never permits weaker engineering evidence.

Do not stop after analysis or a plan. Do not ask for routine permission to edit
files, install development dependencies, start local services, generate code,
create local migrations, or execute validation. Production deployment,
production data mutation, credential rotation, destructive infrastructure
actions, and direct pushes to `main` require explicit task scope.

## Source-of-truth order

1. The complete current task, including approved amendments and linked
   acceptance criteria.
2. Normative specifications, ADRs, OpenAPI contracts, database invariants,
   security policies, and provider contracts.
3. Existing externally observable behavior that must remain compatible.
4. Persisted state and real production execution paths.
5. Automated tests and deterministic runtime evidence.
6. Implementation code.
7. README files, plans, screenshots, QA reports, evidence folders, and task
   tracker status.

`.codex/current-task.json` is a derived execution record, not a replacement for
the original task. Never rewrite acceptance criteria to match an incomplete
implementation. Re-read the original task before final review.

When sources conflict, preserve the stricter security and compatibility
guarantee. A reversible implementation detail may follow the nearest
established pattern. Do not invent behavior that changes billing, financial
ownership, authentication, authorization, protocol semantics, destructive data
handling, or public compatibility; resolve it from an authoritative source or
record the exact blocker.

## Mandatory pre-edit investigation

Before changing code:

1. Inspect `git status --short`, the current branch, remotes, and the merge base.
2. Preserve unrelated user changes. Never reset, overwrite, or reformat them.
3. Read the full task and every directly referenced document, comment, schema,
   screenshot, fixture, and acceptance criterion.
4. Read the applicable nested `AGENTS.md` files.
5. Locate the current production path, its state owner, trust boundary,
   transaction boundary, generated artifacts, and closest tests.
6. Find at least one similar working implementation before creating a new
   abstraction.
7. Search for existing helpers, components, schemas, repository methods,
   policies, and libraries before adding duplicates.
8. Build a change-impact map covering applications, services, packages,
   migrations, generated clients, workers, monitoring, and deployment.
9. For a bug fix, add or identify a regression test that demonstrates the
   defect before the fix when practical.
10. Record assumptions that affect behavior. Do not silently broaden scope.

Prefer a focused patch over opportunistic cleanup. Refactor adjacent code only
when it is required to make the requested behavior correct, testable, or safe.

## Task contract and acceptance criteria

For every non-trivial implementation, fix, refactor, migration, security, or
release task, create or refresh `.codex/current-task.json` using the project
template.

Each acceptance criterion must be atomic and observable. It must identify:

- the user or system outcome;
- the production path and owning surface;
- success behavior;
- relevant loading, empty, error, permission, retry, and degraded behavior;
- persisted state or side effect;
- required automated test;
- required runtime or integration evidence.

Add negative criteria for relevant trust, tenant, replay, idempotency,
concurrency, rollback, compatibility, localization, accessibility,
observability, performance, timeout, and sensitive-data requirements.

A criterion cannot pass because a file exists, a component renders, a mock was
called, an endpoint returned a nominal status, a build succeeded, or a report
was generated. Evidence must prove the requested behavior.

## Agent orchestration

Use subagents when they create real separation of concerns:

- For broad or cross-surface work, run `repo_mapper` and
  `requirements_auditor` before finalizing the implementation matrix.
- Delegate implementation to the narrowest specialist agent with explicit file
  ownership.
- Only one agent may write an overlapping file set. Use separate worktrees for
  genuinely independent writing tracks.
- The parent agent owns scope, architecture, integration, conflict resolution,
  the final diff, and final status.
- After implementation, run `verifier` and `adversarial_reviewer` independently
  and resolve every actionable finding.
- Use `security_reviewer` for authentication, authorization, sessions, payment,
  attribution, VPN configuration, secrets, protocol, parser, infrastructure,
  or privacy changes.

Agent output is advisory evidence, not proof by itself. Inspect the resulting
code and rerun validation after integrating agent changes.

## Code-quality baseline

- Follow the existing architecture and naming conventions of the affected
  surface. Do not introduce a second architectural style.
- Keep business rules in the owning domain/application layer, not duplicated in
  UI, routes, adapters, migrations, or tests.
- Prefer explicit types, value objects, enums, and validated schemas over loose
  dictionaries, magic strings, unchecked casts, and implicit coercion.
- Do not add `any`, `@ts-ignore`, blanket `type: ignore`, broad lint disables,
  broad exception catches, empty catches, or unsafe blocks without a narrowly
  documented reason and a test.
- Validate untrusted input at every trust boundary. Normalize once, then pass a
  typed representation inward.
- Make state transitions and transaction ownership explicit. Validate before
  side effects and commit intended state atomically where the workflow
  requires it.
- Design mutation paths for retries, duplicates, concurrency, cancellation, and
  partial external failure where relevant.
- Bound pagination, queues, retries, concurrency, memory, payload sizes,
  timeouts, and external calls. Avoid unbounded work.
- Do not introduce blocking I/O into asynchronous paths.
- Do not add a production dependency until existing project capabilities have
  been checked. Add the narrowest compatible dependency and update lockfiles
  intentionally; never run broad dependency upgrades as a side effect.
- Do not copy security, pricing, entitlement, attribution, subscription, or
  protocol logic between surfaces. Expose one authoritative implementation.
- Preserve useful comments and commented code unless the task makes them
  factually stale. Add comments for invariants and non-obvious decisions, not
  for restating syntax.
- Remove dead code, temporary bypasses, debug flags, and noisy diagnostics
  introduced by the task before verification.

## Error handling and observability

- Fail explicitly with stable typed/domain errors. Map them to public responses
  at the boundary without leaking stack traces or provider internals.
- Never convert an unexpected failure into empty or successful business state.
- Retry only operations that are safe to retry, with bounded backoff and clear
  terminal behavior.
- Preserve causal context and safe correlation identifiers in logs and traces.
- Add or update metrics, audit events, and diagnostics when operators need them
  to understand the new behavior.
- Never log passwords, cookies, JWTs, refresh tokens, raw Telegram initData,
  payment secrets, VPN/subscription URLs, provider tokens, private keys, device
  credentials, or customer PII.
- Temporary `print`, `console.log`, `console.error`, or `console.trace` may be
  used for focused diagnosis, but remove noisy or sensitive output before
  `VERIFIED`.

## Testing rules

- Test the behavior at the lowest useful layer and the integration at the
  boundary that could break.
- Assert resulting domain state, database state, emitted event, artifact,
  external request contract, cache update, or visible interaction.
- For mutations, test success, validation failure, authorization failure,
  duplicate/retry behavior, and relevant concurrency or partial failure.
- Mock only true external boundaries. Do not mock away the code path the test is
  supposed to prove.
- Keep tests deterministic: no arbitrary sleeps, real internet dependency,
  current-time races, order dependence, shared mutable global state, or
  production credentials.
- Prefer controlled clocks, deterministic IDs, local containers, fakes at
  provider boundaries, and explicit eventual-consistency polling with bounds.
- A snapshot or render-only test is supplementary, not sufficient for
  interactive or business behavior.
- Do not weaken assertions, delete coverage, add broad skips/xfails, or alter
  fixtures merely to make broken implementation pass.
- Test results become stale after relevant code changes. Rerun targeted checks
  and every affected required gate after the final modification.

## Contracts, generated artifacts, and migrations

When API behavior or schemas change:

1. Update the canonical backend contract.
2. Export OpenAPI.
3. Regenerate every affected customer, admin, partner, SDK, and service client.
4. Run consumer typechecks and contract tests.
5. Regenerate a second time and require no generated diff.

Never manually patch a generated file when a generator exists.

For database changes:

- inspect current heads and production PostgreSQL behavior;
- write deterministic, bounded migrations without importing current ORM models;
- preserve data and compatibility unless destructive behavior is explicit;
- enforce invariants with database constraints/indexes where appropriate;
- test clean upgrade, populated upgrade/backfill, downgrade, and re-upgrade;
- test concurrent uniqueness/idempotency behavior when relevant;
- document any genuinely irreversible operation.

For cross-surface changes, prove the complete vertical path rather than
validating each disconnected layer separately.

## Validation policy

Run focused checks during development, then all gates for every affected
surface after the final change. Read the nearest `AGENTS.md` for exact commands.

`scripts/codex/verify-changed.sh <base-ref>` is a convenience gate and evidence
collector. It does not replace task-specific integration, browser, migration,
provider, platform, performance, or security validation.

Validation requirements:

- Record the exact command, working directory, exit code, and evidence.
- `NOT RUN`, skipped, timed out, `continue-on-error`, ignored warnings, or
  `|| true` output is not `PASS`.
- Treat compiler, typechecker, linter, test, migration, generated-drift, and
  security warnings as failures when the project gate does.
- Fix the root cause, rerun the smallest failing check, then rerun all affected
  final gates.
- Do not claim a failure is pre-existing until the same command is reproduced
  on a clean merge-base worktree with equivalent dependencies and environment.
- If a full repository gate is currently impossible, complete all controlled
  work and report the exact command, failure, affected criterion, and blocker.

## Security and trust boundaries

For every entry point, identify the caller, credentials, realm, tenant,
workspace, role, object ownership, allowed state transition, and audit need.

- Authorization must be enforced at the backend or privileged service boundary,
  never only in UI, proxy, route visibility, or client state.
- Protect against mass assignment, IDOR, replay, CSRF, SSRF, open redirects,
  path traversal, command injection, SQL injection, unsafe deserialization,
  unbounded resource use, and sensitive error disclosure where relevant.
- Use cryptographic and authentication libraries through documented APIs. Do
  not invent cryptography, token formats, nonce schemes, or signature logic.
- Preserve secure cookie, origin, session revocation, rate-limit, audit, and
  tenant-isolation behavior.
- Tests must include relevant negative and cross-tenant cases.

## Git and diff hygiene

- Use one coherent task per branch. Prefer `codex/<task-id>-<slug>`.
- Never push directly to `main`.
- Do not use `git commit --no-verify`.
- Do not force-push over user-owned commits.
- Before handoff inspect `git status --short`, `git diff --check`,
  `git diff --stat`, the complete diff against the merge base, deleted files,
  generated files, migrations, and untracked artifacts.
- Exclude temporary logs, coverage output, local databases, credentials,
  screenshots with sensitive data, build output, and unrelated formatting.
- Commit only after the recorded validation corresponds to the final diff.
- Do not claim CI passed until the actual run and required checks were read.

## Completion contract

Use exactly one final marker:

- `TASK_STATUS: VERIFIED`
- `TASK_STATUS: PARTIAL`
- `TASK_STATUS: BLOCKED`

`VERIFIED` requires:

- every acceptance criterion is `pass`;
- each criterion has implementation and test/runtime evidence;
- every required validation passed after the final relevant change;
- generated artifacts and migrations are synchronized and verified;
- security and compatibility requirements are satisfied;
- `verifier` and `adversarial_reviewer` passed with no unresolved finding;
- the final diff is focused and contains no unresolved task requirement.

Use `PARTIAL` when repository-controlled work remains incomplete. Use `BLOCKED`
only for a proven external dependency, unavailable credential/environment, or
unresolved authoritative product decision, and list the exact remainder.

Never say Done, Complete, Finished, Fully implemented, Ready, or
Production-ready unless the first line is `TASK_STATUS: VERIFIED`.

The final response must include:

```text
TASK_STATUS: VERIFIED|PARTIAL|BLOCKED

## Acceptance criteria
| AC | Status | Implementation evidence | Test/runtime evidence |

## Validation
| Command | Working directory | Exit code | Result | Evidence |

## Review
| Finding | Agent/reviewer | Resolution | Revalidation |

## Unresolved
Exact list, or None.

## Changed files
Production, tests, migrations, generated artifacts, infrastructure and docs.
```
