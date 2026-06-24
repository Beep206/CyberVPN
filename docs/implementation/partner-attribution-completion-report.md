# Partner Attribution Completion Report

Task: `PARTNER-ATTRIBUTION-HARDENING`

Current repository status for this run: local verification passed. GitHub and
GitLab `main` parity for the final commit is recorded in the task contract and
delivery response after push.

## Delivered Behavior

- Public customer attribution capture uses a dedicated backend realm dependency
  that ignores forged realm headers and accepts only trusted public hosts.
- The customer public `/p/[publicToken]` route strips spoofed forwarding
  headers, sets an opaque HttpOnly browser cookie, sends a deterministic
  idempotency key, limits destination selection to server-owned keys, preserves
  backend `429 Retry-After`, removes inbound `pat` query parameters from the
  backend `source_path`, and falls back when backend redirects are unsafe.
- The `/p/[publicToken]` route treats `NODE_ENV=production` as secure runtime
  even when `NEXT_PUBLIC_APP_ENV` is a non-production label such as `staging`,
  so local/test hosts are rejected and the browser attribution cookie is
  `Secure` in production builds.
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
| Frontend route regression | `npm exec -w frontend -- vitest run 'src/app/p/[publicToken]/route.test.ts'` from repo root | Exit 0, 1 file and 7 tests passed; proves `pat` is removed from backend `source_path`, campaign parameters remain, and production Node runtime keeps host/cookie security even with `NEXT_PUBLIC_APP_ENV=staging` |
| Frontend gates | `npm run prepare:i18n -w frontend`; `npm run lint -w frontend`; `npm exec -w frontend -- tsc --noEmit`; `npm run test:run -w frontend`; `NEXT_TELEMETRY_DISABLED=1 npm run build -w frontend` | All exit 0; full Vitest 196 files/1366 tests passed and production build generated 3522 static pages |
| Browser SQL E2E | `CYBERVPN_E2E_REDIS_URL=redis://127.0.0.1:6380/15 backend/.venv/bin/python scripts/testing/partner_attribution_browser_sql_evidence.py --evidence docs/evidence/partner-attribution/browser-sql-e2e-latest.json` | Exit 0; Chrome drove canonical `/p/{public_slug}` through local Next, backend capture persisted one partner session, one touchpoint, one outbox event, and an HttpOnly browser cookie; tracked evidence stores structured counters instead of browser DOM or raw log tails |
| Downstream revenue-path matrix | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_POSTGRES_URL=postgresql+asyncpg://postgres:[REDACTED]@127.0.0.1:6767/postgres .venv/bin/python -m pytest tests/integration/test_quote_checkout_sessions.py::test_postgres_concurrent_quote_and_claim_routes_share_single_pending_attribution tests/integration/test_order_attribution_resolution_postgres.py::test_postgres_concurrent_order_attribution_resolve_returns_single_result tests/e2e/test_phase4_settlement_foundations.py::test_phase4_settlement_foundations_end_to_end tests/integration/test_settlement_adjustments.py::test_refund_and_dispute_create_typed_settlement_side_effects tests/integration/test_partner_statement_lifecycle.py::test_partner_statement_lifecycle_close_reopen_and_adjustments -q --tb=short --no-cov --continue-on-collection-errors` | Exit 0, 5 tests passed; proves persisted claim/binding, quote snapshot, order attribution, settlement E2E, statement lifecycle, and refund/dispute adjustments |
| Payment.completed worker/outbox matrix | Backend worker/outbox targeted pytest plus task-worker targeted pytest, recorded in `docs/evidence/partner-attribution/downstream-sql-e2e-latest.json` | Exit 0; backend 11 tests passed and task-worker 6 tests passed, covering duplicate webhook serialization, outbox publication, concurrent worker claim-once behavior, retry/dead-letter, internal runner auth, schedule/queue contract, and dedicated worker secret handling |

Local repository evidence now covers the browser-facing partner attribution
capture path, backend state transitions, generated contracts, migration
rollback/reapply behavior, PostgreSQL constraints/concurrency, durable
payment.completed outbox/worker behavior, settlement, statements, and
refund/dispute adjustments. The browser SQL smoke uses local DNS mapping for
the canonical public host; the final external customer redirect can land on a
Chrome connection-refused page after capture, while persisted capture SQL state
and the HttpOnly cookie are asserted as the pass criteria. The downstream
revenue path is proven by the separate matrix in
`docs/evidence/partner-attribution/downstream-sql-e2e-latest.json`.

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

- The partner-attribution delivery range `55af4938^..HEAD` contains no tracked
  changes under `cybervpn_mobile/`, `apps/desktop-client/`, or
  `apps/browser-extension/`.
- The broader recorded merge-base diff
  `d06d92a5753e4b6470a3d0dab4c526589a0607b3..HEAD` includes earlier desktop
  stabilization commits already present before the partner-attribution delivery
  range. Those desktop changes are not partner-attribution implementation
  evidence and were not part of the final stabilization slice.
- No `cybervpn_mobile/` or `apps/browser-extension/` tracked changes exist in
  the recorded merge-base diff.
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
