Use $cybervpn-autonomous-delivery.

TASK ID
CYBA-XXX

TASK
<Одно точное название функции/исправления.>

USER-VISIBLE OUTCOME
<Что пользователь, оператор или связанная система реально сможет сделать или увидеть после завершения.>

CURRENT BEHAVIOR
<Что происходит сейчас и почему это неправильно.>

REPRODUCTION
1. ...
2. ...
3. Actual result: ...
4. Expected result: ...

AUTHORITATIVE SOURCES
- Ticket/issue: ...
- Product/spec document: ...
- ADR: ...
- OpenAPI/database/protocol contract: ...
- Existing regression test: ...

IN SCOPE
- ...
- ...

OUT OF SCOPE
- ...
- ...

AFFECTED SURFACES
- [ ] backend
- [ ] frontend
- [ ] admin
- [ ] partner
- [ ] cybervpn_mobile
- [ ] desktop client
- [ ] browser extension
- [ ] worker/service
- [ ] Verta/protocol
- [ ] API/OpenAPI/generated clients
- [ ] database/migration/backfill
- [ ] infrastructure/CI
- [ ] observability
- [ ] release/deployment

ARCHITECTURAL CONSTRAINTS
- Следуй существующим domain/application/infrastructure и UI boundaries.
- Не размещай business rules в React component, route adapter или ORM model.
- Используй typed request/response/event contracts.
- Не редактируй generated clients вручную.
- Сохрани backward compatibility, если это ТЗ явно её не отменяет.
- Не добавляй production mock, hard-coded demo data или silent fallback.
- Сохрани существующие комментарии, кроме ставших фактически неверными.

ACCEPTANCE CRITERIA
AC-01. <Один наблюдаемый outcome.>
AC-02. <Production execution path и persisted/state outcome.>
AC-03. <Failure/degraded/retry behavior.>
AC-04. <Authentication/authorization/tenant behavior.>
AC-05. <Idempotency/concurrency/replay behavior.>
AC-06. <Loading/empty/error/success UI behavior.>
AC-07. <API/generated client compatibility.>
AC-08. <Migration/backfill/downgrade behavior.>
AC-09. <Logging/metrics/tracing/audit behavior.>
AC-10. <Automated/runtime validation.>

NEGATIVE ACCEPTANCE CRITERIA
NAC-01. Documentation, screenshot, QA report или evidence artifact не заменяют implementation.
NAC-02. Build success не заменяет functional test/runtime evidence.
NAC-03. Mock call, handler invocation или HTTP status без business-state assertion не доказывают flow.
NAC-04. Нельзя возвращать success, если операция не завершила intended state transition.
NAC-05. Нельзя swallow errors или превращать failure в empty-success state.
NAC-06. Нельзя ослаблять, удалять, skip/xfail tests ради green run.
NAC-07. Нельзя использовать git commit --no-verify.
NAC-08. Нельзя вручную править generated API clients.
NAC-09. Нельзя переносить repository-controlled in-scope requirement в technical debt вместо реализации.
NAC-10. Нельзя ставить issue/task Done до TASK_STATUS: VERIFIED.
NAC-11. Нельзя объявлять failure pre-existing без воспроизведения на clean merge base.
NAC-12. Нельзя менять unrelated files.

SECURITY AND PRIVACY INVARIANTS
- Authentication: ...
- Authorization/RBAC/object ownership: ...
- Realm/tenant/workspace isolation: ...
- Cookie/session/token/passkey/Telegram behavior: ...
- CSRF/Origin/redirect behavior: ...
- Replay/idempotency/race behavior: ...
- Rate/resource limits: ...
- Secrets/PII/VPN config fields, которые нельзя логировать: ...
- Payment/settlement/provider integrity: ...

DATA AND MIGRATION
- Schema changes: ...
- Backfill: ...
- Upgrade compatibility: ...
- Downgrade/rollback: ...
- Transaction boundaries: ...
- Concurrent uniqueness/idempotency: ...

OBSERVABILITY
- Logs: ...
- Metrics: ...
- Traces: ...
- Audit events: ...
- Alerts/dashboard impact: ...
- Redaction requirements: ...

REQUIRED TESTS
- Backend unit: ...
- Backend integration: ...
- Backend route/e2e/conformance: ...
- Frontend/admin/partner component interaction: ...
- Browser/runtime smoke: ...
- API/OpenAPI/generated client: ...
- Authorization/tenant negative: ...
- Idempotency/concurrency/replay: ...
- Migration upgrade/downgrade: ...
- Regression: ...

REQUIRED VALIDATION
До implementation внеси exact команды в `.codex/current-task.json`.
Каждая required команда должна получить status, exit code и evidence.

Примеры:
- `npm run lint -w partner`
- `npm exec -w partner -- tsc --noEmit`
- `npm run test:run -w partner`
- `NEXT_TELEMETRY_DISABLED=1 npm run build -w partner`
- `backend/.venv/bin/python -m ruff check backend`
- `backend/.venv/bin/python -m ruff format --check backend`
- `backend/.venv/bin/python -m mypy backend/src --ignore-missing-imports --no-strict-optional`
- `backend/.venv/bin/python -m pytest backend/tests/... -v`
- `scripts/codex/verify-changed.sh`
- task-specific migration/runtime/browser/staging smoke

AGENT PROTOCOL
1. Spawn `repo_mapper` and `requirements_auditor` in parallel.
2. Wait for both and update acceptance criteria/matrix.
3. Present a concise implementation plan, then continue in the same turn.
4. Use one production-code writer for overlapping files. Use worktrees for independent parallel writers.
5. Install missing dependencies/system packages and start local services autonomously.
6. Delegate narrow implementation slices to relevant specialists.
7. After integration spawn `verifier` and `adversarial_reviewer` in parallel.
8. For security-sensitive scope also spawn `security_reviewer`.
9. Wait for all reviewers, fix every actionable finding, rerun affected checks.
10. Repeat verifier after material fixes.

EXECUTION RULES
- Не спрашивай routine confirmation.
- Не останавливайся после плана.
- Не сокращай ТЗ во время реализации.
- При неопределённости сначала исследуй code/spec/docs; затем выбери самый compatible, secure и reversible вариант и запиши assumption.
- Python debugging: используй focused `print()`/structured logs без secrets.
- JS/TS debugging: используй focused `console.log()`/`console.trace()` без secrets; убери noisy temporary output до VERIFIED.
- Не push/deploy production, если это прямо не входит в TASK. Если входит — выполни автономно и приложи evidence/rollback.

COMPLETION CONTRACT
- NOT RUN != PASS.
- SKIPPED != PASS.
- Compile/build != feature success.
- Documentation/evidence != implementation.
- Child-agent statement != independent proof.
- TASK_STATUS: VERIFIED разрешён только при PASS всех AC/NAC, required validation, verifier и adversarial review и пустом unresolved.

FINAL RESPONSE FORMAT

TASK_STATUS: VERIFIED|PARTIAL|BLOCKED

## Acceptance criteria
| AC | Status | Implementation evidence | Test/runtime evidence |

## Validation
| Command | Exit code | Result | Evidence |

## Review
| Finding | Agent/reviewer | Resolution |

## Unresolved
<Exact list or None>

## Changed files
- Production:
- Tests:
- Migrations:
- Generated:
- Documentation:
