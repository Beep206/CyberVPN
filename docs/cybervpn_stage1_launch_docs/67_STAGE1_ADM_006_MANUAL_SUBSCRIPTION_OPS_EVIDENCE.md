# Stage 1 Manual Subscription Operations Evidence

> Date: 2026-05-04
> Backlog ID: `S1-ADM-006`
> Scope: local backend/admin API and reusable frontend manual subscription grant panel
> Status: local evidence complete; deployed admin persona/UI/API and real Remnawave proof remain required before go-live

## Purpose

`S1-ADM-006` proves that S1 has a controlled manual subscription operation for support escalations and owner/operator recovery cases.

The operation is intentionally narrow:

- it creates or extends Remnawave-backed VPN access for a customer;
- it requires `SUBSCRIPTION_CREATE`, so owner/super-admin/admin/operator can execute it, while support/finance/viewer cannot;
- it requires an operator reason;
- it writes a required audit event: `customer_subscription_manual_granted`;
- it never returns subscription URL, config links, short UUID or protocol secrets in the API response, UI summary or audit details;
- it is for manual grants/extension only, not promo/gift/referral public flows or checkout discounts.

Support can escalate a case for a manual grant, but the actual grant remains restricted to the subscription-create permission in S1.

## Implementation Summary

| Area | Change |
|---|---|
| Backend use case | Added `backend/src/application/use_cases/subscriptions/stage1_manual_subscription.py` |
| Remnawave adapter | Added `backend/src/infrastructure/remnawave/stage1_manual_subscription_gateway.py` |
| Admin API | Added `POST /api/v1/admin/mobile-users/{user_id}/subscription/manual-grant` in `customer_support.py` |
| Role gate | Endpoint requires `Permission.SUBSCRIPTION_CREATE` |
| Audit manifest | Added `customer_subscription_manual_granted` to required S1 admin audit actions |
| Safe response | Added `AdminCustomerManualSubscriptionResponse` without config links or raw subscription URLs |
| Frontend model | Added role gates, endpoint builder, request validation and safe summary helpers |
| Frontend panel | Added reusable `CustomerManualSubscription` admin-support component |

## Safe Operation Contract

| Contract item | S1 behavior |
|---|---|
| Allowed roles | `owner/super_admin`, `super_admin`, `admin`, `operator` |
| Denied roles | `support`, `finance`, `viewer` |
| Duration | 1-365 days |
| Device limit | 1-10 devices |
| Traffic limit | Positive bytes or unlimited/null |
| Existing active subscription | Extends from current upstream expiry |
| Expired or missing subscription | Grants from request time |
| Customer local state | Stores/updates Remnawave UUID and subscription URL internally only |
| API/UI response | Safe metadata only: action, UUID, status, operation, dates, duration |
| Audit details | Reason length and safe metadata only |
| Config delivery | Marked as required; actual delivery remains a separate controlled user/support flow |

## Local Proof Matrix

| Check | Local result |
|---|---|
| Manual subscription role helper matches backend `SUBSCRIPTION_CREATE` permission | Passed |
| Support/finance/viewer cannot use manual subscription operation | Passed |
| Existing active subscription extends from current upstream expiry | Passed |
| Missing/expired subscription grants from request time | Passed |
| Request validation rejects short reason, duration over 365, device limit over 10 and non-positive traffic limits | Passed |
| Remnawave gateway creates a deterministic non-PII username for new manual grants | Passed |
| Remnawave gateway updates existing users and activates access | Passed |
| Admin route updates local Remnawave UUID/subscription URL internally without returning raw URL | Passed |
| Required audit action is written and contains no raw config link/short UUID | Passed |
| Frontend role helper matches backend permission intent | Passed |
| Frontend request builder emits snake_case backend payload | Passed |
| Frontend component blocks denied roles before submit | Passed |
| Frontend component renders safe success summary without raw config fields | Passed |

## Commands and Results

| Check | Command | Result |
|---|---|---|
| Backend lint | `cd backend && uv run ruff check src/application/use_cases/subscriptions/stage1_manual_subscription.py src/infrastructure/remnawave/stage1_manual_subscription_gateway.py src/presentation/api/v1/admin/customer_support.py src/presentation/api/v1/admin/customer_support_schemas.py src/presentation/api/v1/admin/audit.py tests/security/test_stage1_admin_manual_subscription_ops.py tests/security/test_stage1_admin_audit_log.py tests/security/test_stage1_admin_rbac_matrix.py` | `All checks passed!` |
| Backend tests | `cd backend && uv run pytest tests/security/test_stage1_admin_manual_subscription_ops.py tests/security/test_stage1_admin_audit_log.py tests/security/test_stage1_admin_rbac_matrix.py -q --no-cov` | `18 passed` |
| Frontend tests | `cd frontend && npm run test:run -- src/widgets/admin-support/__tests__/customer-manual-subscription-model.test.ts src/widgets/admin-support/__tests__/customer-manual-subscription.test.tsx` | `9 passed` |
| Frontend lint | `cd frontend && npm run lint -- src/widgets/admin-support/customer-manual-subscription-model.ts src/widgets/admin-support/customer-manual-subscription.tsx src/widgets/admin-support/__tests__/customer-manual-subscription-model.test.ts src/widgets/admin-support/__tests__/customer-manual-subscription.test.tsx` | Passed |
| Backend dependency consistency | `cd backend && uv run pip check` | `No broken requirements found.` |
| Backend dependency audit | `cd backend && uvx pip-audit --progress-spinner off` | `No known vulnerabilities found` |
| Frontend dependency audit | `cd frontend && npm audit --omit=dev` | Existing moderate `postcss` advisory through `next`; `npm audit fix --force` would downgrade/break Next, so this remains tracked under `TD-S1-SEC-001` |
| Sensitive-string scan | `rg -n "(?i)(secret|token|password|subscription_url|config|authorization|bearer|api[_-]?key|private key)" <S1-ADM-006 changed files>` | Accepted false positives only: field names and explicit fake test URLs used to prove redaction |
| Dangerous-pattern scan | `rg -n "(eval\\(|innerHTML|dangerouslySetInnerHTML|document\\.write|localStorage|sessionStorage|new Function\\()" <S1-ADM-006 changed files>` | No matches |
| Diff whitespace check | `git diff --check -- <S1-ADM-006 changed files>` | Passed |

## Source Notes

| Source | Use |
|---|---|
| FastAPI dependencies: <https://fastapi.tiangolo.com/tutorial/dependencies/> | Confirmed dependency callable pattern for role-gated admin routes |
| Pydantic fields: <https://docs.pydantic.dev/latest/concepts/fields/> | Confirmed field validation constraints for request schemas |
| SQLAlchemy ORM select guide: <https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html> | Rechecked existing repository/query patterns around admin/mobile-user flows |
| React `useState`: <https://react.dev/reference/react/useState> | Confirmed controlled-form state pattern for the reusable admin panel |
| Lucide React: <https://lucide.dev/guide/react> | Confirmed imported standalone React icon components are supported |

## Boundaries and Remaining Evidence

This closes the local S1 manual subscription operation contract. It does not close all go-live evidence.

Remaining before paid beta/go-live:

- deployed admin UI/API persona proof for owner/super-admin/admin/operator and denied support/finance/viewer roles;
- staging/prod Remnawave proof that manual grant creates and extends real upstream users;
- redacted audit-log retrieval proof from deployed admin domain;
- support escalation evidence showing support can request a grant but cannot execute it directly;
- config delivery/user notification proof after a manual grant;
- rollback/kill-switch procedure if manual grants must be paused;
- alert/support runbook evidence for manual grant failures.

## Security Notes

- No production Remnawave credentials, subscription URL, config link, provider credential, bot token or user secret was added.
- Docker containers were not started for this task.
- Raw subscription URL is stored internally only when Remnawave returns it; the route response, frontend summary and audit details exclude it.
- The frontend does not render upstream exception messages, so raw provider/Remnawave errors cannot leak into the UI.
- Manual grants do not re-enable public promo/gift/referral flows and do not create checkout discounts.

## Next ID

Next ID after `S1-ADM-006` was `S1-ADM-007` - credential regeneration alignment/checkpoint. It is now covered locally in `68_STAGE1_ADM_007_CREDENTIAL_REGENERATION_ADMIN_EVIDENCE.md`.
