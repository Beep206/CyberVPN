> CyberVPN Stage 1 Evidence
> ID: S1-PAY-010
> Date: 2026-05-08
> Scope: local wallet/payment history verification, customer scoping, safe UI output and active execution-step revalidation.

# S1-PAY-010 Wallet/Payment History Evidence

## Result

`S1-PAY-010` is completed locally.

CyberVPN now has an explicit S1-safe wallet/payment-history contract:

- `/api/v1/payments/history` returns payment history for the authenticated customer only;
- frontend customer payment-history calls no longer accept or send `user_uuid`;
- raw provider fields are not rendered in the customer payment-history timeline;
- wallet withdrawal/payout backend request creation, UI and withdrawal data fetches are disabled by default for S1;
- clean database seed and runtime fallback set `wallet.withdrawal_enabled=false`;
- the Mini App wallet and legacy dashboard wallet client use the same default-off withdrawal UI switch;
- withdrawal/payout UI can only appear when `NEXT_PUBLIC_STAGE1_WALLET_WITHDRAWALS_ENABLED=true` is set intentionally.

This closes the local implementation/test requirement for safe customer payment history. It does not enable live provider payments and does not replace deployed browser screenshots, provider callback samples, or staging/production evidence.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-009`. The customer payment-history contract, frontend raw-provider-field non-rendering, withdrawal default-off policy and backend fail-closed config behavior still match the S1 B2C launch boundary.

## S1 customer data contract

| Surface | S1 rule |
|---|---|
| Backend payment history | Use authenticated customer identity from `get_current_mobile_user_id`; do not trust customer-supplied `user_uuid` |
| Frontend payment-history client | Accept `limit` and `offset`; no `user_uuid` parameter in the customer API helper |
| Customer UI | Render amount, currency, provider, status and created date only |
| Raw provider fields | Do not render `external_id`, `payment_url`, `idempotency_key`, provider snapshots or request snapshots |
| Wallet withdrawals | Backend request creation, UI and data fetches are disabled by default in S1; payout flows are not part of S1 B2C launch |
| Admin/support payment attempts | Covered separately by `66_STAGE1_ADM_005_PAYMENT_ATTEMPTS_VIEW_EVIDENCE.md` |

## Implementation summary

| File | Change |
|---|---|
| `backend/src/presentation/api/v1/payments/routes.py` | `GET /api/v1/payments/history` is now authenticated-customer scoped and no longer exposes admin-style `user_uuid` filtering |
| `backend/tests/integration/api/v1/wallet/test_wallet_payment_flows.py` | Added cross-user payment-history proof and raw provider field non-disclosure assertions |
| `backend/tests/integration/api/v1/payments/test_payment_flows.py` | Added authenticated customer scoping proof for the payment-history endpoint |
| `frontend/src/lib/api/payments.ts` | Added a customer-safe payment-history params alias backed by the regenerated OpenAPI contract with no `user_uuid` |
| `backend/docs/api/openapi.json` | Regenerated OpenAPI so `/api/v1/payments/history` exposes only `offset` and `limit` query params |
| `frontend/src/lib/api/generated/types.ts` | Regenerated frontend API types from the updated OpenAPI contract |
| `frontend/src/lib/api/__tests__/payments.test.ts` | Verified payment-history query params do not include `user_uuid` |
| `frontend/src/widgets/billing-cabinet/wallet-cabinet-dashboard.tsx` | Withdrawal form, withdrawal history, withdrawal fetches and pending-withdrawal metric are gated behind a default-off S1 switch |
| `frontend/src/widgets/billing-cabinet/__tests__/billing-cabinet-dashboards.test.tsx` | Verified default-off withdrawal UI/data fetches and raw provider-field non-rendering in the payment-history dashboard |
| `frontend/src/app/[locale]/miniapp/wallet/page.tsx` | Mini App wallet withdrawal action and bottom sheet are hidden unless the S1 switch is enabled |
| `frontend/src/app/[locale]/miniapp/wallet/__tests__/page.test.tsx` | Verified Mini App withdrawal UI is absent by default |
| `frontend/src/app/[locale]/(dashboard)/wallet/components/WalletClient.tsx` | Legacy wallet client withdrawal button/modal are hidden unless the S1 switch is enabled |
| `frontend/src/shared/lib/stage1-growth-flags.ts` | Added `isStage1WalletWithdrawalUiEnabled()` |
| `frontend/src/shared/lib/__tests__/surface-policy.test.ts` | Verified the withdrawal UI switch is false by default and only true for explicit `true` env |
| `backend/src/application/services/config_service.py` | Wallet withdrawal runtime fallback now fails closed when `wallet.withdrawal_enabled` is missing |
| `backend/alembic/versions/20260210_add_codes_wallet_foundation.py` | Clean database seed now sets `wallet.withdrawal_enabled=false` for S1 |
| `backend/tests/security/test_stage1_wallet_withdrawal_policy.py` | Added fail-closed proof for missing wallet withdrawal config |
| `backend/tests/conftest.py` | Local stale Docker DB bootstrap now adds missing `mobile_users.notification_prefs` before integration tests |

## Verification

| Check | Command | Result |
|---|---|---|
| Backend payment-history integration tests | `cd backend && PYENV_VERSION=3.13.11 uv run pytest --no-cov tests/integration/api/v1/wallet/test_wallet_payment_flows.py::TestPaymentHistory::test_get_payment_history tests/integration/api/v1/payments/test_payment_flows.py::TestPaymentHistory::test_get_payment_history tests/security/test_stage1_wallet_withdrawal_policy.py -q` | `3 passed` with local Docker DB/Redis running |
| Backend lint | `cd backend && uv run ruff check src/presentation/api/v1/payments/routes.py tests/integration/api/v1/wallet/test_wallet_payment_flows.py tests/integration/api/v1/payments/test_payment_flows.py` | `All checks passed!` |
| Backend withdrawal default-off regression | `cd backend && PYENV_VERSION=3.13.11 uv run pytest --no-cov tests/security/test_stage1_wallet_withdrawal_policy.py tests/integration/api/v1/wallet/test_wallet_payment_flows.py::TestWalletFlow::test_withdrawal_requests_are_disabled_by_default_for_s1 tests/integration/api/v1/wallet/test_wallet_payment_flows.py::TestWalletFlow::test_withdrawal_below_minimum tests/integration/api/v1/wallet/test_wallet_payment_flows.py::TestWalletFlow::test_withdrawal_insufficient_balance tests/integration/api/v1/wallet/test_wallet_payment_flows.py::TestPaymentHistory::test_get_payment_history tests/integration/api/v1/payments/test_payment_flows.py::TestPaymentHistory::test_get_payment_history -q` | `6 passed` with local Docker DB/Redis running |
| Backend withdrawal/default-off lint | `cd backend && uv run ruff check tests/conftest.py tests/security/test_stage1_wallet_withdrawal_policy.py tests/integration/api/v1/wallet/test_wallet_payment_flows.py src/application/services/config_service.py alembic/versions/20260210_add_codes_wallet_foundation.py` | `All checks passed!` |
| Legacy admin withdrawal observation | `cd backend && uv run pytest tests/security/test_stage1_wallet_withdrawal_policy.py tests/integration/api/v1/wallet/test_wallet_payment_flows.py::TestWalletFlow::test_complete_wallet_flow tests/integration/api/v1/wallet/test_wallet_payment_flows.py::TestWalletFlow::test_admin_reject_withdrawal -q --no-cov` | Expected non-S1 legacy admin endpoints returned `404` under admin host protection; not a S1-PAY-010 blocker |
| OpenAPI export | `cd backend && uv run python scripts/export_openapi.py` | OpenAPI 3.1.0 exported to `backend/docs/api/openapi.json` |
| Frontend API type generation | `cd frontend && npm run generate:api-types` | `openapi-typescript` regenerated `frontend/src/lib/api/generated/types.ts`; payment-history query params are `offset` and `limit` only |
| Frontend targeted tests | `cd frontend && npm run test:run -- src/lib/api/__tests__/payments.test.ts src/shared/lib/__tests__/surface-policy.test.ts src/widgets/billing-cabinet/__tests__/billing-cabinet-dashboards.test.tsx src/app/[locale]/miniapp/wallet/__tests__/page.test.tsx` | `4 passed`, `48 passed` |
| Frontend lint | `cd frontend && npm run lint -- src/lib/api/payments.ts src/shared/lib/stage1-growth-flags.ts src/shared/lib/__tests__/surface-policy.test.ts src/widgets/billing-cabinet/wallet-cabinet-dashboard.tsx src/widgets/billing-cabinet/__tests__/billing-cabinet-dashboards.test.tsx src/app/[locale]/miniapp/wallet/page.tsx src/app/[locale]/miniapp/wallet/__tests__/page.test.tsx 'src/app/[locale]/(dashboard)/wallet/components/WalletClient.tsx' src/lib/api/generated/types.ts` | Passed with one expected ESLint warning that generated `types.ts` is ignored by project ignore patterns |
| Python dependency check | `cd backend && uv run pip check` | `No broken requirements found.` |
| Python vulnerability audit | `PYENV_VERSION=3.13.11 pip-audit --skip-editable backend` | `No known vulnerabilities found` |
| Frontend/root dependency audit | `npm audit --omit=dev --audit-level=high` | No high/critical blocker; existing low/moderate advisories remain tracked outside `S1-PAY-010` |
| Secret marker scan on touched files | `rg -n '(?i)(api[_-]?key\|secret\|token\|authorization\|password\|private[_-]?key\|payment_url\|checkout_url\|idempotency_key)' <S1-PAY-010 touched files>` | Findings are documentation terms, test fixture placeholders and raw-field sentinel strings only; no real secret material found |
| Dangerous pattern scan on touched files | `rg -n '(?i)(eval\(\|exec\(\|shell=True\|subprocess\|os\.system\|raw sql\|text\()' <S1-PAY-010 touched files>` | No `eval`, shell execution or unsafe user-input SQL; matches are static Alembic/test-bootstrap DDL via SQLAlchemy `text()` |
| Whitespace check | `git diff --check -- <S1-PAY-010 files>` | Passed |
| Local container cleanup | `cd infra && docker compose stop remnawave-db remnawave-redis && docker compose ps` | DB/Redis stopped; no running Compose services listed |

## 2026-05-08 Verification

| Check | Result |
|---|---|
| Local Docker DB/Redis availability | PASS: `remnawave-db` and `remnawave-redis` were started healthy for integration tests |
| Initial backend run before DB/Redis start | PARTIAL: 1 passed, 2 skipped because PostgreSQL on `localhost:6767` was unavailable |
| Backend payment-history/customer-scope pack with DB/Redis | PASS: 3 passed |
| Backend withdrawal default-off regression with DB/Redis | PASS: 6 passed |
| Backend ruff check on S1-PAY-010 scope | PASS |
| Frontend payment-history/withdrawal UI tests | PASS: 4 files passed, 48 tests passed |
| Frontend payment API test after whitespace cleanup | PASS: 1 file passed, 18 tests passed |
| Frontend lint on S1-PAY-010 scope | PASS with one expected generated `types.ts` ignore warning |
| Raw provider field scan/fixture review | PASS: tests verify `external_id`, `payment_url`, `idempotency_key`, provider snapshots and request snapshots are not rendered in customer history |
| Customer-supplied `user_uuid` bypass proof | PASS: backend test sends another user's `user_uuid` query param and still returns only the authenticated customer history |
| Secret marker scan on touched files | PASS: no live credentials found; policy words, function parameter names and synthetic test fixtures excluded |
| Static dangerous-pattern scan on touched files | PASS: no unsafe runtime matches |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical threshold; existing low/moderate advisories remain outside this task |
| `git diff --check` on touched docs/code | PASS |
| Docker runtime cleanup | PASS: `remnawave-db` and `remnawave-redis` stopped after verification |

## Security Review Notes

- Customer payment history is scoped to the authenticated customer identity and does not trust a query-provided `user_uuid`.
- Customer-facing payment-history responses and UI avoid raw provider references, payment URLs, idempotency keys, provider snapshots and request snapshots.
- Wallet withdrawal/payout creation and UI remain default-off for S1 and fail closed when `wallet.withdrawal_enabled` is absent.
- Backend dependency audit passed with no known vulnerabilities.
- NPM high/critical audit threshold passed; low/moderate workspace advisories are tracked outside this wallet/payment-history task and were not fixed with breaking/downgrade changes.
- Static secret and dangerous-pattern scans found no live credentials or unsafe runtime patterns in the touched S1-PAY-010 scope.

## Evidence notes

- The backend test intentionally includes a second user's payment with a raw external reference and proves it is not returned to the current customer.
- Wallet withdrawals now fail closed at backend config level as well as UI level: missing config and clean DB seed both keep `wallet.withdrawal_enabled=false`.
- The frontend test intentionally includes `external_id`, `idempotency_key`, `payment_url`, `provider_snapshot` and `request_snapshot` sentinel values and proves the payment-history dashboard does not render them.
- TanStack Query withdrawal fetch gating uses the documented `enabled` option pattern for disabling queries until a condition is true: <https://tanstack.com/query/v5/docs/react/guides/disabling-queries>.
- A stale local Docker PostgreSQL volume produced an Alembic duplicate-column conflict during this task when trying to run migrations against the old dev volume. The test bootstrap was extended for the missing `mobile_users.notification_prefs` column needed by local integration tests, but the stale local volume still must not be treated as staging/production truth.

## Remaining before paid beta/go-live

| Requirement | Why it remains open |
|---|---|
| Deployed UI screenshots | Local jsdom tests prove safe rendering, but deployed browser screenshots are still needed for RC/go-live evidence |
| Real provider callback/payment samples | Local tests do not prove provider-side payment history semantics |
| Provider-specific payment attempts redaction | Covered by admin/support evidence and provider readiness tasks before enabling paid paths |
| Reconciliation job | Completed locally in `83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md`; real provider/admin queue/alert evidence remains |
| Provider placeholder replacement | Local guardrail completed in `84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md`; real provider samples still required for each enabled provider |

## Next ID

Next ID superseded by `108_STAGE1_PAY_011_TELEGRAM_STARS_READINESS_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
