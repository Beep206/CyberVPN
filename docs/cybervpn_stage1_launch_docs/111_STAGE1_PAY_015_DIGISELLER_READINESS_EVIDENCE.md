> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-015`
> Статус: PASS for local/no-cost Digiseller readiness guardrails and 2026-05-08 official-doc revalidation. Real Digiseller seller account/product/callback/status/refund/reconciliation/provisioning evidence remains required before enablement.

# S1-PAY-015 Digiseller Readiness Evidence

## Purpose

`S1-PAY-015` verifies the CyberVPN S1 Digiseller Russia-path integration contract before Digiseller can be enabled as a paid provider.

This task does not make Digiseller production-ready. It proves that local backend guardrails match the currently documented Digiseller payment API shape and that documentation-only samples cannot enable the provider.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-014`. Digiseller official documentation was rechecked before this evidence refresh. The S1 local contract remains valid: only `paid` is the normal automatic paid-access status, `wait`/`canceled`/`error` never grant access, `refunded` goes to support/finance review, callback/status payloads require valid HMAC-SHA256 signature verification, and Digiseller remains disabled until real seller-account evidence exists.

## Official Digiseller Requirements Checked

| Requirement | Source | CyberVPN S1 rule |
|---|---|---|
| Digiseller payment status update uses `invoice_id`, `amount`, `currency`, `status` and `signature`; documented statuses are `paid`, `wait`, `canceled`, `refunded`, `error` | <https://my.digiseller.com/inside/api_payment.asp> | Only `paid` is the normal automatic paid-access status after signature, amount, currency and invoice checks |
| Digiseller payment status polling returns the same invoice/payment fields and status values | <https://my.digiseller.com/inside/api_payment.asp> | Poll/reconcile by invoice id and expected CyberVPN payment record before provisioning or resolving an orphan |
| Digiseller payment and status APIs use seller-configured callback/status URLs; payment/status fields include `invoice_id`, amount, currency and seller/account context | <https://my.digiseller.com/inside/api_payment.asp> | S1 must validate expected CyberVPN payment, product, amount, currency, seller/account and environment before provisioning |
| Digiseller payment currency values in the documented callback/status contract are `USD`, `RUB` and `EUR` | <https://my.digiseller.com/inside/api_payment.asp> | S1 must reject mismatched amount/currency/product for the CyberVPN order; `RUB` exposure remains Russia-path only |
| Digiseller signature uses SHA256 HMAC over alphabetically sorted `key:value;` pairs with the seller secret; documented non-signed fields are excluded | <https://my.digiseller.com/inside/api_payment.asp> | Reject missing/invalid `payload.signature` before idempotency or paid-access side effects |
| Digiseller API token flow and invoice lookup require seller identity/API permissions; invoice id should be stored and checked for uniqueness | <https://my.digiseller.com/inside/api_general.asp> | Real seller/account evidence, token/permission proof and invoice uniqueness/idempotency evidence are required before enabling the Russia path |
| Digiseller invoice state API includes expected payment, cancellation, successful payment, overdue and refund states | <https://my.digiseller.com/inside/api_general.asp> | Status-poll and reconciliation evidence must cover success, non-success and refund/manual-support cases |
| Digiseller refund policy for delivered digital goods is dispute-driven; quick unconditional refunds are not guaranteed, and seller funds may be held before payout | <https://www.digiseller.com/refundpolicy> | Refunds/disputes are finance/support-reviewed in S1; `refunded` never grants automatic VPN access |

## Local Contract Confirmed

| Area | Local result |
|---|---|
| Status mapping | `paid` maps to `paid` and may provision after verification; `wait`, `canceled`, `error` and unknown statuses do not grant automatic access |
| Refund handling | `refunded` maps to support review and does not auto-grant access |
| Callback authenticity | Digiseller callback/status payload is accepted only when `signature` matches HMAC-SHA256 over sorted signed fields using the configured seller secret |
| Payload shape | Callback-style `invoice_id` + `status` and status-poll `inv` + `payment_status` shapes produce the same operation idempotency key |
| Duplicate callbacks | Provider retries with a different callback id do not repeat wallet, subscription or provisioning side effects for the same Digiseller invoice/status |
| Provider enablement | Documentation-only Digiseller samples do not enable the provider; synthetic provider-account samples require paid callback, non-success callback, status poll, signature verification and refund/reconciliation evidence |
| Secret safety | Tests and docs use synthetic/redacted values only; no Digiseller seller secret, API key, token, checkout URL, raw signature or provider snapshot is committed |

## 2026-05-08 Revalidation Notes

| Area | Result |
|---|---|
| Status contract | Official Digiseller docs still expose `paid`, `wait`, `canceled`, `refunded` and `error`; CyberVPN S1 still treats only `paid` as normal automatic paid-access after all verification gates |
| Signature contract | Official Digiseller docs still define SHA256 HMAC over alphabetically sorted `key:value;` pairs; local verifier keeps non-signed fields excluded and redacts raw secrets/signatures from safe output |
| Amount/currency/product contract | Official Digiseller docs still expose `USD`, `RUB` and `EUR`; CyberVPN S1 requires exact expected amount/currency/product match before provisioning |
| Seller/API contract | Token and invoice lookup remain seller-account/API-permission dependent; provider-account samples cannot be replaced by documentation placeholders |
| Refund/dispute contract | Digiseller refunds for delivered digital goods remain support/dispute driven; `refunded` never grants automatic VPN access |
| Enablement contract | Digiseller remains hidden/disabled until seller account, product, credential, callback/status-poll, refund/reconciliation and payment-to-provisioning evidence is attached |

## Files Added Or Used

```text
backend/tests/security/test_stage1_digiseller_readiness.py
backend/src/presentation/api/shared/stage1_payment_mapping.py
backend/src/presentation/api/shared/stage1_webhook_signature.py
backend/src/presentation/api/shared/stage1_webhook_idempotency.py
backend/src/presentation/api/shared/stage1_provider_evidence.py
backend/tests/fixtures/stage1_provider_evidence/provider_documentation_placeholders.json
```

## Verification Commands

| Check | Result |
|---|---|
| Official Digiseller docs recheck on 2026-05-08 | PASS: payment callback/status, signature, token/invoice lookup and refund-policy requirements reviewed from official Digiseller pages |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_digiseller_readiness.py -q --no-cov` | PASS: 7 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_digiseller_readiness.py tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_webhook_signature_verification.py tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_provider_placeholder_replacement.py tests/security/test_stage1_payment_provisioning_failure.py tests/security/test_stage1_orphan_payment_policy.py -q --no-cov` | PASS: 102 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check tests/security/test_stage1_digiseller_readiness.py src/presentation/api/shared/stage1_payment_mapping.py src/presentation/api/shared/stage1_webhook_signature.py src/presentation/api/shared/stage1_webhook_idempotency.py src/presentation/api/shared/stage1_provider_evidence.py` | PASS |
| Backend dependency audit | PASS: no known vulnerabilities found; local project package skipped because it is not on PyPI |
| Root npm dependency audit | PASS for high/critical issues; one moderate `postcss` advisory remains through the current Next.js dependency path and `npm audit fix --force` proposes a breaking downgrade path |
| High-confidence secret scan over S1-PAY-015 test/evidence/code files | PASS: no real Digiseller seller secret/API key/token/signature URL matches |
| Static dangerous-pattern scan over S1-PAY-015 test/evidence/code files | PASS: no `eval`, `exec`, `subprocess` or `shell=True` matches |
| `git diff --check` over touched S1-PAY-015 code/docs | PASS |
| Stale next-step scan for `S1-PAY-015` as current/next task | PASS: no stale current/next references in source docs after update |
| `docker ps --format '{{.Names}}\t{{.Status}}'` | INFO: no containers were started by `S1-PAY-015` |

## Real Evidence Still Required Before Enabling Digiseller

Digiseller must remain disabled or hidden for public paid flow until all items below are attached as redacted evidence:

1. Digiseller seller account ownership and environment inventory without secret values.
2. Digiseller product/payment model for VPN subscription delivery, including whether Digiseller delivers a digital item/code, redirects to CyberVPN, or only acts as a paid status source.
3. Seller secret/API key/token storage proof through the approved process, without committed values.
4. Staging and production callback/status URL registration proof.
5. Real `paid` callback/status sample with valid `signature`.
6. Real non-success callback/status samples for `wait`, `canceled`, `error` and unknown/unmapped provider cases where available.
7. Real `refunded` or refund/dispute sample and support/finance workflow transcript.
8. Status-poll or invoice lookup sample showing invoice id, amount, currency, seller/account and CyberVPN payment correlation.
9. Duplicate callback/status proof showing no duplicate wallet transaction, subscription extension or provisioning job.
10. Payment -> Remnawave provisioning proof from a Digiseller `paid` callback/status.
11. Admin/support payment-attempt view proof showing no raw seller secret, API token, callback signature, checkout URL, provider snapshot or unredacted buyer/account data.
12. Alert/reconciliation evidence proving no Digiseller paid-but-no-access/orphan case remains older than 24h.
13. Russia-path legal/fiscal/seller-operational evidence if Digiseller is exposed to users from Russia in S1.

## Security Notes

- Digiseller seller secret/API key/token are provider secrets and must never be stored in committed evidence.
- `invoice_id` is the provider payment correlation key; it must be matched to expected user, amount, currency and product before provisioning.
- `paid` does not bypass signature verification, idempotency, support/orphan policy or payment -> provisioning failure handling.
- `refunded`, disputes, negative feedback and delivered-digital-goods refund cases remain finance/support review cases for S1.
- Digiseller is a Russia-path provider for CyberVPN S1; it must stay feature-flagged separately from the first live paid rail unless its own evidence is complete.

## Acceptance Result

`S1-PAY-015` is **completed locally** for Digiseller readiness guardrails.

Digiseller is still **not enabled for live paid beta** until real seller account, product, credential, callback, status-poll, refund/reconciliation and provisioning evidence is attached.

Next ID to execute after `S1-PAY-015`: `S1-PAY-016` - YooKassa Russia path readiness if enabled.
