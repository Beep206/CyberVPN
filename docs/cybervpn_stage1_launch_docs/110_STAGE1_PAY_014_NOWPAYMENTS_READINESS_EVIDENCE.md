> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-08
> Backlog ID: `S1-PAY-014`
> Статус: PASS for local/no-cost NOWPayments readiness guardrails and 2026-05-08 official-doc revalidation. Real NOWPayments account/credential/IPN/refund/reconciliation evidence remains required before enablement.

# S1-PAY-014 NOWPayments Readiness Evidence

## Purpose

`S1-PAY-014` verifies the CyberVPN S1 NOWPayments integration contract before NOWPayments can be enabled as a paid provider.

This task does not make NOWPayments production-ready. It proves that local backend guardrails match the currently documented NOWPayments API/IPN shape and that documentation-only samples cannot enable the provider.

Revalidated on 2026-05-08 as the active execution step after `S1-PAY-013`. NOWPayments documentation was rechecked against the current HelpCenter/API docs. The S1 local contract remains valid: create direct payments or invoices with `x-api-key`, use `ipn_callback_url` for callbacks, verify `x-nowpayments-sig` with HMAC-SHA512 over sorted JSON, treat `finished` as the only normal automatic paid-access status, and route `partially_paid`, wrong-asset/wrong-network, refund and non-final states to reconciliation/support. NOWPayments stays disabled for live S1 until real provider-account evidence is attached.

## Official NOWPayments Requirements Checked

| Requirement | Source | CyberVPN S1 rule |
|---|---|---|
| Direct payment creation uses `POST /payment`, `x-api-key`, `price_amount`, `price_currency`, optional `pay_currency`, `ipn_callback_url` and `order_id`; response includes `payment_id` and deposit address | <https://nowpayments.zendesk.com/hc/en-us/articles/21345824322717-API-and-endpoint-description> | Store CyberVPN payment id against NOWPayments `payment_id` and `order_id`; never commit API key, invoice URL, deposit address or raw provider snapshot |
| Payment status polling uses `GET /payment/:payment_id` with `x-api-key` | <https://nowpayments.zendesk.com/hc/en-us/articles/21345824322717-API-and-endpoint-description> | Reconcile provider status against expected user, amount, currency and order before provisioning |
| IPN callbacks are POST requests, require a public endpoint, include `x-nowpayments-sig` and use body similar to payment-status response | <https://nowpayments.zendesk.com/hc/en-us/articles/21395546303389-IPN-and-how-to-setup> | Reject missing/invalid IPN signature before idempotency or paid-access side effects |
| IPN signature uses HMAC SHA-512 over sorted JSON with the IPN secret | <https://nowpayments.zendesk.com/hc/en-us/articles/21395546303389-IPN-and-how-to-setup> | Verify recursively sorted JSON HMAC-SHA512 using configured IPN secret |
| `finished` is completed; `waiting`, `confirming`, `confirmed` and `sending` are not clean paid final states for CyberVPN access | <https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses> | Only `finished` is normal automatic paid-access status |
| `partially_paid` means funds were received but underpaid; NOWPayments recommends not granting goods/services by default for this status when exact amount matters | <https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses> | `partially_paid` never grants automatic VPN access in S1; support/finance review required |
| Wrong-asset/wrong-network and refund/validation cases need merchant/support handling and may require provider validation | <https://nowpayments.zendesk.com/hc/en-us/articles/18316629513757-Refunds-and-Validation-flow> | Wrong-asset, refund and validation flows remain manual support/finance/reconciliation cases |
| NOWPayments integration setup requires base currency, IPN secret and callback setup; payout safety controls include IP allowlisting, wallet allowlisting and 2FA | <https://nowpayments.zendesk.com/hc/en-us/articles/21341613323421-NOWPayments-Integration-Guide> | Account setup, IPN secret, payout safety controls and callback proof are external evidence blockers before enablement |
| NOWPayments documents create-payment rate limits | <https://nowpayments.zendesk.com/hc/en-us/articles/21395546303389-IPN-and-how-to-setup> | S1 must keep checkout creation rate-limited and must not retry create-payment aggressively |

## Local Contract Confirmed

| Area | Local result |
|---|---|
| Status mapping | `finished` maps to `paid` and may provision after verification; waiting/confirming/confirmed/sending are not paid; partial/wrong-asset/refunded states require review |
| Partial/wrong-asset policy | `partially_paid` and `wrong_asset_confirmed` are support/reconciliation states and do not auto-grant access |
| IPN authenticity | NOWPayments IPN is accepted only when `x-nowpayments-sig` matches HMAC-SHA512 over recursively sorted JSON using the configured IPN secret |
| Payload shape | IPN-style `payment_id` + `payment_status` and status-poll `paymentId` + `paymentStatus` shapes produce the same operation idempotency key |
| Duplicate IPN | Provider retries with a different IPN id do not repeat wallet, subscription or provisioning side effects for the same NOWPayments payment/status |
| Provider enablement | Documentation-only NOWPayments samples do not enable the provider; synthetic provider-account samples require paid callback, non-success callback, status poll, signature verification and refund/reconciliation evidence |
| Secret safety | Tests and docs use synthetic/redacted values only; no NOWPayments API key, IPN secret, payment URL, deposit address or raw provider snapshot is committed |

## Files Added Or Used

```text
backend/tests/security/test_stage1_nowpayments_readiness.py
backend/src/presentation/api/shared/stage1_payment_mapping.py
backend/src/presentation/api/shared/stage1_webhook_signature.py
backend/src/presentation/api/shared/stage1_webhook_idempotency.py
backend/src/presentation/api/shared/stage1_provider_evidence.py
backend/tests/fixtures/stage1_provider_evidence/provider_documentation_placeholders.json
```

## Verification Commands

| Check | Result |
|---|---|
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_nowpayments_readiness.py -q --no-cov` | PASS: 7 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_nowpayments_readiness.py tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_webhook_signature_verification.py tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_provider_placeholder_replacement.py tests/security/test_stage1_payment_provisioning_failure.py tests/security/test_stage1_orphan_payment_policy.py -q --no-cov` | PASS: 102 tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run ruff check tests/security/test_stage1_nowpayments_readiness.py src/presentation/api/shared/stage1_payment_mapping.py src/presentation/api/shared/stage1_webhook_signature.py src/presentation/api/shared/stage1_webhook_idempotency.py src/presentation/api/shared/stage1_provider_evidence.py` | PASS |
| Official NOWPayments docs recheck | PASS: payment statuses, API/endpoints, IPN setup and integration guide reviewed on 2026-05-08 |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable backend` | PASS: no known vulnerabilities found |
| `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate `postcss` advisory via Next remains tracked and was not force-fixed because the proposed path is breaking |
| High-confidence secret scan over new S1-PAY-014 test/evidence files | PASS: no matches |
| Static dangerous-pattern scan over new S1-PAY-014 test/evidence files | PASS: no matches |
| `git diff --check` over touched S1-PAY-014 code/docs | PASS |
| Stale next-step scan for `S1-PAY-014` as current/next task | PASS: no stale current/next references in source docs after update |
| `docker ps --format '{{.Names}}\t{{.Status}}'` | PASS: no running containers; `S1-PAY-014` did not start or require containers |

## 2026-05-08 Revalidation Notes

| Area | Result |
|---|---|
| Payment creation/status API | Current docs still require `x-api-key`; `POST /payment` returns `payment_id`; `GET /payment/:payment_id` is the payment-status endpoint |
| IPN authenticity | Current docs still require `x-nowpayments-sig` and HMAC-SHA512 over sorted JSON with the IPN secret |
| Status mapping | Current docs list `waiting`, `confirming`, `confirmed`, `sending`, `partially_paid`, `cancelled`, `finished`, `failed`, `expired` and wrong-asset handling; S1 only grants normal automatic access on `finished` |
| Partial/wrong-asset posture | NOWPayments explicitly warns not to grant goods/services by default for `partially_paid` when exact amount matters; CyberVPN S1 exact-price subscriptions keep this in support/reconciliation |
| Enablement | Documentation-only samples still cannot enable NOWPayments; real provider-account samples are required for IPN, status poll, signature verification and refund/reconciliation |

## Real Evidence Still Required Before Enabling NOWPayments

NOWPayments must remain disabled or hidden for public paid flow until all items below are attached as redacted evidence:

1. NOWPayments account ownership and environment inventory without secret values.
2. Sandbox/test-mode or production-low-value payment creation proof with stored `payment_id` and `order_id`.
3. Staging and production `ipn_callback_url` registration proof.
4. Real `finished` IPN sample with valid `x-nowpayments-sig`.
5. Real non-success IPN/status samples for `waiting`, `confirming`, `confirmed`, `sending`, `failed`, `expired` and `cancelled/canceled` where available.
6. Real `partially_paid` or provider dashboard setting proof showing underpaid handling is not auto-finished for CyberVPN exact-price subscriptions.
7. Real wrong-asset/wrong-network validation or manual continuation/refund policy proof.
8. Status-poll sample showing amount/currency/payment_id/order_id validation against CyberVPN records.
9. Duplicate IPN proof showing no duplicate wallet transaction, subscription extension or provisioning job.
10. Payment -> Remnawave provisioning proof from a NOWPayments `finished` IPN.
11. Admin/support payment-attempt view proof showing no raw API keys, IPN secrets, payment URLs, deposit addresses, provider snapshots or unredacted references.
12. Alert/reconciliation evidence proving no NOWPayments paid-but-no-access/orphan case remains older than 24h.
13. Final production secret inventory with NOWPayments API key and IPN secret stored through the approved process.

## Security Notes

- NOWPayments `x-api-key` and IPN secret are provider secrets and must never be stored in committed evidence.
- `payment_id` / `order_id` are correlation keys; they must be matched to expected user, amount and currency before provisioning.
- `finished` does not bypass idempotency, support/orphan policy or payment -> provisioning failure handling.
- `partially_paid`, `wrong_asset_confirmed` and `refunded` remain finance/support review cases for S1.
- NOWPayments recurring/custodial flows are not promised in S1; manual renewal and invoice/payment links remain the S1 posture.

## Acceptance Result

`S1-PAY-014` is **completed locally** for NOWPayments readiness guardrails.

NOWPayments is still **not enabled for live paid beta** until real account, credential, IPN, status-poll, refund/reconciliation and provisioning evidence is attached.

Next ID to execute after `S1-PAY-014`: `S1-PAY-015` - Digiseller Russia path readiness if enabled.
