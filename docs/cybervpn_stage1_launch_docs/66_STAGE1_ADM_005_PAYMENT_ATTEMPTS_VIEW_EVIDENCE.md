# Stage 1 Payment Attempts View Evidence

> Date: 2026-05-04  
> Backlog ID: `S1-ADM-005`  
> Scope: local backend/admin API and reusable frontend support/finance payment-attempt view contract  
> Status: local evidence complete; deployed admin UI/API persona proof remains required before go-live

## Purpose

`S1-ADM-005` proves that support and finance can inspect payment-attempt status during Controlled Public Beta without exposing provider payloads, idempotency keys, payment URLs, raw external references or request snapshots.

The S1 boundary is intentionally split:

- global `/admin/payment-attempts` and `/admin/payment-attempts/{payment_attempt_id}` require `PAYMENT_READ`, so finance/admin roles can inspect the finance-safe list/detail view;
- scoped `/admin/mobile-users/{user_id}/payment-attempts` is available only to support, finance and admin/owner roles, so support can inspect a specific customer's safe payment state;
- support visibility hides internal `payment_id`, wallet/gateway breakdown and all raw provider/request fields;
- finance visibility still uses a safe response shape and never exposes provider snapshots, raw external references, checkout URLs or idempotency keys.

## Implementation Summary

| Area | Change |
|---|---|
| Backend route | Added `backend/src/presentation/api/v1/admin/payment_attempts.py` |
| Router wiring | Included the new admin payment-attempt router in `backend/src/presentation/api/v1/router.py` |
| Finance API | `GET /api/v1/admin/payment-attempts` and `GET /api/v1/admin/payment-attempts/{id}` require `PAYMENT_READ` |
| Support API | `GET /api/v1/admin/mobile-users/{user_id}/payment-attempts` allows only support, finance, admin, super-admin and owner/super-admin roles |
| Safe serialization | Response excludes `external_reference`, `idempotency_key`, `provider_snapshot`, `request_snapshot` and `invoice.payment_url` |
| Review signals | Response includes S1 review state: `ok`, `manual_review`, `alert_15m`, `p1_escalation`, `p0_blocker` |
| Frontend model | Added reusable role gates, endpoint builders and safe summary helpers in `customer-payment-attempts-view-model.ts` |
| Frontend panel | Added `CustomerPaymentAttemptsView` for support/finance payment status inspection |

## Safe Response Contract

| Field group | Support view | Finance view |
|---|---|---|
| Payment status | Visible | Visible |
| Provider name/status | Visible, sanitized | Visible, sanitized |
| Displayed amount/currency | Visible | Visible |
| Wallet/gateway split | Hidden | Visible |
| Internal `payment_id` | Hidden | Visible only if linked |
| Raw provider external reference | Hidden; one-way fingerprint only | Hidden; one-way fingerprint only |
| Idempotency key | Hidden; boolean presence only | Hidden; boolean presence only |
| Provider snapshot/request snapshot | Hidden | Hidden |
| Checkout/payment URL | Hidden | Hidden |
| Review/escalation state | Visible | Visible |

## Local Proof Matrix

| Check | Local result |
|---|---|
| Support serializer hides `payment_id`, wallet/gateway split, raw external reference, idempotency key, provider snapshot, request snapshot and payment URL | Passed |
| Finance serializer shows safe wallet/gateway breakdown while still hiding provider/request raw fields | Passed |
| Support/finance/admin role gate allows only approved roles for scoped customer view | Passed |
| Operator/viewer cannot access scoped payment-attempt view | Passed |
| FastAPI route test proves scoped support response hides raw provider/payment fields | Passed |
| Frontend role helpers match backend intent for support and finance views | Passed |
| Frontend endpoint builders use approved admin paths | Passed |
| Frontend safe summary does not propagate accidental raw provider fields | Passed |
| Frontend panel renders support review state and blocks operator/viewer roles | Passed |

## Commands and Results

| Check | Command | Result |
|---|---|---|
| Backend lint | `cd backend && uv run ruff check src/presentation/api/v1/admin/payment_attempts.py src/presentation/api/v1/router.py tests/security/test_stage1_admin_payment_attempts_view.py` | `All checks passed!` |
| Backend tests | `cd backend && uv run pytest tests/security/test_stage1_admin_payment_attempts_view.py tests/security/test_stage1_admin_rbac_matrix.py -q --no-cov` | `10 passed` |
| Frontend tests | `cd frontend && npm run test:run -- src/widgets/admin-support/__tests__/customer-payment-attempts-view-model.test.ts src/widgets/admin-support/__tests__/customer-payment-attempts-view.test.tsx` | `8 passed` |
| Frontend lint | `cd frontend && npm run lint -- src/widgets/admin-support/customer-payment-attempts-view-model.ts src/widgets/admin-support/customer-payment-attempts-view.tsx src/widgets/admin-support/__tests__/customer-payment-attempts-view-model.test.ts src/widgets/admin-support/__tests__/customer-payment-attempts-view.test.tsx` | Passed |
| Backend dependency consistency | `cd backend && uv run pip check` | `No broken requirements found.` |
| Backend dependency audit | `cd backend && uvx pip-audit --progress-spinner off` | `No known vulnerabilities found` |
| Frontend dependency audit | `cd frontend && npm audit --omit=dev` | Existing moderate `postcss` advisory through `next`; `npm audit fix --force` would downgrade/break Next, so this remains tracked under `TD-S1-SEC-001` |
| Diff whitespace check | `git diff --check -- <S1-ADM-005 changed files>` | Passed |

## Source Notes

| Source | Use |
|---|---|
| FastAPI dependencies: <https://fastapi.tiangolo.com/tutorial/dependencies/> | Confirmed dependency callable pattern for role-gated admin routes |
| SQLAlchemy ORM select guide: <https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html> | Confirmed ORM `select()`/`join()`/`execute()` query shape |
| Pydantic models: <https://docs.pydantic.dev/latest/concepts/models/> | Confirmed response model usage for safe schema serialization |
| Lucide React: <https://lucide.dev/guide/react> | Confirmed imported standalone React icon components are supported |

## Boundaries and Remaining Evidence

This closes the local S1 admin payment-attempt view contract. It does not close all paid-beta/go-live evidence.

Remaining before paid beta/go-live:

- deployed admin UI/API persona proof for support, finance, admin and denied operator/viewer users;
- staging/prod screenshots or API transcripts through `admin.cyber-vpn.net`;
- real provider payment attempts from at least one enabled payment path;
- provider dashboard/callback reconciliation proof showing safe fields match real payment state;
- real paid-but-no-access/orphan queue and alert delivery evidence;
- audit log evidence for any future manual payment/support actions attached to this view.

## Security Notes

- No production payment provider credentials, bot token, user payment record or Remnawave credential was used.
- No Docker containers were started for this task.
- The response intentionally carries a one-way external-reference fingerprint only; it is not reversible and is not a provider credential.
- `request_snapshot` and `provider_snapshot` remain backend-only and are not returned to admin/support UI surfaces.

## Next ID

Next ID completed after this file: `S1-ADM-006` in `67_STAGE1_ADM_006_MANUAL_SUBSCRIPTION_OPS_EVIDENCE.md`.
