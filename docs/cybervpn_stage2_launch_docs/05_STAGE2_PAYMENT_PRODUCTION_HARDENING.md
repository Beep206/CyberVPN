# Stage 2 Payment Production Hardening

**Stage:** `S2-STAGE-06`
**Status:** Approved local hardening baseline
**Date:** 2026-05-22
**Product stage:** CyberVPN Public Release 1.0

---

## 1. Purpose

This document freezes the S2 payment production contract before wider public B2C sale.

The goal is not to enable every provider at once. The goal is to make one primary payment path reliable, observable and supportable, while keeping secondary providers and growth/payment features behind explicit evidence gates.

---

## 2. Primary And Secondary Payment Paths

| Path | S2 state | Runtime rule |
|---|---|---|
| CryptoBot / Crypto Pay | Primary S2 candidate | May be enabled for public B2C only with production token, signed webhook route, duplicate webhook proof, reconciliation proof and support refund/intake process |
| Telegram Stars | Secondary Telegram-only path | May be enabled only inside Telegram Bot / Mini App paid flow; no generic web checkout and no wallet/add-on mixing |
| PayRam | Conditional | Keep disabled until production account, credential storage, callback proof, status mapping proof, refund/support proof and reconciliation proof exist |
| NOWPayments | Conditional | Keep disabled until production account, credential storage, IPN proof, status mapping proof, wrong-asset/partial-payment support process and reconciliation proof exist |
| Digiseller | Conditional RU path | Keep disabled until account, product/callback proof, refund proof and country/payment routing proof exist |
| YooKassa | Conditional RU path | Keep disabled until legal seller, shop credentials, payment/recheck proof, refund proof and fiscal/legal obligations are approved |

S2 launch should not depend on all providers. The minimum S2 public-payment gate is one reliable live path plus a manual/support-safe fallback policy.

---

## 3. Runtime Switch Contract

Safe default before S2 payment opening:

```text
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=false
PAYMENT_RECONCILIATION_ENABLED=true
PAYMENT_AUTORENEWAL_ENABLED=false
REFERRAL_ENABLED=false
PROMO_CODES_ENABLED=false
GIFT_CODES_ENABLED=false
CHECKOUT_CODE_DISCOUNTS_ENABLED=false
```

Payment canary posture after provider evidence:

```text
PAYMENTS_ENABLED=true
TELEGRAM_STARS_ENABLED=false or true only for Telegram Bot/Mini App
PAYMENT_RECONCILIATION_ENABLED=true
PAYMENT_AUTORENEWAL_ENABLED=false
```

Growth/payment features remain separate:

| Feature | S2 rule |
|---|---|
| Referral rewards | Allowed only after reward idempotency, refund reversal and abuse evidence |
| Promo checkout discounts | Allowed only after stacking, refund, reconciliation and abuse evidence |
| Gift purchase/redeem | Allowed only after payment ownership, delivery, redeem idempotency, refund and support reversal evidence |
| Autoprolongation | Stays disabled in `S2-STAGE-06`; lifecycle belongs to `S2-STAGE-07` |

---

## 4. Final Status Contract

The production code keeps the S1 provider status resolver as the canonical payment-state mapper for S2 unless a provider-specific S2 adapter supersedes it with evidence.

| Provider | Paid/final statuses allowed to provision access | Non-paid/review examples | Refund/reversal handling |
|---|---|---|---|
| PayRam | `FILLED` | `OPEN`, `PARTIALLY_FILLED`, `OVER_FILLED`, `CANCELLED` | Manual/provider support mode until refund evidence |
| NOWPayments | `finished` | `waiting`, `confirming`, `confirmed`, `sending`, `partially_paid`, `wrong_asset_confirmed`, `failed`, `expired` | `refunded` requires support/finance review |
| CryptoBot | `paid`, `invoice_paid` | `active`, `expired` | Manual finance review by default |
| Telegram Stars | `successful_payment` | `invoice_sent`, `pre_checkout_query`, `payment_timeout` | `refund_succeeded` requires access adjustment/review |
| Digiseller | `paid` | `wait`, `canceled`, `error` | `refunded` requires support/finance review |
| YooKassa | `succeeded`, `payment.succeeded` | `pending`, `waiting_for_capture`, `payment.waiting_for_capture`, `canceled`, `payment.canceled` | `refund.succeeded` requires access adjustment/review |

Unknown future provider statuses must not grant access automatically. They must resolve to reconciliation/manual review.

---

## 5. Webhook Signature And Idempotency Contract

S2 payment webhooks must fail closed before side effects.

Implemented hardening:

1. CryptoBot webhook route verifies `crypto-pay-api-signature` before the payment use-case runs.
2. CryptoBot webhook route now passes Redis/Valkey into `CryptoBotWebhookHandler`.
3. `ProcessPaymentWebhookUseCase` now calls full payment validation for CryptoBot invoice terminal events:
   - signature validation;
   - numeric invoice-id format validation;
   - Redis duplicate invoice check.
4. Duplicate paid invoice events return `already_processed` and do not repeat paid-access side effects.
5. Database terminal state remains the authoritative fallback if Redis idempotency is unavailable.
6. Unknown `payment_not_found` paid invoice events are not marked as processed in Redis, so they can remain visible for orphan/manual review instead of being silently closed.
7. Failure/expired/cancelled events are not written to the paid-invoice idempotency key, so a late provider success cannot be suppressed by an earlier failed-state callback.

Relevant code paths:

```text
backend/src/presentation/api/v1/webhooks/routes.py
backend/src/application/use_cases/payments/payment_webhook.py
backend/src/infrastructure/payments/cryptobot/webhook_handler.py
backend/tests/security/test_stage2_payment_production_hardening.py
```

---

## 6. Orphan And Paid-But-No-Access Policy

S2 keeps the S1 hard rule:

```text
No paid-but-no-access or orphan payment item may remain unresolved older than 24 hours.
```

Operational thresholds:

| Age | State | Required action |
|---:|---|---|
| `0-15m` | manual review | Create review item/support context |
| `15m+` | alert | Alert support/finance |
| `60m+` | P1 escalation | Support/ops escalation |
| `24h+` | P0 blocker | Public payment expansion must stop until owner action |

Safe identifiers only:

```text
safe payment reference
payment attempt id
order id
user id
support ticket reference
provider name
provider status
```

Do not expose raw provider payloads, full payment URLs, webhook signatures, provider secrets or private VPN material in support output.

---

## 7. Reconciliation And Dashboard Contract

S2 payment reconciliation is mandatory whenever payments are enabled.

Required surfaces:

| Surface | Path |
|---|---|
| Internal reconciliation run | `POST /api/v1/payments/internal/reconciliation/run` |
| Reconciliation use-case | `backend/src/application/use_cases/payments/stage1_reconciliation.py` |
| Grafana dashboard | `infra/grafana/dashboards/stage2-payment-reconciliation-dashboard.json` |
| Alert rules | `infra/prometheus/rules/stage2_analytics_alerts.yml` and existing Stage 1 payment alerts |

Dashboard panels currently cover:

1. payment success ratio over 24h;
2. payment failures over 24h;
3. current paid-but-no-access count;
4. max reconciliation age;
5. payment results by status;
6. webhook failures and retries;
7. reconciliation findings by severity;
8. payment/reconciliation error logs.

---

## 8. Refund And Dispute Handling

S2 keeps refunds support-operated unless a provider-specific refund API path is proven.

| Provider | S2 refund mode |
|---|---|
| CryptoBot | manual finance review |
| Telegram Stars | Telegram Stars API after evidence |
| PayRam | provider support/manual payout |
| NOWPayments | provider support/manual payout |
| Digiseller | provider API after evidence |
| YooKassa | provider API after evidence |

Support may intake refund/dispute cases. Only finance/admin/super-admin/owner roles may change financial refund/dispute state. Admin 2FA remains required.

---

## 9. Customer-Facing Copy Rules

Do not show or imply these until the matching evidence exists:

1. automatic renewal;
2. saved recurring payment method;
3. instant refund guarantee;
4. every country/provider accepted;
5. promo/gift/referral discounts as part of checkout;
6. payment-provider support outside approved channels.

Allowed S2 wording:

```text
Manual renewal is available.
Payment status can take time to update.
If payment succeeded but access is not ready, support will review it.
Telegram Stars are available only inside Telegram flows.
```

---

## 10. No-Go Conditions

Do not open wider public payments if any condition is true:

1. primary provider production credential is missing;
2. webhook signature validation is disabled or bypassed;
3. duplicate webhook idempotency is untested;
4. provider paid status is unknown or unmapped;
5. paid-but-no-access/orphan item can exceed 24h without escalation;
6. reconciliation job/dashboard is unavailable;
7. support cannot identify payment state without developer DB access;
8. refund process is unclear to support/finance;
9. Telegram Stars leaks into generic web checkout;
10. autoprolongation copy appears while `PAYMENT_AUTORENEWAL_ENABLED=false`.

---

## 11. Acceptance Evidence

Completed checks for this stage:

| Check | Result |
|---|---|
| CryptoBot route Redis idempotency wiring | Added |
| CryptoBot invoice-id validation before side effects | Added |
| Duplicate CryptoBot paid webhook suppression | Added |
| Orphan `payment_not_found` not silently closed | Added |
| Provider final status mapping | Existing resolver verified |
| Signature/idempotency/orphan/refund tests | Passed targeted security suite |
| Route-level payment integration | Passed with local PostgreSQL/Redis |

Commands and outputs are recorded in:

```text
docs/evidence/releases/s2-stage-06-payment-hardening-20260522.md
```
