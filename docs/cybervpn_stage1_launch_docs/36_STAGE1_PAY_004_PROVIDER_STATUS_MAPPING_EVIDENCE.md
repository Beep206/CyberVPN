> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-08
> Backlog ID: `S1-PAY-004`
> Статус: local provider status mapping revalidated against official provider docs; real sandbox/prod callback samples remain required before enabling any paid provider.

# S1-PAY-004 Provider Status Mapping Evidence

## Purpose

Этот документ фиксирует `S1-PAY-004`: provider-specific payment statuses must map into one CyberVPN S1 payment decision model before any paid path can create or extend VPN access.

S1 rule:

```text
Only provider-proven paid/final statuses may automatically grant paid VPN access.
Partial, overpaid-by-default, waiting, capture-required, refunded, canceled, failed and unknown states must not grant paid access automatically.
```

This is a no-cost implementation gate. It does not enable production payments and does not replace real provider callback evidence.

## Official Sources Checked

Revalidated on `2026-05-08` against the official provider documentation below.

| Provider | Official source | Key status facts used |
|---|---|---|
| PayRam | https://docs.payram.com/api-integration/payments-api/payment-status | `OPEN`, `CANCELLED`, `FILLED`, `PARTIALLY_FILLED`, `OVER_FILLED`; API key required for payment status/webhook handling |
| NOWPayments | https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses | `finished` is completed; `partially_paid` means funds received but underpaid; wrong-asset and partial payments require business handling |
| CryptoBot / Crypto Pay | https://help.send.tg/en/articles/10279948-crypto-pay-api | Invoice statuses include `active`, `paid`, `expired`; webhook update type `invoice_paid`; webhook signature uses `crypto-pay-api-signature` |
| Telegram Stars | https://core.telegram.org/bots/payments-stars | Deliver only after `successful_payment`; `pre_checkout_query` alone is not proof of payment; store `telegram_payment_charge_id`; `/paysupport`/support and `refundStarPayment` are required for live readiness |
| Digiseller | https://my.digiseller.com/inside/api_payment.asp | Payment callback/status values include `paid`, `wait`, `canceled`, `refunded`, `error` |
| YooKassa | https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process | `pending`, `waiting_for_capture`, `succeeded`, `canceled`; `succeeded` and `canceled` are final; `waiting_for_capture` requires capture/cancel before final handling |

## 2026-05-08 Revalidation Notes

| Provider | Result |
|---|---|
| PayRam | Official docs still expose `paymentState` with `OPEN`, `CANCELLED`, `FILLED`, `PARTIALLY_FILLED`, `OVER_FILLED`; S1 mapping remains valid. |
| NOWPayments | Official docs were checked with the 2026-03-03 updated status article; `finished` remains the only normal completed status for automatic paid access, and `partially_paid`/wrong-asset states remain manual-review states. |
| CryptoBot / Crypto Pay | Official Crypto Pay API docs were checked; invoice statuses include `active` and `paid`, webhook update `invoice_paid` remains the paid event path, and mainnet/testnet endpoints remain separated. |
| Telegram Stars | Official Telegram Stars payment docs were checked; delivery remains gated on `successful_payment`, while pre-checkout handling is not payment proof. |
| Digiseller | Official payment API docs were checked; documented status values remain `paid`, `wait`, `canceled`, `refunded`, `error`. |
| YooKassa | Official payment process docs were checked; `succeeded` and `canceled` are final states, while `waiting_for_capture` requires capture/cancel before S1 access. |

## Implementation

Added:

```text
backend/src/presentation/api/shared/stage1_payment_mapping.py
backend/tests/security/test_stage1_provider_payment_status_mapping.py
```

Updated:

```text
backend/src/presentation/api/shared/__init__.py
```

The mapping exposes:

- `Stage1PaymentProvider`;
- `Stage1ProviderStatusSource`;
- `Stage1ProviderPaymentStatusRule`;
- `Stage1ProviderPaymentStatusDecision`;
- `STAGE1_PROVIDER_STATUS_SOURCES`;
- `STAGE1_PROVIDER_STATUS_RULES`;
- `normalize_provider_status`;
- `resolve_stage1_provider_payment_status`;
- `stage1_provider_status_values`.

## Provider Status Mapping

### PayRam

| Provider status | CyberVPN state | Final? | Auto paid access? | S1 behavior |
|---|---|---:|---:|---|
| `OPEN` | `pending` | No | No | Poll/reconcile |
| `FILLED` | `paid` | Yes | Yes | Verify `API-Key`, reference, amount, currency; provision |
| `OVER_FILLED` | `reconciliation_required` by default | Yes | No by default | Manual finance/support review |
| `OVER_FILLED` with explicit policy and amount evidence | `paid` | Yes | Yes | Provision, but keep finance/support review open |
| `PARTIALLY_FILLED` | `reconciliation_required` | No | No | Underpaid; manual review |
| `CANCELLED` / `CANCELED` | `expired` | Yes | No | No access; retry allowed |

### NOWPayments

| Provider status | CyberVPN state | Final? | Auto paid access? | S1 behavior |
|---|---|---:|---:|---|
| `waiting` | `pending` | No | No | Await deposit |
| `confirming` | `pending` | No | No | Await confirmations |
| `confirmed` | `pending` | No | No | Await `finished` |
| `sending` | `processing` | No | No | Await settlement |
| `finished` | `paid` | Yes | Yes | Verify IPN/signature, amount, currency; provision |
| `partially_paid` | `reconciliation_required` | Yes | No | Funds received but underpaid; manual review |
| `wrong_asset_confirmed` | `reconciliation_required` | Yes | No | Wrong asset/network; manual review |
| `failed` | `failed` | Yes | No | No access |
| `expired` | `expired` | Yes | No | No access; retry allowed |
| `cancelled` / `canceled` | `cancelled` | Yes | No | No access |
| `refunded` | `refunded` | Yes | No | Revoke/adjust according to refund policy |

### CryptoBot / Crypto Pay

| Provider status/event | CyberVPN state | Final? | Auto paid access? | S1 behavior |
|---|---|---:|---:|---|
| `active` | `pending` | No | No | No access |
| `paid` | `paid` | Yes | Yes | Verify signature/payload; provision |
| `invoice_paid` | `paid` | Yes | Yes | Webhook paid event after signature verification; provision |
| `expired` | `expired` | Yes | No | No access; retry allowed |

### Telegram Stars

| Event/object | CyberVPN state | Final? | Auto paid access? | S1 behavior |
|---|---|---:|---:|---|
| `invoice_sent` | `pending` | No | No | No access |
| `pre_checkout_query` | `processing` | No | No | Answer within 10 seconds; no access |
| `successful_payment` | `paid` | Yes | Yes | Store `telegram_payment_charge_id`; provision |
| `payment_timeout` | `expired` | Yes | No | No access |
| `refund_succeeded` | `refunded` | Yes | No | Revoke/adjust according to refund policy |

### Digiseller

| Provider status | CyberVPN state | Final? | Auto paid access? | S1 behavior |
|---|---|---:|---:|---|
| `wait` | `pending` | No | No | No access |
| `paid` | `paid` | Yes | Yes | Verify signature, amount, currency, invoice id; provision |
| `canceled` | `cancelled` | Yes | No | No access |
| `refunded` | `refunded` | Yes | No | Revoke/adjust according to refund policy |
| `error` | `failed` | Yes | No | No access |

### YooKassa

| Provider status/event | CyberVPN state | Final? | Auto paid access? | S1 behavior |
|---|---|---:|---:|---|
| `pending` | `pending` | No | No | Await user/provider action |
| `waiting_for_capture` | `processing` | No | No | Capture before access in S1 |
| `payment.waiting_for_capture` | `processing` | No | No | Webhook event for two-stage payment awaiting capture; no access before capture |
| `succeeded` | `paid` | Yes | Yes | Verify API/webhook state, amount, currency, metadata; provision |
| `payment.succeeded` | `paid` | Yes | Yes | Webhook succeeded event after verification; provision |
| `canceled` | `cancelled` | Yes | No | No access |
| `payment.canceled` | `cancelled` | Yes | No | No access |
| `refund.succeeded` | `refunded` | Yes | No | Refund succeeded; support/finance review and revoke/adjust access |

## Unknown Status Policy

Any unknown provider status maps to:

```json
{
  "payment_state": "reconciliation_required",
  "final": false,
  "automatic_paid_access_allowed": false,
  "manual_review_required": true,
  "support_state": "ops_escalation"
}
```

Interpretation: unknown provider states must never grant paid access automatically during S1.

## Local Evidence Summary

| Check | Result |
|---|---|
| Provider source table covers all 6 owner-approved S1 providers | Passed |
| Status normalization handles case, dots, spaces and hyphens | Passed |
| PayRam documented statuses covered | Passed |
| NOWPayments documented statuses covered | Passed |
| CryptoBot invoice/webhook statuses covered | Passed |
| Telegram Stars invoice/pre-checkout/success/refund states covered | Passed |
| Digiseller documented statuses covered | Passed |
| YooKassa payment status/webhook/refund event states covered | Passed; extended by `112_STAGE1_PAY_016_YOOKASSA_READINESS_EVIDENCE.md` |
| Only provider-proven paid statuses allow automatic paid access | Passed |
| Waiting/partial/capture/refund/unknown states do not allow automatic paid access | Passed |
| PayRam `OVER_FILLED` is blocked by default | Passed |
| PayRam `OVER_FILLED` can be explicitly accepted only with amount evidence | Passed |
| ASGI feature route serializes mapping decisions for API usage | Passed |
| Previous S1 backend hardening/status contract regression pack still passes | Passed |

## Regression Tests

Added:

```text
backend/tests/security/test_stage1_provider_payment_status_mapping.py
```

Targeted result after `2026-05-08` revalidation:

```text
40 passed in 0.27s
```

Provider-readiness regression result after `2026-05-08` revalidation:

```text
85 passed in 0.34s
```

Updated `S1-PAY-016` regression result:

```text
82 passed in 0.39s
```

Broader regression result:

```text
186 passed in 13.48s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-PAY-004` local provider status mapping | Closed locally |
| Official-doc provider status baseline in code | Added |
| Fixture tests for PayRam/NOWPayments/CryptoBot/Telegram Stars/Digiseller/YooKassa | Added |
| Automatic paid-access gate for provider-proven paid statuses | Added |
| Unknown status manual reconciliation policy | Added |

## What Remains Open

| Item | Why still open |
|---|---|
| Real sandbox/prod callback samples | Requires provider accounts/credentials and configured webhooks; local evidence registry guardrail is completed in `84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md` |
| Provider signature verification evidence | Covered by `S1-PAY-005` and provider readiness tasks |
| Webhook idempotency evidence | Covered by `S1-PAY-006` |
| Orphan payment queue/support escalation | Local policy covered by `S1-PAY-007` in `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`; real admin/support queue and alert delivery remain open |
| Payment -> provisioning failure preservation/retry | Closed locally by `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`; durable/live provider/staging evidence remains open |
| Provider-specific refunds/disputes | Covered by `S1-PAY-009`, `S1-PAY-011`, `S1-PAY-013`...`S1-PAY-016` |

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
  backend/tests/security/test_stage1_provider_payment_status_mapping.py \
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

2026-05-08 provider-readiness regression command:

```bash
PYENV_VERSION=3.13.11 \
uv run pytest \
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
| Official provider documentation recheck | PASS: no S1 mapping change required |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_provider_payment_status_mapping.py -q --no-cov` | PASS: 40 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_payram_readiness.py tests/security/test_stage1_nowpayments_readiness.py tests/security/test_stage1_telegram_stars_readiness.py tests/security/test_stage1_digiseller_readiness.py tests/security/test_stage1_yookassa_readiness.py tests/security/test_stage1_provider_placeholder_replacement.py -q --no-cov` | PASS: 85 passed |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_payment_mapping.py tests/security/test_stage1_provider_payment_status_mapping.py` | PASS |
| `git diff --check -- <S1-PAY-004 touched files>` | PASS |
| Secret scan over touched files | PASS after excluding explicit `<redacted-placeholder>` examples |
| Static dangerous-pattern scan over touched files | PASS |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing low/moderate advisories remain tracked outside this task |
| Backend `pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| Running containers after task | PASS: no task containers started |

## Next ID

Next ID superseded by `46_STAGE1_PAY_005_WEBHOOK_SIGNATURE_VERIFICATION_EVIDENCE.md`, `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
