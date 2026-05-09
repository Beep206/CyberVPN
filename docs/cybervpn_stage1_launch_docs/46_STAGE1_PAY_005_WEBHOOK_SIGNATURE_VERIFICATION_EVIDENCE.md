> CyberVPN Launch Program
> Evidence ID: S1-PAY-005
> Date: 2026-05-08
> Status: local webhook signature/authenticity contract revalidated against official provider docs; real provider callback samples and credentials remain required before paid beta.

# S1-PAY-005 Webhook Signature Verification Evidence

## Scope

`S1-PAY-005` proves the local no-cost contract for payment webhook authenticity before any payment event can reach status mapping, idempotency, subscription extension or Remnawave provisioning.

This closes only the local code/test gate. It does not enable production payments and does not replace real provider sandbox/prod webhook samples, credential storage evidence, provider dashboards, IP allowlists, amount/currency matching, reconciliation or durable idempotency.

## Official Contract Inputs

Revalidated on `2026-05-08` against the official provider documentation below.

| Provider | S1 authenticity rule | Source |
|---|---|---|
| CryptoBot / Crypto Pay | Verify `crypto-pay-api-signature` as HMAC-SHA256 over the exact request body, using `sha256(app_token)` as the HMAC key | `https://help.send.tg/en/articles/10279948-crypto-pay-api` |
| NOWPayments | Verify `x-nowpayments-sig` as HMAC-SHA512 over recursively sorted JSON using the IPN secret | `https://nowpayments.zendesk.com/hc/en-us/articles/21395546303389-IPN-and-how-to-setup` |
| Telegram Stars | Verify Telegram Bot webhook `X-Telegram-Bot-Api-Secret-Token` against configured `secret_token` | `https://core.telegram.org/bots/api#setwebhook` |
| PayRam | Verify webhook `API-Key` header before processing payment data | `https://docs.payram.com/api-integration/payments-api/webhook`; `https://docs.payram.com/payram-sdk/typescript-javascript-sdk` |
| Digiseller | Verify `signature` using SHA256 HMAC over sorted `key:value;` fields with the seller secret | `https://my.digiseller.com/inside/api_payment.asp` |
| YooKassa | No HMAC webhook signature is documented; S1 requires provider status/IP recheck before processing | `https://yookassa.ru/developers/using-api/webhooks` |

## 2026-05-08 Revalidation Notes

| Provider | Result |
|---|---|
| CryptoBot / Crypto Pay | Official docs still require comparing `crypto-pay-api-signature` with HMAC-SHA256 of the raw request body using `sha256(app_token)` as key; S1 implementation remains valid. |
| NOWPayments | Official IPN docs still require `x-nowpayments-sig`, sorted JSON and HMAC SHA-512 with the IPN secret; S1 implementation remains valid. |
| Telegram Stars | Official Bot API still supports `secret_token` and sends `X-Telegram-Bot-Api-Secret-Token`; S1 implementation remains valid for Telegram Stars webhook traffic. |
| PayRam | Official Payments API webhook docs describe payment callbacks; SDK docs explicitly require checking the `API-Key` header for webhook authenticity. S1 source reference was updated to the current API/SDK docs. |
| Digiseller | Official payment API docs still define HMAC signature generation over sorted `key:value;` fields using the private key; S1 implementation remains valid. |
| YooKassa | Official webhook docs still do not provide a provider HMAC signature contract; S1 remains fail-closed until provider status/IP recheck evidence exists. |

## Code Added / Changed

| File | Purpose |
|---|---|
| `backend/src/presentation/api/shared/stage1_webhook_signature.py` | Provider-specific S1 webhook authenticity verifier with safe decisions |
| `backend/tests/security/test_stage1_webhook_signature_verification.py` | Component and ASGI feature tests for valid/invalid/missing signatures |

Updated:

```text
backend/src/presentation/api/shared/__init__.py
backend/src/presentation/api/v1/webhooks/routes.py
backend/tests/integration/api/v1/payments/test_payment_flows.py
docs/cybervpn_stage1_launch_docs/00_INDEX.md
docs/cybervpn_stage1_launch_docs/06_STAGE1_IMPLEMENTATION_BACKLOG.md
docs/cybervpn_stage1_launch_docs/21_STAGE1_EXECUTION_PLAN_AND_WORK_QUEUE.md
```

## S1 Contract

| Rule | S1 behavior |
|---|---|
| Invalid CryptoBot HMAC | rejected before `ProcessPaymentWebhookUseCase` |
| Missing provider signature/header | rejected |
| Missing configured verifier secret | rejected |
| NOWPayments body order differs | accepted only if sorted JSON HMAC matches |
| CryptoBot body is mutated after signing | rejected |
| Telegram Stars webhook lacks valid secret token header | rejected |
| PayRam `API-Key` mismatch | rejected |
| Digiseller signed fields mismatch | rejected |
| YooKassa webhook arrives without provider recheck | blocked as `requires_provider_recheck` |
| Safe decision output | no raw provider payment id, payload, token, API key, HMAC or signature value |

## Test Coverage

| Scenario | Result |
|---|---|
| CryptoBot valid official HMAC contract | accepted |
| CryptoBot mutated body | rejected |
| CryptoBot missing signature header | rejected |
| NOWPayments sorted JSON HMAC-SHA512 | accepted/rejected correctly |
| PayRam `API-Key` header | accepted/rejected correctly |
| Telegram Bot `secret_token` header | accepted; missing secret rejected |
| Digiseller sorted field HMAC-SHA256 | accepted/rejected correctly |
| YooKassa without provider recheck | blocked |
| ASGI feature route | invalid signature returns `401` before idempotency/side effects; valid signature reaches idempotency |
| Real CryptoBot route invalid-path | returns `401` with safe error |

## Targeted Test Result

Command:

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://localhost:6379/15 \
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings \
JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough \
CRYPTOBOT_TOKEN=test-cryptobot-token \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest backend/tests/security/test_stage1_webhook_signature_verification.py -q --no-cov
```

Original result:

```text
collected 10 items
backend/tests/security/test_stage1_webhook_signature_verification.py .......... [100%]
10 passed in 0.05s
```

2026-05-08 revalidation result:

```text
10 passed in 0.05s
```

## Real Route Invalid-Path Result

Command:

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://localhost:6379/15 \
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings \
JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough \
CRYPTOBOT_TOKEN=test-cryptobot-token \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest backend/tests/integration/api/v1/payments/test_payment_flows.py::TestCryptobotWebhook::test_webhook_invalid_signature -q --no-cov
```

Original result:

```text
collected 1 item
backend/tests/integration/api/v1/payments/test_payment_flows.py . [100%]
1 passed in 0.04s
```

2026-05-08 revalidation result:

```text
1 passed in 0.21s
```

Full `TestCryptobotWebhook` valid-path route execution was not used as accepted evidence because local PostgreSQL was not running on `localhost:5432`; S1-PAY-005 specifically verifies fail-closed invalid signature behavior, which does not require database access.

## Regression Pack

Command:

```bash
ENVIRONMENT=test \
SKIP_TEST_DB_BOOTSTRAP=1 \
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test \
REDIS_URL=redis://localhost:6379/15 \
REMNAWAVE_TOKEN=test-remnawave-token \
JWT_SECRET=test-jwt-secret-that-is-long-enough-for-settings \
JWT_REFRESH_SECRET=test-refresh-secret-that-is-long-enough \
CRYPTOBOT_TOKEN=test-cryptobot-token \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest backend/tests/security/test_stage1_*.py -q --no-cov
```

Original result:

```text
collected 225 items
225 passed in 13.29s
```

2026-05-08 provider/payment regression result:

```text
108 passed in 0.37s
```

Ruff:

```text
python -m ruff check \
  backend/src/presentation/api/shared/stage1_webhook_signature.py \
  backend/src/presentation/api/shared/__init__.py \
  backend/src/presentation/api/v1/webhooks/routes.py \
  backend/tests/security/test_stage1_webhook_signature_verification.py \
  backend/tests/integration/api/v1/payments/test_payment_flows.py

All checks passed.
```

Compile:

```text
python -m py_compile \
  backend/src/presentation/api/shared/stage1_webhook_signature.py \
  backend/src/presentation/api/v1/webhooks/routes.py \
  backend/tests/security/test_stage1_webhook_signature_verification.py
```

Result: passed.

## What This Closes Locally

| Item | Status |
|---|---|
| `S1-PAY-005` local webhook authenticity verifier | Closed locally |
| Invalid signature fail-closed route behavior for CryptoBot | Closed locally |
| Provider-specific signature/header/recheck scheme table | Closed locally |
| Safe verifier decision serialization | Closed locally |
| Signature verifier export for future provider adapters | Closed locally |

## Remaining Evidence Before Paid Beta

| Evidence | Status |
|---|---|
| Real CryptoBot testnet/prod callback sample with valid signature | Open |
| Real NOWPayments IPN sample with `x-nowpayments-sig` | Open |
| Real Telegram webhook configured with `secret_token` | Open |
| Real PayRam webhook header sample and status API recheck | Open |
| Real Digiseller callback/status sample and signature | Open |
| Real YooKassa notification plus status/IP recheck evidence | Open |
| Production/staging credential storage and rotation evidence | Open |
| Durable webhook idempotency persistence | Open |
| Amount/currency/order ownership verification evidence | Open |
| Reconciliation job evidence | Local done in `83_STAGE1_PAY_012_RECONCILIATION_JOB_EVIDENCE.md`; real provider/admin queue/alert evidence open |

## Security Review Notes

| Check | Result |
|---|---|
| `pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing low/moderate advisories remain tracked outside this task |
| Targeted secret scan | PASS after excluding explicit `<redacted-placeholder>` examples |
| Static dangerous-pattern scan | PASS: no `eval`, shell execution, pickle/YAML unsafe load or string-built SQL pattern found in changed Python files/docs |
| Running containers after task | PASS: no task containers started |

## Conclusion

`S1-PAY-005` is locally complete. Payment webhook processing now has a provider-specific authenticity gate and the CryptoBot route rejects invalid signatures before any payment or provisioning side effects. Paid beta remains blocked until real provider callbacks, credentials, status/API rechecks, durable idempotency and reconciliation evidence are attached.

## Next ID

Next ID superseded by `37_STAGE1_PAY_006_WEBHOOK_IDEMPOTENCY_EVIDENCE.md`, `38_STAGE1_PAY_007_ORPHAN_PAYMENT_POLICY_EVIDENCE.md`, `45_STAGE1_PAY_008_PAYMENT_PROVISIONING_FAILURE_EVIDENCE.md`, `81_STAGE1_PAY_009_REFUND_DISPUTE_PROCESS_EVIDENCE.md` and `82_STAGE1_PAY_010_WALLET_PAYMENT_HISTORY_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.
