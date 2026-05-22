# S2-STAGE-06 Evidence: Payment Production Hardening

**Date:** 2026-05-22
**Stage:** `S2-STAGE-06`
**Status:** Passed targeted local hardening evidence

---

## 1. Scope

This evidence covers the S2 payment production hardening gate:

1. primary and secondary provider posture;
2. provider final-status contract;
3. webhook signature validation;
4. duplicate webhook idempotency;
5. orphan/paid-but-no-access policy;
6. reconciliation dashboard/process;
7. refund/dispute handling;
8. Telegram Stars surface restriction;
9. growth/payment feature kill switches;
10. autoprolongation disabled posture.

---

## 2. Official Provider Documentation Checked

Context7 was not available in this environment, so provider documentation was checked through direct official URLs.

| Provider/surface | Source | Local fetch result |
|---|---|---|
| CryptoBot / Crypto Pay | `https://help.send.tg/en/articles/10279948-crypto-pay-api` | reachable |
| Telegram Stars | `https://core.telegram.org/bots/payments-stars` | reachable |
| Telegram Bot payments API | `https://core.telegram.org/bots/api#payments` | reachable |
| PayRam status docs | `https://docs.payram.com/api-integration/payments-api/payment-status` | reachable |
| Digiseller API docs | `https://my.digiseller.com/inside/api_payment.asp` | reachable |
| YooKassa payment process | `https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process` | reachable |
| NOWPayments payment statuses | `https://nowpayments.zendesk.com/hc/en-us/articles/18395434917149-Payment-statuses` | 403 from local fetch; existing resolver remains conditional until provider evidence |

---

## 3. Code Changes Verified

Changed backend payment hardening code:

```text
backend/src/presentation/api/v1/webhooks/routes.py
backend/src/application/use_cases/payments/payment_webhook.py
backend/src/infrastructure/payments/cryptobot/webhook_handler.py
```

Added tests:

```text
backend/tests/security/test_stage2_payment_production_hardening.py
```

Added contract document:

```text
docs/cybervpn_stage2_launch_docs/05_STAGE2_PAYMENT_PRODUCTION_HARDENING.md
```

---

## 4. Payment Contract Outcome

| Area | Result |
|---|---|
| Primary S2 path | CryptoBot / Crypto Pay candidate |
| Secondary S2 path | Telegram Stars, Telegram-only |
| Other providers | Conditional; disabled until credentials/callback/refund/reconciliation evidence |
| Autoprolongation | Disabled; deferred to `S2-STAGE-07` lifecycle proof |
| Growth-related payment features | Referral/promo/gift payment effects remain behind kill switches |
| Orphan SLA | No unresolved paid-but-no-access/orphan case older than 24h |
| Support model | Support can use safe IDs and reconciliation output, not raw provider secrets/payloads |

---

## 5. Runtime Switch Outcome

Safe pre-opening state:

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

Payment canary state after credential/webhook evidence:

```text
PAYMENTS_ENABLED=true
TELEGRAM_STARS_ENABLED=false or Telegram-only true
PAYMENT_RECONCILIATION_ENABLED=true
PAYMENT_AUTORENEWAL_ENABLED=false
```

---

## 6. Webhook Hardening Outcome

CryptoBot webhook behavior now has these layered protections:

1. route-level signature verification through `verify_stage1_webhook_signature`;
2. Redis/Valkey idempotency wiring in the real FastAPI route;
3. use-case-level `validate_payment` before invoice terminal-event side effects;
4. numeric invoice-id validation;
5. duplicate paid-invoice suppression with `already_processed`;
6. database terminal status as fallback authority;
7. `payment_not_found` orphan events are not marked processed in Redis;
8. failed/expired/cancelled callbacks do not consume the paid-invoice idempotency key.

This avoids the specific S2 risk where the handler had idempotency capability but the production route did not supply Redis and the use-case did not call the full validation path.

---

## 7. Backend Lint

Command:

```bash
cd backend
uv run ruff check src/application/use_cases/payments/payment_webhook.py src/presentation/api/v1/webhooks/routes.py src/infrastructure/payments/cryptobot/webhook_handler.py tests/security/test_stage2_payment_production_hardening.py
```

Result:

```text
All checks passed!
```

---

## 8. Backend Targeted Security Tests

Command:

```bash
cd backend
uv run pytest tests/security/test_stage2_payment_production_hardening.py tests/security/test_stage1_webhook_signature_verification.py tests/security/test_stage1_webhook_idempotency.py tests/security/test_stage1_payment_runtime_kill_switch.py tests/security/test_stage1_provider_payment_status_mapping.py tests/security/test_stage1_orphan_payment_policy.py tests/security/test_stage1_refund_dispute_process.py -q --no-cov
```

Result:

```text
96 passed in 0.43s
```

Coverage in this run:

1. provider status mapping;
2. signature validation;
3. idempotency contract;
4. runtime kill switches;
5. orphan policy thresholds;
6. refund/dispute role contract;
7. S2 CryptoBot invoice validation and duplicate suppression.

---

## 9. Route-Level Integration Subset

Local prerequisites:

```bash
cd infra
docker compose up -d remnawave-db remnawave-redis
```

Command:

```bash
cd backend
SWAGGER_ENABLED=false RATE_LIMIT_PAYMENT_WRITE_REQUESTS=1000 uv run pytest tests/integration/api/v1/payments/test_payment_flows.py -q --no-cov
```

Result:

```text
6 passed in 0.75s
```

This confirms the real FastAPI payment routes still work after adding Redis/Valkey injection to the CryptoBot webhook route.

---

## 10. Dashboard And Alert Coverage

Confirmed existing dashboard:

```text
infra/grafana/dashboards/stage2-payment-reconciliation-dashboard.json
```

Dashboard panels:

```text
Payment Success Ratio 24h
Payment Failures 24h
Paid-But-No-Access Current
Max Reconciliation Age
Payment Results By Status
Webhook Failures And Retries
Current Reconciliation Findings By Severity
Payment/Reconciliation Errors
```

Confirmed alert/rule coverage:

```text
infra/prometheus/rules/stage2_analytics_alerts.yml
infra/prometheus/rules/stage1_alerts.yml
infra/prometheus/rules/stage1_dashboard_recording_rules.yml
```

---

## 11. Residual Risks

| Risk | Handling |
|---|---|
| CryptoBot production token and live webhook callback are not re-proven in this local gate | Required before `PAYMENTS_ENABLED=true` in public runtime |
| NOWPayments status source returned 403 from local fetch | Keep NOWPayments conditional until provider account/callback evidence |
| Telegram Stars refund execution not proven here | Keep Stars refunds in support/finance review until API evidence |
| Promo/gift/referral payment effects are not opened here | Keep kill switches closed until dedicated S2/S3 gates |
| Autoprolongation is not part of this stage | Keep `PAYMENT_AUTORENEWAL_ENABLED=false` and handle lifecycle in `S2-STAGE-07` |

---

## 12. Security Sweep

| Check | Result |
|---|---|
| `git diff --check` | Passed |
| `npm audit --audit-level=high` | Passed high/critical gate; residual moderate advisories remain |
| Backend `uvx pip-audit --progress-spinner off --skip-editable .` | Passed |
| Targeted secret scan on changed files | No literal production secrets found |
| Targeted dangerous-pattern scan on changed files | No new dangerous patterns found |

Residual npm audit advisories are moderate and unrelated to this backend payment hardening change.

---

## 13. Exit Decision

`S2-STAGE-06` passes targeted local hardening.

This is not full live provider approval by itself. Before public sale, the owner still needs production credential/callback smoke evidence for the primary payment path and dashboard alert delivery evidence.

Next stage:

```text
S2-STAGE-07: Subscription, Renewal, Expiry, And Refund Flows
```
