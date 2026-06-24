# Partner Attribution Test Matrix

Task: `PARTNER-ATTRIBUTION-HARDENING`

Status: Verified for the repository-controlled gates listed below. Browser
vertical acceptance for the remaining user-facing checks was supplied as user
runtime evidence on 2026-06-24.

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

## Business-State Coverage

| Business behavior | Evidence |
| --- | --- |
| Public capture idempotency and duplicate touchpoint/session prevention | Covered by partner attribution integration and PostgreSQL-specific claim tests in the full backend suite and dedicated Postgres run |
| Real PostgreSQL concurrency and uniqueness | Covered by `test_partner_attribution_claim_postgres.py` on a clean migrated PostgreSQL database |
| Partner commission contract migration and immutable terms | Covered by `test_partner_commission_contracts_migration_postgres.py` on a clean migrated PostgreSQL database |
| Generated API contract synchronization | Covered by `scripts/check-generated-artifacts.sh`; no generated drift after regeneration |
| Migration upgrade, rollback, and reapply | Covered by clean PostgreSQL `upgrade head`, `downgrade -1`, `upgrade head` cycle |
| Payment/order/reporting/service-access side effects | Covered by full backend suite, including reporting outbox, service access observability, order attribution, renewal ownership, settlement, and partner statement tests |
| JWT/session/revocation safety | Covered by full backend security tests and explicit bounded clock-skew positive/negative tests |

## Skips And External Runtime Evidence

- The full backend suite contains 79 expected skips for provider-backed or
  externally credentialed E2E flows and Postgres-only tests that are run in the
  separate clean Postgres command above.
- User runtime checks on 2026-06-24 supplied the remaining browser-facing
  vertical evidence for the acceptance criteria the local environment did not
  re-run with Playwright.
