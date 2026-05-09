> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-08
> Backlog ID: `S1-PAY-006`
> Статус: local webhook idempotency contract and duplicate-webhook proof revalidated; durable Redis/DB/live-provider evidence remains required before enabling any paid provider.

# S1-PAY-006 Webhook Idempotency Evidence

## Purpose

Этот документ фиксирует `S1-PAY-006`: duplicate payment webhooks must not create duplicate wallet transactions, subscription extensions or provisioning jobs.

S1 rule:

```text
Provider retries may be accepted with HTTP 2xx, but payment side effects must be idempotent.
The second webhook for the same provider/payment/status operation must not repeat wallet, subscription or provisioning side effects.
```

This is a no-cost local implementation gate. It does not enable production payments and does not replace real provider callback/signature evidence.

## Provider Payload Fields Used

Revalidated on `2026-05-08` against current provider documentation and local S1 provider readiness fixtures.

| Provider | Identity fields used for local S1 fixtures | Source / basis |
|---|---|---|
| PayRam | `referenceID`/`reference_id` + `payment_state`/`paymentState`/`status`; optional webhook event id | PayRam docs describe webhook payload fields including `reference_id` and `status`; SDK/docs require webhook API-key validation |
| NOWPayments | `payment_id` + `payment_status`; optional IPN/event id | NOWPayments IPN docs describe `payment_id`, `order_id`, `purchase_id` and `payment_status` |
| CryptoBot / Crypto Pay | `payload.invoice_id` + `update_type`; optional `update_id`/invoice `hash` | Crypto Pay docs describe `invoice_paid` updates, invoice payloads and webhook retries |
| Telegram Stars | `successful_payment.telegram_payment_charge_id` + `successful_payment` event | Telegram Bot payments expose `successful_payment` and payment charge ids after successful payment |
| Digiseller | `invoice_id`/`inv`/`id` + `status`; optional notification id | Digiseller payment API docs describe `invoice_id`, amount/currency and `status` in callback/status payloads; live callback samples still required |
| YooKassa | `object.id` + `event` such as `payment.succeeded`; optional notification id | YooKassa webhooks send `event` and `object`; non-200 responses are retried for 24 hours; provider requests support `Idempotence-Key` |

## 2026-05-08 Revalidation Notes

| Provider | Result |
|---|---|
| CryptoBot / Crypto Pay | Official docs now explicitly state webhook delivery retries for up to 3 days / 17 attempts. The S1 duplicate-event and same-payment/status side-effect keys remain required. |
| NOWPayments | Official IPN example still includes `payment_id`, `payment_status`, `order_id` and `purchase_id`; S1 identity extraction remains valid for local proof. |
| Telegram Stars | Official Bot API uses update delivery semantics and `successful_payment` payloads; S1 keys use `telegram_payment_charge_id` to suppress duplicate paid delivery. |
| PayRam | Official webhook payload still includes payment reference/status fields; S1 accepts both webhook-style and status-poll field names. |
| Digiseller | Official payment API still uses `invoice_id` and `status` in payment status exchange; S1 identity extraction remains valid for local proof. |
| YooKassa | Official webhook docs retry non-200 responses for 24 hours, and API docs define request idempotency through `Idempotence-Key`; S1 keeps CyberVPN-side idempotency in addition to provider-side keys. |

## Implementation

Added:

```text
backend/src/presentation/api/shared/stage1_webhook_idempotency.py
backend/tests/security/test_stage1_webhook_idempotency.py
```

Updated:

```text
backend/src/presentation/api/shared/__init__.py
```

The contract exposes:

- `Stage1WebhookIdentity`;
- `Stage1WebhookSideEffect`;
- `Stage1WebhookIdempotencyResult`;
- `Stage1WebhookIdempotencyDecision`;
- `Stage1InMemoryWebhookIdempotencyGuard`;
- `DEFAULT_STAGE1_WEBHOOK_SIDE_EFFECTS`;
- `build_stage1_webhook_identity`;
- `build_stage1_webhook_side_effect_keys`;
- `extract_stage1_webhook_identity`.

## Key Design

The local contract separates two keys:

| Key | Purpose | Includes provider event id? |
|---|---|---:|
| `idempotency_key` | Detect exact duplicate event delivery | Yes, when provider supplies it |
| `operation_key` and side-effect keys | Suppress repeated side effects for the same provider/payment/status operation | No |

This matters because providers may retry the same webhook body, or send a new notification id for the same already-paid payment. CyberVPN must accept both safely, but must not run duplicate wallet/subscription/provisioning side effects.

Default guarded side effects:

```text
payment_status_update
wallet_transaction
subscription_extension
provisioning_job
```

`support_escalation` is available as a separate side effect for later orphan/reconciliation flows, but is not part of the default paid webhook side-effect set.

## Local Evidence Summary

| Check | Result |
|---|---|
| Identity extraction covers PayRam fixture | Passed |
| Identity extraction covers NOWPayments fixture | Passed |
| Identity extraction covers CryptoBot fixture | Passed |
| Identity extraction covers Telegram Stars fixture | Passed |
| Identity extraction covers Digiseller fixture | Passed |
| Identity extraction covers YooKassa fixture | Passed |
| Reordered payload fields produce the same key | Passed |
| Unknown/secret-like payload fields do not affect the key | Passed |
| Safe serialization does not echo raw signatures, tokens, passwords or secrets | Passed |
| Exact duplicate webhook returns `duplicate_accepted` and no side effects | Passed |
| New event id for same provider/payment/status does not repeat side effects | Passed |
| ASGI feature route returns 200 for duplicate webhook and leaves counters unchanged | Passed |
| Missing provider payment id is rejected without echoing payload values | Passed |

## Targeted Test Result

Original result:

```text
backend/tests/security/test_stage1_webhook_idempotency.py .............  [100%]
13 passed in 0.06s
```

2026-05-08 revalidation result:

```text
13 passed in 0.06s
```

## Broader Regression Result

Original result:

```text
199 passed in 12.71s
```

2026-05-08 provider/payment regression result:

```text
108 passed in 0.48s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-PAY-006` local webhook idempotency contract | Closed locally |
| Duplicate webhook component proof | Closed locally |
| Duplicate webhook ASGI feature proof | Closed locally |
| Provider fixture extraction for all S1 payment providers | Closed locally |
| Secret-safe idempotency evidence serialization | Closed locally |

## What Remains Open

| Item | Why still open |
|---|---|
| Durable idempotency persistence | The local guard is in-memory; paid beta requires Redis and/or database-backed uniqueness |
| Real provider duplicate callback evidence | Requires configured provider accounts/webhooks and sandbox/prod callback samples |
| Provider signature verification evidence | Covered by `S1-PAY-005` and provider readiness tasks |
| Actual wallet/subscription/provisioning integration | This task proves the contract and feature behavior with counters; S1 payment/provisioning flows must wire the same keys into real handlers |
| Orphan payment escalation | Local policy covered by `S1-PAY-007` in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`; real admin/support queue and alert delivery remain open |
| Payment -> provisioning failure retry | Closed locally by `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`; durable/live provider/staging evidence remains open |

## Regeneration Command

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL='postgresql+asyncpg://<redacted>' \
REDIS_URL='redis://localhost:6379/15' \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder-32-plus-chars>' \
JWT_REFRESH_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest \
  backend/tests/security/test_stage1_webhook_idempotency.py \
  -q --no-cov
```

Broader regression command:

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL='postgresql+asyncpg://<redacted>' \
REDIS_URL='redis://localhost:6379/15' \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder-32-plus-chars>' \
JWT_REFRESH_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest \
  backend/tests/security/test_stage1_webhook_idempotency.py \
  backend/tests/security/test_stage1_provider_payment_status_mapping.py \
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

2026-05-08 provider/payment regression command:

```bash
PYENV_VERSION=3.13.11 \
uv run pytest \
  tests/security/test_stage1_webhook_idempotency.py \
  tests/security/test_stage1_webhook_signature_verification.py \
  tests/security/test_stage1_provider_payment_status_mapping.py \
  tests/security/test_stage1_payram_readiness.py \
  tests/security/test_stage1_nowpayments_readiness.py \
  tests/security/test_stage1_telegram_stars_readiness.py \
  tests/security/test_stage1_digiseller_readiness.py \
  tests/security/test_stage1_yookassa_readiness.py \
  tests/security/test_stage1_provider_placeholder_replacement.py \
  -q --no-cov
```

## 2026-05-08 Verification

| Check | Result |
|---|---|
| Official provider documentation recheck | PASS: no S1 idempotency key change required |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_webhook_idempotency.py -q --no-cov` | PASS: 13 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_webhook_signature_verification.py tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_payram_readiness.py tests/security/test_stage1_nowpayments_readiness.py tests/security/test_stage1_telegram_stars_readiness.py tests/security/test_stage1_digiseller_readiness.py tests/security/test_stage1_yookassa_readiness.py tests/security/test_stage1_provider_placeholder_replacement.py -q --no-cov` | PASS: 108 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_webhook_idempotency.py tests/security/test_stage1_webhook_idempotency.py` | PASS |
| `git diff --check -- <S1-PAY-006 touched files>` | PASS |
| Secret scan over touched files | PASS after excluding explicit `<redacted-placeholder>` examples and documentation terms |
| Static dangerous-pattern scan over touched files | PASS |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing low/moderate advisories remain tracked outside this task |
| Backend `pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| Running containers after task | PASS: no task containers started |

## Next ID

Next ID superseded by `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
