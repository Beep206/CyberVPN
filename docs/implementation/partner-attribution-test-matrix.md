# Partner Attribution Test Matrix

Task: `PARTNER-ATTRIBUTION-HARDENING`

Status: Verified for the repository-controlled gates listed below. The browser
capture slice is covered by the local browser-plus-SQL smoke evidence at
`docs/evidence/partner-attribution/browser-sql-e2e-latest.json`. The downstream
claim, quote, order, payment.completed outbox/worker, earning, hold, statement,
payout dry-run, refund, and dispute adjustment slice is covered by
`docs/evidence/partner-attribution/downstream-sql-e2e-latest.json`.

## Final Required Gates

| Area | Command | Result |
| --- | --- | --- |
| Backend lint | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret .venv/bin/python -m ruff check .` from `backend/` | Passed, exit 0 |
| Backend format | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret .venv/bin/python -m ruff format --check .` from `backend/` | Passed, exit 0, 1465 files already formatted |
| Backend typecheck | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret .venv/bin/python -m mypy src --ignore-missing-imports --no-strict-optional` from `backend/` | Passed, exit 0, no issues in 1032 source files |
| Backend full suite | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_REDIS_URL=redis://127.0.0.1:6380/15 .venv/bin/python -m pytest tests -v --tb=short` from `backend/` | Passed, exit 0, 2230 passed, 79 skipped, coverage 79.68% |
| OpenAPI/generated clients | `PYTHON_BIN=backend/.venv/bin/python PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret bash scripts/check-generated-artifacts.sh` from repo root | Passed, exit 0, backend OpenAPI plus frontend/admin/partner generated API types and i18n bundles are in sync |
| Clean migration cycle | Clean PostgreSQL database: `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head` | Passed, exit 0; upgraded to `20260622_partner_owner_ranges`, downgraded to `20260621_partner_slug_required`, re-upgraded to head |
| PostgreSQL partner attribution/commission tests | `CYBERVPN_TEST_POSTGRES_URL=<clean-temp-postgres> .venv/bin/python -m pytest tests/integration/test_partner_attribution_claim_postgres.py tests/integration/test_partner_commission_contracts_migration_postgres.py -q --tb=short --no-cov` from `backend/` | Passed, exit 0, reached 100% |
| Previously unstable backend group | `pytest tests/integration/api/v1/auth/test_telegram_miniapp_flow.py tests/integration/test_auth_realm_sessions.py tests/integration/test_passkey_webauthn_api.py tests/integration/test_reporting_outbox.py tests/integration/api/v1/codes/test_codes_system_flows.py tests/load/test_helix_canary_evidence_budget.py tests/e2e/test_all_endpoints.py tests/integration/test_service_access_observability.py tests/security/test_jwt_revocation.py -q --tb=short --no-cov` from `backend/` | Passed, exit 0 |
| Pip-equivalent backend typecheck | Temporary clean venv, `pip install -e '.[dev]'`, then `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret mypy src/ --ignore-missing-imports --no-strict-optional` from `backend/` | Passed, exit 0, no issues in 1032 source files |
| Frontend route regression | `npm exec -w frontend -- vitest run 'src/app/p/[publicToken]/route.test.ts'` from repo root | Passed, exit 0, 1 file and 7 tests passed; covers spoofed forwarding header stripping, `pat` removal from backend `source_path`, and production Node runtime security behavior when public app env is `staging` |
| Frontend i18n | `npm run prepare:i18n -w frontend` from repo root | Passed, exit 0, generated 39 locale bundles |
| Frontend lint | `npm run lint -w frontend` from repo root | Passed, exit 0; one existing warning remains in `frontend/src/app/[locale]/miniapp/profile/page.tsx` |
| Frontend typecheck | `npm exec -w frontend -- tsc --noEmit` from repo root | Passed, exit 0 |
| Frontend full Vitest | `npm run test:run -w frontend` from repo root | Passed, exit 0, 196 files passed, 1 skipped; 1366 tests passed, 7 skipped |
| Frontend production build | `NEXT_TELEMETRY_DISABLED=1 npm run build -w frontend` from repo root | Passed, exit 0, Next production build compiled, typechecked, generated 3522 static pages, and completed successfully |
| Browser SQL E2E | `CYBERVPN_E2E_REDIS_URL=redis://127.0.0.1:6380/15 backend/.venv/bin/python scripts/testing/partner_attribution_browser_sql_evidence.py --evidence docs/evidence/partner-attribution/browser-sql-e2e-latest.json` from repo root | Passed, exit 0; Chrome hit canonical `/p/{public_slug}` through local Next, backend capture persisted one session, one touchpoint, one outbox event, and no attacker `pat` in `source_path`; tracked evidence stores structured counters instead of browser DOM or raw log tails |
| Downstream revenue-path matrix | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_POSTGRES_URL=postgresql+asyncpg://postgres:[REDACTED]@127.0.0.1:6767/postgres .venv/bin/python -m pytest tests/integration/test_quote_checkout_sessions.py::test_postgres_concurrent_quote_and_claim_routes_share_single_pending_attribution tests/integration/test_order_attribution_resolution_postgres.py::test_postgres_concurrent_order_attribution_resolve_returns_single_result tests/e2e/test_phase4_settlement_foundations.py::test_phase4_settlement_foundations_end_to_end tests/integration/test_settlement_adjustments.py::test_refund_and_dispute_create_typed_settlement_side_effects tests/integration/test_partner_statement_lifecycle.py::test_partner_statement_lifecycle_close_reopen_and_adjustments -q --tb=short --no-cov --continue-on-collection-errors` from `backend/` | Passed, exit 0, 5 tests passed; covers PostgreSQL claim/quote race, PostgreSQL order attribution race, settlement E2E, statement lifecycle, refund/dispute adjustments |
| Payment.completed worker/outbox matrix | `PAYMENT_SETTLEMENT_WORKER_SECRET=codex-local-secret REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_REDIS_URL=redis://127.0.0.1:6380/15 CYBERVPN_TEST_POSTGRES_URL=postgresql+asyncpg://postgres:[REDACTED]@127.0.0.1:6767/postgres .venv/bin/python -m pytest tests/integration/test_partner_commission_contracts_migration_postgres.py::test_payment_completed_partner_earning_policy_failure_retries_without_cash_artifacts tests/integration/test_partner_commission_contracts_migration_postgres.py::test_payment_completed_partner_earning_concurrent_workers_claim_publication_once tests/integration/test_partner_commission_contracts_migration_postgres.py::test_payment_completed_partner_earning_retry_exhaustion_dead_letters_with_reconciliation_event tests/integration/test_payment_webhook_concurrency_postgres.py::test_postgres_paid_webhook_serializes_duplicate_invoice_side_effects tests/integration/api/v1/payments/test_payment_flows.py::TestPaymentInternalPartnerEarnings tests/unit/application/use_cases/test_payment_attempt_completed_publication.py::test_completed_order_payment_attempt_publishes_payment_completed_after_attempt_exists tests/unit/application/use_cases/test_post_payment_policy_fail_closed.py::test_payment_completed_worker_uses_order_amount_not_tampered_payment_metadata tests/contract/test_payment_completed_partner_earnings_internal_contract.py -q --tb=short --no-cov --continue-on-collection-errors` from `backend/` | Passed, exit 0, 11 tests passed; covers duplicate webhook serialization, durable payment.completed publication, concurrent worker claim-once behavior, retry/dead-letter/reconciliation, dedicated internal runner secret, and OpenAPI/generated-client exclusion |
| Task-worker boundary matrix | `python -m pytest services/task-worker/tests/test_payments.py::test_partner_earning_from_payment_worker_calls_internal_backend_job services/task-worker/tests/test_payments.py::test_partner_earning_from_payment_worker_fails_without_backend_config services/task-worker/tests/test_payments.py::test_partner_earning_from_payment_worker_skips_when_explicitly_disabled services/task-worker/tests/test_payments.py::test_partner_earning_from_payment_task_contract_and_schedule services/task-worker/tests/test_payments.py::test_partner_earning_backend_client_uses_dedicated_worker_secret services/task-worker/tests/test_payments.py::test_partner_earning_backend_client_final_request_excludes_telegram_secret -q --tb=short --continue-on-collection-errors` from repo root | Passed, exit 0, 6 tests passed; covers task-worker scheduling, payments queue/retry policy, internal backend call, retryable misconfiguration, disabled skip path, and no Telegram secret forwarding |
| GitHub Backend CI | GitHub Actions Backend CI run `28112021874` on SHA `5fa1adf9a71c8d375dd86cc8e037a9d5e84ec860` | Passed, all backend jobs successful |
| Remote parity | `git ls-remote` for GitHub and GitLab `main` plus local `git rev-parse HEAD` | Recorded in `.codex/current-task.json` and the delivery response after the final code/evidence commit is pushed |

## Business-State Coverage

| Business behavior | Evidence |
| --- | --- |
| Public capture idempotency and duplicate touchpoint/session prevention | Covered by partner attribution integration and PostgreSQL-specific claim tests in the full backend suite and dedicated Postgres run |
| Real PostgreSQL concurrency and uniqueness | Covered by `test_partner_attribution_claim_postgres.py` on a clean migrated PostgreSQL database |
| Partner commission contract migration and immutable terms | Covered by `test_partner_commission_contracts_migration_postgres.py` on a clean migrated PostgreSQL database |
| Generated API contract synchronization | Covered by `scripts/check-generated-artifacts.sh`; no generated drift after regeneration |
| Migration upgrade, rollback, and reapply | Covered by clean PostgreSQL `upgrade head`, `downgrade -1`, `upgrade head` cycle |
| Payment/order/reporting/service-access side effects | Covered by full backend suite, including reporting outbox, service access observability, order attribution, renewal ownership, settlement, and partner statement tests |
| Browser public partner link capture | Covered by `scripts/testing/partner_attribution_browser_sql_evidence.py`, which upgrades a temporary PostgreSQL database to Alembic head, seeds a durable partner link, drives Chrome through local Next using canonical `cyber-vpn.net`, and asserts cookie plus persisted SQL state |
| Claim, commercial binding, quote snapshot, and order attribution | Covered by `downstream-sql-e2e-latest.json` matrix: PostgreSQL quote/claim race asserts one active binding and no cookie token in quote snapshot; PostgreSQL order attribution race asserts one `order_attribution_results` row and one finalized outbox event |
| Durable payment.completed outbox and task-worker boundary | Covered by `downstream-sql-e2e-latest.json` matrix: backend tests assert duplicate webhook serialization, payment.completed publication, concurrent worker claim-once behavior, retry/dead-letter behavior, and internal runner authorization; task-worker tests assert queue/schedule contract and dedicated worker secret use |
| Settlement, statement, payout dry-run, refund, and dispute adjustments | Covered by `downstream-sql-e2e-latest.json` matrix: settlement E2E and statement/adjustment tests assert earning events, holds, statements, payout instructions/executions, reconciliation pack, refund clawback, dispute clawback, and reserve release adjustments |
| JWT/session/revocation safety | Covered by full backend security tests and explicit bounded clock-skew positive/negative tests |

## Skips And External Runtime Evidence

- The full backend suite contains 79 expected skips for provider-backed or
  externally credentialed E2E flows and Postgres-only tests that are run in the
  separate clean Postgres command above.
- Browser-facing partner attribution capture is covered by local Chrome smoke
  plus SQL assertions. The smoke deliberately follows the production canonical
  public host while resolving it to local Next, so the final external customer
  redirect may render a Chrome connection-refused page after capture; persisted
  SQL state and the HttpOnly cookie are the pass criteria.
- The remaining revenue path is not claimed from the browser-smoke alone. It is
  covered by the downstream matrix in
  `docs/evidence/partner-attribution/downstream-sql-e2e-latest.json`, including
  PostgreSQL concurrency tests and task-worker boundary tests.
