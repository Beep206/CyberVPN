> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-05
> Backlog ID: `S1-PAY-017`
> Статус: local provider evidence replacement structure completed; real sandbox/prod provider samples remain required before any paid provider can be enabled.

# S1-PAY-017 Provider Placeholder Replacement Evidence

## Purpose

`S1-PAY-017` closes the no-cost/local part of replacing provider documentation placeholders with a strict evidence structure.

This task does **not** claim that PayRam, NOWPayments, CryptoBot, Telegram Stars, Digiseller or YooKassa are ready for live paid beta. It creates a guardrail: documentation-derived examples can be used for local mapping tests, but they cannot unlock provider enablement.

## Scope Completed

| Area | Result |
|---|---|
| Provider evidence registry | Added typed backend evidence model and validation helpers |
| Documentation placeholder fixture | Added redacted fixture samples for all six owner-approved S1 providers |
| Enablement decision gate | Documentation-only samples always block provider enablement |
| Real evidence contract | Provider-account samples must be sandbox/production, redacted, status-mapped and complete |
| Tests | Added security tests proving docs-only placeholders do not enable paid rails |
| Tech debt tracking | Existing payment provider tech debt remains blocking before paid beta/provider enablement |

## Files Added Or Updated

```text
backend/src/presentation/api/shared/stage1_provider_evidence.py
backend/src/presentation/api/shared/__init__.py
backend/tests/fixtures/stage1_provider_evidence/provider_documentation_placeholders.json
backend/tests/security/test_stage1_provider_placeholder_replacement.py
docs/cybervpn_stage1_launch_docs/84_STAGE1_PAY_017_PROVIDER_PLACEHOLDER_REPLACEMENT_EVIDENCE.md
```

## Official Sources Rechecked

The placeholder fixture was aligned with official documentation available on 2026-05-05:

| Provider | Official source | Facts used |
|---|---|---|
| PayRam | https://docs.payram.com/api-integration/payments-api/payment-status and https://docs.payram.com/api-integration/payments-api/webhook | `OPEN`, `CANCELLED`, `FILLED`, `PARTIALLY_FILLED`, `OVER_FILLED`; webhook sample uses `status` |
| NOWPayments | https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses | `finished` is completed; `partially_paid` and wrong-asset payments require manual/business handling |
| CryptoBot / Crypto Pay | https://help.send.tg/en/articles/10279948-crypto-pay-api | invoice statuses include `active`, `paid`, `expired`; webhook retries are documented; testnet and mainnet endpoints are separate |
| Telegram Stars | https://core.telegram.org/bots/payments-stars | access must be delivered only after `successful_payment`, not after `pre_checkout_query`; `telegram_payment_charge_id` must be stored for refunds |
| Digiseller | https://my.digiseller.com/inside/api_payment.asp | callback/status values include `paid`, `wait`, `canceled`, `refunded`, `error`; signature uses HMAC SHA256 |
| YooKassa | https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process and https://yookassa.ru/developers/using-api/webhooks | `succeeded` and `canceled` are final; `waiting_for_capture` requires capture/cancel handling; notification authenticity must be checked by status recheck or IP |

## Evidence Contract

Provider evidence samples must include:

| Field | Requirement |
|---|---|
| `provider` | One of the owner-approved S1 providers |
| `evidence_kind` | `callback_sample`, `status_poll_sample`, `signature_verification`, `refund_sample` or `reconciliation_sample` |
| `environment` | `official_docs`, `sandbox` or `production` |
| `source` | `official_documentation` or `provider_account` |
| `provider_status` | Provider status/event that maps through the S1 payment status matrix |
| `expected_payment_state` | Expected CyberVPN S1 payment state |
| `automatic_paid_access_allowed` | Must match the code-level status mapping decision |
| `payload_shape` | Redacted structure only; no real IDs, secrets, tokens, URLs, idempotency keys or raw snapshots |
| `tech_debt_id` | Must link back to `TD-S1-PAY-*` |

Provider-account samples are invalid if they use `environment=official_docs`.

## Enablement Gate

For a provider to be considered enablement-ready in S1, real provider-account evidence must include at minimum:

1. A real paid/success callback sample.
2. A real non-success callback sample.
3. A real provider status/API polling sample.
4. Signature/authenticity verification evidence.
5. Refund or reconciliation evidence.
6. Redaction proof for committed evidence.

Documentation-only placeholder samples fail this gate with:

```text
real_provider_account_samples_missing
real_callback_sample_missing
real_paid_success_callback_missing
real_non_success_callback_missing
real_status_poll_sample_missing
signature_verification_evidence_missing
refund_or_reconciliation_evidence_missing
```

## Local Test Evidence

Targeted command:

```bash
cd backend && uv run pytest tests/security/test_stage1_provider_placeholder_replacement.py -q --no-cov
```

Observed result:

```text
12 passed
```

Combined mapping/evidence command:

```bash
cd backend && uv run pytest tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_provider_placeholder_replacement.py -q --no-cov
```

Observed result:

```text
50 passed
```

The test suite proves:

- all six approved S1 providers have documentation placeholder samples;
- placeholder samples match the S1 payment status mapping;
- placeholder samples are redacted;
- documentation-only samples never enable paid provider rails;
- synthetic provider-account evidence unlocks a provider only when all required sample categories exist;
- provider-account evidence cannot use `official_docs` as environment;
- sensitive payload keys are rejected.

## What This Closes

| Item | Status |
|---|---|
| `S1-PAY-017` local evidence structure | Closed locally |
| Documentation placeholder fixture for all approved providers | Added |
| Guardrail against enabling providers from documentation-only samples | Added and tested |
| Remaining provider placeholder debt | Tracked in `19_STAGE1_TECH_DEBT_REGISTER.md` |

## What Remains Open

| Item | Why still open |
|---|---|
| Real PayRam evidence | Requires provider account, webhook/API configuration and real sandbox/prod samples |
| Real NOWPayments evidence | Requires provider account, IPN setup, signature evidence and live dashboard samples |
| Real CryptoBot evidence | Requires `@CryptoTestnetBot`/production app credentials and callback samples |
| Real Telegram Stars evidence | Requires real BotFather/Stars flow, XTR pricing, successful payment and refund evidence |
| Real Digiseller evidence | Requires product/payment setup, callback/status samples and signature proof |
| Real YooKassa evidence | Requires test/prod shop webhook samples, amount/metadata verification and fiscalization/receipt decision |
| Paid beta provider enablement | At least one provider must pass real evidence gate before live paid beta |

## Security Notes

- No real provider credential, token, API key, webhook secret, checkout URL or payment URL was added.
- Fixture values are redacted shape examples only.
- The registry rejects forbidden payload keys such as `api_key`, `secret`, `token`, `authorization`, `idempotency_key`, `payment_url`, `provider_snapshot` and `request_snapshot`.
- This task does not call provider APIs and creates no external payment side effects.

## Next Recommended Task

Next ID to execute: `S1-VPN-009` - define usage display policy before continuing VPN/customer-facing readiness work.
