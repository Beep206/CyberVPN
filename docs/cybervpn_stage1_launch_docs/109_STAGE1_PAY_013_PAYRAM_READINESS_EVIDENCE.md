> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-013`
> Статус: PASS for local/no-cost PayRam readiness guardrails and 2026-05-08 official-doc revalidation. Real PayRam instance/account/credential/callback/refund/reconciliation evidence remains required before enablement.

# S1-PAY-013 PayRam Readiness Evidence

## Purpose

`S1-PAY-013` verifies the CyberVPN S1 PayRam integration contract before PayRam can be enabled as a paid provider.

This task does not make PayRam production-ready. It proves that local backend guardrails match the currently documented PayRam API shape and that documentation-only samples cannot enable the provider.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-011`. PayRam documentation was rechecked against the current GitBook docs. The S1 local contract remains valid: create payment through `/api/v1/payment`, store PayRam `reference_id`, verify every callback/webhook with the project `API-Key`, treat `FILLED` as the only normal paid-access status, and route underpaid/overpaid/non-final states to reconciliation/support. PayRam stays disabled for live S1 until real provider-instance evidence is attached.

## Official PayRam Requirements Checked

| Requirement | Source | CyberVPN S1 rule |
|---|---|---|
| PayRam is self-hosted and crypto-only; fiat handling is not native by default | <https://docs.payram.com/faqs/general-faqs> | Treat PayRam as a crypto payment rail, not fiat/autoprolongation provider |
| Payment creation uses `/api/v1/payment`, `API-Key`, customer identity and `amountInUSD`; response includes `reference_id` and payment URL | <https://docs.payram.com/api-integration/payments-api/create-payment> and <https://docs.payram.com/support/faq/api-integration-faqs> | Store CyberVPN payment id against PayRam `reference_id`; never commit or expose API key/payment URL in evidence |
| Status polling uses `/api/v1/payment/reference/{reference_id}` and `paymentState` / `payment_state` statuses | <https://docs.payram.com/api-integration/payments-api/payment-status>, <https://docs.payram.com/api-integration/custom-api-integration> and <https://docs.payram.com/support/faq/api-integration-faqs> | `FILLED` is the only normal paid-access status; `OPEN`, `CANCELLED/CANCELED`, `PARTIALLY_FILLED`, `OVER_FILLED` are non-auto or review states |
| PayRam webhooks are sent as callbacks to merchant endpoint and include payment details; docs show webhook `GET`, while SDK examples expose framework handlers | <https://docs.payram.com/api-integration/payments-api/webhook>, <https://docs.payram.com/introduction/getting-started/webhook-integration> and <https://docs.payram.com/payram-sdk/typescript-javascript-sdk> | Treat method/framework differences as integration details; parse callback payload only after authenticity check and reference/amount/currency validation |
| Webhook security uses the project `API-Key` header and must be matched server-side | <https://docs.payram.com/support/faq/api-integration-faqs> and <https://docs.payram.com/payram-sdk/typescript-javascript-sdk> | Reject missing/invalid `API-Key` before idempotency or paid-access side effects |
| Refunds have no automatic on-chain chargeback path and are processed manually through dashboard/API | <https://docs.payram.com/faqs/general-faqs> | Refund/dispute handling remains finance/support-reviewed and provider-specific evidence is still required |
| Underpayments/overpayments require reconciliation behavior | <https://docs.payram.com/faqs/general-faqs> | Underpaid never grants access; overpaid is blocked by default unless explicit policy plus amount evidence accepts it, while support review stays open |

## Local Contract Confirmed

| Area | Local result |
|---|---|
| Status mapping | `FILLED` maps to `paid` and may provision after verification; `OPEN`, `PARTIALLY_FILLED`, `OVER_FILLED`, `CANCELLED/CANCELED` do not grant ordinary paid access |
| Overpayment policy | `OVER_FILLED` is manual review by default; optional auto-access requires explicit policy and valid expected/received amount evidence |
| Webhook authenticity | PayRam callback is accepted only when `API-Key` matches the configured project key; missing/invalid header fails closed |
| Payload shape | Both webhook-style `reference_id` + `status` and status-poll `referenceID` + `paymentState` shapes produce the same operation idempotency key |
| Duplicate callbacks | Provider retries with a different callback id do not repeat wallet, subscription or provisioning side effects for the same PayRam reference/status |
| Provider enablement | Documentation-only PayRam samples do not enable the provider; synthetic provider-account samples require paid callback, non-success callback, status poll, signature verification and refund/reconciliation evidence |
| Secret safety | Tests and docs use synthetic/redacted values only; no PayRam API key, payment URL or raw provider snapshot is committed |

## Files Added Or Used

```text
backend/tests/security/test_stage1_payram_readiness.py
backend/src/presentation/api/shared/stage1_payment_mapping.py
backend/src/presentation/api/shared/stage1_webhook_signature.py
backend/src/presentation/api/shared/stage1_webhook_idempotency.py
backend/src/presentation/api/shared/stage1_provider_evidence.py
backend/tests/fixtures/stage1_provider_evidence/provider_documentation_placeholders.json
```

## Verification Commands

| Check | Result |
|---|---|
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_payram_readiness.py -q --no-cov` | PASS: 7 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_payram_readiness.py tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_webhook_signature_verification.py tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_provider_placeholder_replacement.py tests/security/test_stage1_payment_provisioning_failure.py tests/security/test_stage1_orphan_payment_policy.py -q --no-cov` | PASS: 102 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check tests/security/test_stage1_payram_readiness.py src/presentation/api/shared/stage1_payment_mapping.py src/presentation/api/shared/stage1_webhook_signature.py src/presentation/api/shared/stage1_webhook_idempotency.py src/presentation/api/shared/stage1_provider_evidence.py` | PASS |
| Official PayRam docs recheck | PASS: create-payment, status-poll, webhook, FAQ and SDK docs reviewed on 2026-05-08 |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory via Next remains tracked and was not force-fixed because the proposed path is breaking |
| High-confidence secret scan over new S1-PAY-013 test/evidence files | PASS: no matches |
| Static dangerous-pattern scan over new S1-PAY-013 test/evidence files | PASS: no matches |
| `git diff --check` over touched S1-PAY-013 code/docs | PASS |
| Stale next-step scan for `S1-PAY-013` as current/next task | PASS: no stale current/next references in source docs after update |
| `docker ps --format '{{.Names}}\t{{.Status}}'` | PASS: no running containers; `S1-PAY-013` did not start or require containers |

## 2026-05-08 Revalidation Notes

| Area | Result |
|---|---|
| Create payment contract | Current docs still require `API-Key`, `customerEmail`, `customerID`/`customerId`, `amountInUSD`; response still includes `reference_id` and a payment `url` |
| Status contract | Current docs list `OPEN`, `CANCELLED`, `FILLED`, `PARTIALLY_FILLED`, `OVER_FILLED`; S1 accepts `CANCELED` alias defensively |
| Webhook contract | Docs confirm merchant callback/webhook delivery with PayRam payment details and `API-Key` verification requirement |
| SDK contract | SDK docs expose `initiatePayment`, `getPaymentRequest`, webhook helpers and `verifyApiKey`; S1 keeps custom backend guardrails instead of depending on SDK runtime |
| S1 enablement | Documentation-only samples still cannot enable PayRam; provider-account samples are required for callback, status poll, API-key verification and refund/reconciliation |

## Real Evidence Still Required Before Enabling PayRam

PayRam must remain disabled or hidden for public paid flow until all items below are attached as redacted evidence:

1. PayRam instance/account ownership and environment inventory without secret values.
2. Sandbox/testnet or production-low-value payment creation proof with stored `reference_id`.
3. Callback URL registration proof for staging and production.
4. Real success callback sample for `FILLED` after `API-Key` verification.
5. Real non-success callback/status samples for `OPEN`, `CANCELLED/CANCELED`, `PARTIALLY_FILLED` and `OVER_FILLED` where available.
6. Status-poll sample showing amount/currency/reference validation against CyberVPN records.
7. Duplicate callback or retry proof showing no duplicate wallet transaction, subscription extension or provisioning job.
8. Payment -> Remnawave provisioning proof from a PayRam paid callback.
9. Manual refund/reconciliation evidence for underpaid, overpaid or refunded PayRam cases.
10. Admin/support payment-attempt view proof showing no raw API keys, payment URLs, provider snapshots or unredacted references.
11. Alert/reconciliation evidence proving no PayRam paid-but-no-access/orphan case remains older than 24h.
12. Final production secret inventory with PayRam API keys stored through the approved process.

## Security Notes

- PayRam `API-Key` is treated as a provider secret and must never be stored in committed evidence.
- `reference_id` / `referenceID` is the CyberVPN payment correlation key; it must be matched to expected user, amount and currency before provisioning.
- `FILLED` does not bypass idempotency, support/orphan policy or payment -> provisioning failure handling.
- `PARTIALLY_FILLED` and `OVER_FILLED` remain finance/support review cases for S1.
- PayRam recurring billing is not promised in S1; manual renewal and invoice links remain the S1 posture.

## Acceptance Result

`S1-PAY-013` is **completed locally** for PayRam readiness guardrails.

PayRam is still **not enabled for live paid beta** until real PayRam instance/account, credential, callback, status-poll, refund/reconciliation and provisioning evidence is attached.

Next ID to execute after `S1-PAY-013`: `S1-PAY-014` - NOWPayments readiness if enabled.
