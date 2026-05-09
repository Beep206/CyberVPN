> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-04
> Backlog ID: `S1-BE-008`
> Статус: local canonical status/error contract completed; endpoint-by-endpoint adoption and deployed UI/support evidence remain required before go-live.

# S1-BE-008 Status/Error Contract Evidence

## Purpose

Этот документ фиксирует `S1-BE-008`: backend, customer UI, Telegram Mini App, admin/support and worker flows must use one canonical S1 status/error model for auth, payments, provisioning and support.

S1 не должен запускаться с ситуацией, где backend говорит `completed`, UI показывает `active`, support видит `pending`, а пользователь остаётся в `paid-but-no-access`. Для Controlled Public Beta это особенно важно в цепочке:

```text
trial/pay -> Remnawave provisioning -> QR/subscription URL/config ready -> support/admin control
```

## Source References

FastAPI error handling docs: https://fastapi.tiangolo.com/tutorial/handling-errors/

Pydantic model/validation docs: https://pydantic.dev/docs/validation/latest/concepts/validators/

Important rules reflected in this implementation:

- API errors should have stable machine-readable codes, not only free-form text;
- response models should be serializable through FastAPI/Starlette JSON responses;
- validation and state mapping should be explicit enough for tests to fail when enum values change.

## Implementation

Added:

```text
backend/src/presentation/api/shared/stage1_contract.py
backend/tests/security/test_stage1_status_error_contract.py
```

Updated:

```text
backend/src/presentation/api/shared/__init__.py
```

The contract defines:

- `Stage1Surface` for `auth`, `payment`, `provisioning`, `support`, `system`, `validation`;
- `Stage1AccessState` for customer access/subscription state;
- `Stage1PaymentState` for payment/invoice/attempt state;
- `Stage1ProvisioningState` for Remnawave/VPN access readiness;
- `Stage1SupportState` for manual review and ops escalation;
- `Stage1ErrorCode` and `STAGE1_ERROR_MATRIX`;
- `Stage1CanonicalErrorResponse`;
- `Stage1FlowStatusResponse`;
- domain enum mapping tables for current backend statuses.

This is intentionally a contract layer first. Existing legacy endpoints may still return `{"detail": ...}` until touched by S1 implementation tasks, but all new or modified S1 endpoints should use this canonical model.

## Canonical Error Response Shape

```json
{
  "code": "payment_orphan_review_required",
  "message": "Payment was received, but access is not ready yet.",
  "surface": "payment",
  "http_status": 409,
  "user_action": "Support must review and restore access within the S1 orphan-payment SLA.",
  "retryable": true,
  "support_escalation": true,
  "request_id": "req-orphan-test",
  "details": {
    "payment_id": "pay_test",
    "age_hours": 1
  }
}
```

## Canonical S1 Surfaces

| Surface | Owner / usage |
|---|---|
| `auth` | Login, registration, session refresh, 2FA, email verification, OAuth/Telegram identity |
| `payment` | Invoice/payment attempts, provider callbacks, failed/cancelled/expired payments, orphan payment review |
| `provisioning` | Remnawave access creation/update, retry, failed provisioning, reconciliation |
| `support` | Manual support review, ops escalation, resolved cases |
| `system` | Generic backend/system errors and not-found conditions |
| `validation` | Request validation failures |

## Canonical Payment States

| Canonical state | Meaning |
|---|---|
| `not_started` | No invoice/payment flow exists yet |
| `quote_ready` | Checkout quote exists, payment not started |
| `pending` | Provider/payment attempt has been created and is waiting |
| `processing` | Provider is processing the payment |
| `paid` | Final paid/succeeded/completed state |
| `failed` | Payment failed |
| `cancelled` | User/provider cancelled the payment |
| `expired` | Invoice/payment attempt expired |
| `refunded` | Payment was refunded |
| `orphan_review_required` | Paid-but-no-access/manual review case |
| `reconciliation_required` | Provider/backend state mismatch requires review |

Current backend mapping:

| Backend enum | Canonical state |
|---|---|
| `PaymentStatus.PENDING` | `pending` |
| `PaymentStatus.COMPLETED` | `paid` |
| `PaymentStatus.FAILED` | `failed` |
| `PaymentStatus.REFUNDED` | `refunded` |
| `PaymentAttemptStatus.PENDING` | `pending` |
| `PaymentAttemptStatus.PROCESSING` | `processing` |
| `PaymentAttemptStatus.SUCCEEDED` | `paid` |
| `PaymentAttemptStatus.FAILED` | `failed` |
| `PaymentAttemptStatus.EXPIRED` | `expired` |
| `PaymentAttemptStatus.CANCELLED` | `cancelled` |

## Canonical Provisioning States

| Canonical state | Meaning |
|---|---|
| `not_required` | No VPN provisioning is required for this response |
| `queued` | Provisioning job accepted but not started |
| `pending` | Waiting for prerequisites |
| `provisioning` | Remnawave/API work is running |
| `ready` | VPN access is ready for QR/subscription URL/config delivery |
| `retrying` | Retry is scheduled/running |
| `failed` | Provisioning failed |
| `expired` | Credential/access expired |
| `suspended` | Access/channel is suspended |
| `reconciliation_required` | Backend/Remnawave state mismatch requires review |
| `remnawave_unavailable` | Remnawave control-plane/API is unavailable |

Current backend mapping:

| Backend enum | Canonical state |
|---|---|
| `ServiceIdentityStatus.ACTIVE` | `ready` |
| `ServiceIdentityStatus.SUSPENDED` | `suspended` |
| `ServiceIdentityStatus.REVOKED` | `failed` |
| `ProvisioningProfileStatus.DRAFT` | `pending` |
| `ProvisioningProfileStatus.ACTIVE` | `ready` |
| `ProvisioningProfileStatus.ARCHIVED` | `failed` |
| `DeviceCredentialStatus.ACTIVE` | `ready` |
| `DeviceCredentialStatus.REVOKED` | `failed` |
| `DeviceCredentialStatus.EXPIRED` | `expired` |
| `AccessDeliveryChannelStatus.ACTIVE` | `ready` |
| `AccessDeliveryChannelStatus.SUSPENDED` | `suspended` |
| `AccessDeliveryChannelStatus.ARCHIVED` | `failed` |

## Canonical Access States

| Backend enum | Canonical customer access state |
|---|---|
| `UserStatus.ACTIVE` | `active` |
| `UserStatus.DISABLED` | `suspended` |
| `UserStatus.LIMITED` | `limited` |
| `UserStatus.EXPIRED` | `expired` |
| `EntitlementGrantStatus.PENDING` | `provisioning_pending` |
| `EntitlementGrantStatus.ACTIVE` | `active` |
| `EntitlementGrantStatus.SUSPENDED` | `suspended` |
| `EntitlementGrantStatus.REVOKED` | `no_access` |
| `EntitlementGrantStatus.EXPIRED` | `expired` |

## Required Manual Escalation Errors

| Error code | HTTP | Surface | Retryable | Support escalation |
|---|---:|---|---|---|
| `payment_orphan_review_required` | `409` | `payment` | `true` | `true` |
| `provisioning_failed` | `502` | `provisioning` | `true` | `true` |
| `provisioning_reconciliation_required` | `409` | `provisioning` | `true` | `true` |
| `remnawave_unavailable` | `503` | `provisioning` | `true` | `true` |
| `support_escalation_required` | `409` | `support` | `false` | `true` |

S1 orphan payment rule remains unchanged: no paid-but-no-access/orphan payment may be unresolved for more than 24 hours.

## Local Evidence Summary

| Check | Result |
|---|---|
| Error matrix covers every `Stage1ErrorCode` | Passed |
| Error matrix covers all launch-critical surfaces | Passed |
| Manual review errors require support escalation | Passed |
| Retryable transient states are explicit | Passed |
| Internal error response does not leak traceback/password/secret/token wording | Passed |
| `PaymentStatus` mapping is exhaustive | Passed |
| `PaymentAttemptStatus` mapping is exhaustive | Passed |
| `UserStatus` mapping is exhaustive | Passed |
| `ServiceIdentityStatus` mapping is exhaustive | Passed |
| `ProvisioningProfileStatus` mapping is exhaustive | Passed |
| `EntitlementGrantStatus` mapping is exhaustive | Passed |
| `DeviceCredentialStatus` mapping is exhaustive | Passed |
| `AccessDeliveryChannelStatus` mapping is exhaustive | Passed |
| Canonical error serializes through ASGI JSON response | Passed |
| Previous BE-003...BE-007 regression pack still passes | Passed |

## Regression Tests

Added:

```text
backend/tests/security/test_stage1_status_error_contract.py
```

Targeted result:

```text
21 passed in 0.07s
```

Broader backend hardening regression result:

```text
148 passed in 13.99s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-BE-008` canonical status/error model | Closed locally |
| API contract/error matrix for auth/payment/provisioning/support/system/validation | Added |
| Exhaustive mapping for current launch-critical backend enums | Added and tested |
| Orphan payment/provisioning/support escalation semantics | Added and tested |
| ASGI serialization proof for canonical error response | Added |

## What Remains Open

| Item | Why still open |
|---|---|
| Endpoint-by-endpoint migration from legacy `detail` errors | Should be done as each S1 endpoint is touched under `S1-AUTH-*`, `S1-PAY-*`, `S1-VPN-*`, `S1-FE-*`, `S1-TG-*` |
| Frontend/admin/Telegram rendering evidence | Requires UI work and screenshots/tests under `S1-FE-*` and `S1-TG-*` |
| Provider-specific payment status mapping | Must be handled under `S1-PAY-004`, `S1-PAY-017` and provider readiness tasks |
| Real orphan payment/reconciliation queue evidence | Local policy proof exists in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`; real admin/support queue and alert delivery remain under support/observability tasks |
| Deployed staging/prod evidence | Requires deployed backend/UI/support flows |

## Regeneration Command

```bash
ENVIRONMENT=test \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
TOTP_ENCRYPTION_KEY='<redacted-placeholder>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest \
  backend/tests/security/test_stage1_status_error_contract.py \
  -q --no-cov
```

Broader regression command:

```bash
ENVIRONMENT=test \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
TOTP_ENCRYPTION_KEY='<redacted-placeholder>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest \
  backend/tests/security/test_stage1_status_error_contract.py \
  backend/tests/security/test_stage1_rate_limit_policy.py \
  backend/tests/security/test_rate_limiter.py \
  backend/tests/security/test_stage1_csrf_protection.py \
  backend/tests/unit/config/test_settings.py \
  backend/tests/security/test_stage1_cors_cookie_config.py \
  backend/tests/security/test_stage1_swagger_public_off.py \
  backend/tests/security/test_stage1_route_boundary.py \
  backend/tests/unit/test_first_admin_bootstrap.py \
  backend/tests/unit/test_use_cases.py \
  backend/tests/security/test_ws_topic_auth.py \
  backend/tests/unit/test_domain_entities.py \
  -q --no-cov
```
