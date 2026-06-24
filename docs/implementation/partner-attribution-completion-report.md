# Partner Attribution Completion Report

Task: `PARTNER-ATTRIBUTION-HARDENING`

Current repository status for this run: local verification passed, GitHub and
GitLab `main` are synchronized on the delivered code SHA, and GitHub CI for the
code delivery SHA passed.

## Delivered Behavior

- Public customer attribution capture uses a dedicated backend realm dependency
  that ignores forged realm headers and accepts only trusted public hosts.
- The customer public `/p/[publicToken]` route strips spoofed forwarding
  headers, sets an opaque HttpOnly browser cookie, sends a deterministic
  idempotency key, limits destination selection to server-owned keys, preserves
  backend `429 Retry-After`, and falls back when backend redirects are unsafe.
- Backend capture reuses an active pending attribution session for the same
  browser/idempotency key instead of duplicating sessions and touchpoints on
  reload.
- Consumed transfer tokens move to explicit replay state and are removed from
  the active transfer-token column after first use.
- Persistent partner code links, claim concurrency, active-owner uniqueness,
  immutable commission contracts, and corrective commercial-owner effective
  range constraints are enforced by PostgreSQL-backed migrations and tests.
- Order attribution resolver precedence prefers persistent reseller binding
  over passive click when no explicit checkout touchpoint exists.
- Production CORS includes the partner portal origin for cookie-authenticated
  unsafe requests.
- Backend CI now treats type checking as a required gate: `mypy` no longer uses
  `continue-on-error`, and the aggregate backend check fails on typecheck
  failure.
- JWT decode clock-skew tolerance is bounded at 30 seconds and covered by both
  positive and negative security tests.

## Verification Summary

| Area | Command | Result |
| --- | --- | --- |
| Backend lint | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret .venv/bin/python -m ruff check .` from `backend/` | Exit 0, all checks passed |
| Backend format | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret .venv/bin/python -m ruff format --check .` from `backend/` | Exit 0, 1465 files already formatted |
| Backend typecheck | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret .venv/bin/python -m mypy src --ignore-missing-imports --no-strict-optional` from `backend/` | Exit 0, no issues in 1032 source files |
| Backend full suite | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_REDIS_URL=redis://127.0.0.1:6380/15 .venv/bin/python -m pytest tests -v --tb=short` from `backend/` | Exit 0, 2230 passed, 79 skipped, coverage 79.68% |
| Generated artifacts | `PYTHON_BIN=backend/.venv/bin/python PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret bash scripts/check-generated-artifacts.sh` from repo root | Exit 0, backend OpenAPI plus frontend/admin/partner generated API types and i18n bundles are in sync |
| Migration cycle | Clean PostgreSQL database: `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head` | Exit 0, `20260622_partner_owner_ranges` head reached, downgraded to `20260621_partner_slug_required`, then re-upgraded to head |
| PostgreSQL partner tests | `CYBERVPN_TEST_POSTGRES_URL=<clean-temp-postgres> .venv/bin/python -m pytest tests/integration/test_partner_attribution_claim_postgres.py tests/integration/test_partner_commission_contracts_migration_postgres.py -q --tb=short --no-cov` from `backend/` | Exit 0, PostgreSQL-specific attribution/commission migration tests reached 100% |

User runtime evidence on 2026-06-24 covered the remaining browser-facing
acceptance checks for the vertical partner attribution flow. Local repository
evidence covers backend state transitions, generated contracts, migration
rollback/reapply behavior, PostgreSQL constraints/concurrency, and release
gate correctness.

## Review Resolution

- Final verifier found no local blocker before commit/push; post-push evidence
  confirmed GitHub/GitLab remote parity and passing GitHub CI on the delivered
  code SHA.
- Final security reviewer found no blocker in the current diff. The JWT leeway
  remains bounded, signature/issuer/audience/revocation checks are unchanged,
  and no new secret/PII logging was introduced.
- Final adversarial reviewer found stale evidence documents and task-contract
  text that still declared an incomplete status; this report, the test matrix,
  migration preflight, and `.codex/current-task.json` were reconciled with the
  final command evidence.

## Scope Notes

- The final main-bound diff contains no tracked changes under
  `cybervpn_mobile/`, desktop, browser extension, or mobile client source.
- Existing mobile-related files already present in `HEAD` were not part of the
  final uncommitted stabilization diff.
- No library versions were downgraded.
- No production secrets were emitted in source, task evidence, logs, or final
  reports.

## Rollout And Rollback

- Rollout: apply migrations to head, deploy backend/API clients together, and
  keep backend CI typecheck as a blocking gate.
- Rollback: downgrade the latest partner owner range migration by one revision
  to remove the corrective active-owner range constraints. Earlier replay-state
  migration rollback drops its added indexes/columns and does not reconstruct
  consumed transfer-token history.
- Operational check: after deployment, monitor partner attribution capture,
  claim, payment-to-earning, outbox publication, and partner statement metrics
  for duplicate-owner, duplicate-earning, and replay rejection anomalies.
