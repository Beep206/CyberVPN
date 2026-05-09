> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-016`
> Статус: PASS for local/no-cost YooKassa readiness guardrails and 2026-05-08 official-doc revalidation. Real YooKassa shop/account/credential/webhook/status/refund/reconciliation/receipt/fiscal evidence remains required before enablement.

# S1-PAY-016 YooKassa Readiness Evidence

## Purpose

`S1-PAY-016` verifies the CyberVPN S1 YooKassa Russia-path integration contract before YooKassa can be enabled as a paid provider.

This task does not make YooKassa production-ready. It proves that local backend guardrails match the currently documented YooKassa payment lifecycle, webhook authenticity posture, idempotency expectations, refund constraints and receipt/fiscalization risk.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-015`. YooKassa official documentation was rechecked before this evidence refresh. The S1 local contract remains valid: only `succeeded` / `payment.succeeded` is the normal automatic paid-access status, `pending`/`waiting_for_capture`/`payment.waiting_for_capture`/`canceled` do not grant access, `refund.succeeded` goes to support/finance review, webhook body is not trusted without current provider status or IP recheck, and YooKassa remains disabled until real shop-account and receipt/fiscal evidence exists.

## Official YooKassa Requirements Checked

| Requirement | Source | CyberVPN S1 rule |
|---|---|---|
| Payment creation uses shop id + secret key authentication, `Idempotence-Key`, amount/currency, confirmation/return URL and optional metadata | <https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process> | Store CyberVPN payment id against YooKassa `payment.id` and order metadata; never commit shop id/secret, payment URL, full card data or raw provider snapshot |
| Payment lifecycle statuses are `pending`, `waiting_for_capture`, `succeeded`, `canceled`; `succeeded` and `canceled` are final, while `waiting_for_capture` requires capture or cancellation | <https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process> | Only `succeeded` / `payment.succeeded` is normal automatic paid-access status; `waiting_for_capture` never grants VPN access in S1 |
| Webhook notifications contain `type`, `event` and `object`; events include payment status events such as `payment.waiting_for_capture` and payment/refund events | <https://yookassa.ru/developers/using-api/webhooks> | Parse webhook identity from `object.id` + `event`; amount/currency/metadata and provider state must be rechecked before provisioning |
| YooKassa webhook delivery requires HTTP 200 acknowledgement; non-200 responses are retried for 24 hours. Authenticity should be checked by current object status and/or sender IP allowlist | <https://yookassa.ru/developers/using-api/webhooks> | No YooKassa webhook side effects until provider status/IP recheck is proven; duplicate delivery must not repeat side effects |
| Idempotency uses `Idempotence-Key` for POST/DELETE requests, max 64 characters, recommended UUID v4, and YooKassa keeps idempotency for 24 hours | <https://yookassa.ru/developers/using-api/interaction-format> | Use CyberVPN-side idempotency plus provider idempotency keys for create/capture/cancel/refund operations |
| Refunds are for successful `succeeded` payments, require `payment_id` and `amount`, use `Idempotence-Key`, and partial refund support depends on payment method | <https://yookassa.ru/developers/payment-acceptance/after-the-payment/refunds> | `refund.succeeded` is support/finance-reviewed and never grants access; refund evidence is required before YooKassa enablement |
| 54-FZ receipt/fiscalization can be handled through external online cash register or YooKassa receipts; receipt data must be sent for payment/refund when legally required | <https://yookassa.ru/developers/payment-acceptance/receipts/54fz/basics> and <https://yookassa.ru/developers/payment-acceptance/receipts/54fz/yoomoney/basics> | Russia public YooKassa path remains blocked until seller/fiscal/receipt decision and receipt evidence are attached |

## Local Contract Confirmed

| Area | Local result |
|---|---|
| Status mapping | `succeeded` and `payment.succeeded` map to `paid` and may provision after verification; `pending`, `waiting_for_capture`, `payment.waiting_for_capture`, `canceled` and `payment.canceled` do not grant automatic access |
| Two-stage capture | `waiting_for_capture` and `payment.waiting_for_capture` are support review / no-access states for S1 |
| Refund handling | `refund.succeeded` maps to `refunded`, requires support review and does not auto-grant access |
| Webhook authenticity | YooKassa webhooks are blocked as `requires_provider_recheck` until provider status/IP recheck is confirmed |
| Payload shape | Webhook-style `event` + `object.id` and status-poll `id` + `status` shapes are parsed into safe identities without exposing raw provider ids in idempotency keys |
| Duplicate webhook | Provider retries with a different notification id do not repeat wallet, subscription or provisioning side effects for the same YooKassa payment/status operation |
| Provider enablement | Documentation-only YooKassa samples do not enable the provider; synthetic provider-account samples require paid callback, non-success callback, status poll, provider recheck evidence and refund/reconciliation evidence |
| Secret safety | Tests and docs use synthetic/redacted values only; no YooKassa shop secret, API key, payment URL, full card data, idempotency key or raw provider snapshot is committed |

## 2026-05-08 Revalidation Notes

| Area | Result |
|---|---|
| Payment lifecycle contract | Official YooKassa docs still expose `pending`, `waiting_for_capture`, `succeeded` and `canceled`; CyberVPN S1 still treats only `succeeded` / `payment.succeeded` as normal automatic paid-access after all verification gates |
| Webhook contract | Official webhook docs still use `type`, `event` and `object`; relevant S1 events remain `payment.waiting_for_capture`, `payment.succeeded`, `payment.canceled` and `refund.succeeded` |
| Authenticity contract | Official webhook docs still require HTTP 200 acknowledgement and recommend current object status and/or IP validation; CyberVPN S1 requires provider status/IP recheck before side effects |
| Idempotency contract | Official API docs still require `Idempotence-Key` for POST/DELETE, max 64 chars, recommended UUID v4 and 24h provider retention; CyberVPN S1 also keeps internal operation-level idempotency |
| Refund contract | Official refund docs still require `payment_id`, amount and `Idempotence-Key`; `refund.succeeded` remains support/finance review and never grants access |
| Receipt/fiscal contract | 54-FZ receipt handling remains a Russia-path blocker; YooKassa cannot be exposed publicly in S1 until seller/fiscal/receipt evidence is attached |

## Files Added Or Used

```text
backend/tests/security/test_stage1_yookassa_readiness.py
backend/tests/security/test_stage1_provider_payment_status_mapping.py
backend/src/presentation/api/shared/stage1_payment_mapping.py
backend/src/presentation/api/shared/stage1_webhook_signature.py
backend/src/presentation/api/shared/stage1_webhook_idempotency.py
backend/src/presentation/api/shared/stage1_provider_evidence.py
backend/tests/fixtures/stage1_provider_evidence/provider_documentation_placeholders.json
```

## Verification Commands

| Check | Result |
|---|---|
| Official YooKassa docs recheck on 2026-05-08 | PASS: payment lifecycle, webhook events/authenticity, API idempotency, refund and receipt/fiscalization requirements reviewed from official YooKassa pages |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_yookassa_readiness.py -q --no-cov` | PASS: 7 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_yookassa_readiness.py tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_webhook_signature_verification.py tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_provider_placeholder_replacement.py tests/security/test_stage1_payment_provisioning_failure.py tests/security/test_stage1_orphan_payment_policy.py -q --no-cov` | PASS: 102 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check tests/security/test_stage1_yookassa_readiness.py src/presentation/api/shared/stage1_payment_mapping.py src/presentation/api/shared/stage1_webhook_signature.py src/presentation/api/shared/stage1_webhook_idempotency.py src/presentation/api/shared/stage1_provider_evidence.py` | PASS |
| Backend dependency audit | PASS: no known vulnerabilities found; local project package skipped because it is not on PyPI |
| Root npm dependency audit | PASS for high/critical issues; one moderate `postcss` advisory remains through the current Next.js dependency path and `npm audit fix --force` proposes a breaking downgrade path |
| High-confidence secret scan over S1-PAY-016 test/evidence/code files | PASS: no real YooKassa shop secret/API key/payment URL/idempotency key matches |
| Static dangerous-pattern scan over S1-PAY-016 test/evidence/code files | PASS: no `eval`, `exec`, `subprocess` or `shell=True` matches |
| `git diff --check` over touched S1-PAY-016 code/docs | PASS |
| Stale next-step scan for `S1-PAY-016` as current/next task | PASS: no stale current/next references in source docs after update |
| `docker ps --format '{{.Names}}\t{{.Status}}'` | INFO: no containers were started by `S1-PAY-016` |

## Real Evidence Still Required Before Enabling YooKassa

YooKassa must remain disabled or hidden for public paid flow until all items below are attached as redacted evidence:

1. YooKassa shop/account ownership and test/production environment inventory without secret values.
2. Shop id and secret key storage proof through the approved process, without committed values.
3. Test shop or production-low-value payment creation proof with stored CyberVPN order metadata and YooKassa `payment.id`.
4. Confirmation URL/return URL proof without exposing payment URLs in committed evidence.
5. Webhook registration proof for staging and production.
6. Real `payment.succeeded` webhook plus provider status/IP recheck evidence.
7. Real non-success webhook/status samples for `pending`, `waiting_for_capture`, `payment.waiting_for_capture`, `canceled` and `payment.canceled` where available.
8. Status-poll sample showing `payment.id`, amount, currency, metadata/order id and user/payment ownership validation.
9. Duplicate webhook proof showing no duplicate wallet transaction, subscription extension or provisioning job.
10. Payment -> Remnawave provisioning proof from a verified YooKassa `succeeded` state.
11. Real `refund.succeeded` or refund API sample with `payment_id`, amount, idempotency and finance/support workflow evidence.
12. Receipt/fiscalization decision for Russia path: external online cash register or YooKassa receipts, payment receipt data, refund receipt behavior and user email collection if required.
13. Admin/support payment-attempt view proof showing no raw shop secret, payment URL, full card data, provider snapshot or unredacted payment identifiers.
14. Alert/reconciliation evidence proving no YooKassa paid-but-no-access/orphan case remains older than 24h.

## Security Notes

- YooKassa shop secret is a provider secret and must never be stored in committed evidence.
- `payment.id` and metadata/order id are correlation keys; they must be matched to expected user, amount, currency and plan before provisioning.
- Webhook body alone is not trusted in S1. YooKassa processing requires current provider status/IP recheck evidence before side effects.
- `waiting_for_capture` is not a paid-access state for CyberVPN S1. Use one-stage `capture=true` unless owner explicitly approves a two-stage capture workflow with tests and support runbook.
- `refund.succeeded` is a support/finance state; access must be revoked or adjusted according to the approved refund policy.
- YooKassa Russia path is blocked until fiscalization/receipt obligations are explicitly resolved.

## Acceptance Result

`S1-PAY-016` is **completed locally** for YooKassa readiness guardrails.

YooKassa is still **not enabled for live paid beta** until real shop/account, credential, webhook, status-poll, refund/reconciliation, receipt/fiscalization and provisioning evidence is attached.

Next ID to execute after `S1-PAY-016`: `S1-AUTH-001` - public registration toggle.
