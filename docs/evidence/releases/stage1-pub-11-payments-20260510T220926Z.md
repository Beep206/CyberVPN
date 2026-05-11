# STAGE1-PUB-11 Payment Path Deploy Evidence

Date: 2026-05-10T22:09:26Z

Stage: Stage 1 Controlled Public Beta

Result: **safe-blocked; paid checkout not enabled**

## Scope

This evidence covers the first Stage 1 payment runtime deployment gate:

- CryptoBot as the first candidate payment provider.
- Backend payment runtime kill switch.
- Telegram Stars disabled until evidence.
- Worker/scheduler availability for Stage 1 payment reconciliation.
- Webhook signature rejection for unsigned CryptoBot callbacks.
- Paid-but-no-access/orphan reconciliation API and metrics.

## Official Provider Contract Checked

CryptoBot Crypto Pay official docs were checked during this step:

- API token is sent through `Crypto-Pay-API-Token`.
- Production API base is `https://pay.crypt.bot/api/%method%`.
- Testnet base is `https://testnet-pay.crypt.bot/`.
- Invoice status values include `active`, `paid` and `expired`.
- Webhook authenticity is verified with the `crypto-pay-api-signature` header and HMAC-SHA-256 over the raw request body using SHA-256(token) as the HMAC key.
- Webhook delivery retries continue for multiple attempts over several days, so idempotency must be mandatory.

Source: https://help.send.tg/en/articles/10279948-crypto-pay-api

## Runtime Changes Applied

Backend code:

- Added `PAYMENTS_ENABLED`, `TELEGRAM_STARS_ENABLED`, `PAYMENT_RECONCILIATION_ENABLED`, `PAYMENT_AUTORENEWAL_ENABLED` and `PAYMENT_ORPHAN_MAX_AGE_HOURS` settings.
- Added `backend/src/presentation/api/shared/stage1_payment_runtime.py`.
- New paid checkout/invoice creation is blocked when `PAYMENTS_ENABLED=false`.
- New Telegram Stars invoice creation is blocked when either `PAYMENTS_ENABLED=false` or `TELEGRAM_STARS_ENABLED=false`.
- Guarded web checkout, Mini App checkout and Telegram bot checkout creation paths.

Compose/runtime:

- Built and loaded `local/cybervpn-backend:stage1-beta-rc.2`.
- Built and loaded `local/cybervpn-task-worker:stage1-beta-rc.2`.
- Retagged unchanged admin/frontend/telegram images as `stage1-beta-rc.2` for compose tag consistency.
- Updated Stage 1 compose runtime to `CYBERVPN_IMAGE_TAG=stage1-beta-rc.2`.
- Started `cybervpn-worker` and `cybervpn-scheduler`.
- Worker now creates `PROMETHEUS_MULTIPROC_DIR` before startup.
- Worker runs one process for S1 to avoid duplicate metrics server port binding.
- Worker/scheduler env-file order now lets `payments.env` override placeholder payment values from `telegram-bot.env`.
- `BACKEND_INTERNAL_SECRET` was added to the server app env for worker reconciliation calls.

## Runtime State

Payment flags inside live backend:

```text
CRYPTOBOT_NETWORK=mainnet
PAYMENTS_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
PAYMENT_ORPHAN_MAX_AGE_HOURS=24
PAYMENT_RECONCILIATION_ENABLED=true
STAGE1_PAID_PROVISIONING_ENABLED=false
STAGE1_TRIAL_PROVISIONING_ENABLED=false
TELEGRAM_STARS_ENABLED=false
```

Live services:

```text
cybervpn-backend:   healthy, image local/cybervpn-backend:stage1-beta-rc.2
cybervpn-worker:    healthy, image local/cybervpn-task-worker:stage1-beta-rc.2
cybervpn-scheduler: healthy, image local/cybervpn-task-worker:stage1-beta-rc.2
```

## Verification

Local backend checks:

```text
uv run ruff check ... -> passed
uv run pytest --no-cov ... -> 100 passed
```

The test set included:

- payment runtime kill switch;
- CryptoBot production/testnet runtime guards;
- webhook signature verification;
- webhook idempotency;
- orphan payment policy;
- paid provisioning failure safety;
- provider status mapping;
- Stage 1 payment reconciliation job.

Live backend probes:

```text
GET http://127.0.0.1:18080/health -> {"status":"ok"}
POST /api/v1/webhooks/cryptobot without signature -> 401 Invalid webhook signature
live require_stage1_payments_enabled() -> blocked status=503
live require_stage1_telegram_stars_enabled() -> blocked status=503
```

Reconciliation:

```json
{
  "report_version": "stage1-payment-reconciliation-v1",
  "summary": {
    "total_items": 0,
    "manual_review_items": 0,
    "alert_15m_items": 0,
    "p1_escalation_items": 0,
    "p0_blocker_items": 0,
    "max_age_minutes": 0,
    "launch_blocked": false,
    "mismatch_counts": {}
  },
  "items_count": 0
}
```

Worker payment metrics after manual reconciliation run:

```text
cybervpn_stage1_payment_reconciliation_runs_total{result="success"} 1.0
cybervpn_stage1_payment_reconciliation_max_age_minutes 0.0
cybervpn_stage1_payment_reconciliation_launch_blocked 0.0
cybervpn_stage1_payment_reconciliation_items_current{severity="manual_review"} 0.0
cybervpn_stage1_payment_reconciliation_items_current{severity="alert_15m"} 0.0
cybervpn_stage1_payment_reconciliation_items_current{severity="p1_escalation"} 0.0
cybervpn_stage1_payment_reconciliation_items_current{severity="p0_blocker"} 0.0
```

## Provider Readiness

CryptoBot:

```text
GET https://pay.crypt.bot/api/getMe -> 401 UNAUTHORIZED
```

Conclusion: the current CryptoBot token is **not proven valid**. It may be invalid, revoked, wrong-network, or not the expected Crypto Pay app token. Therefore no paid checkout can be enabled.

Other providers:

- PayRam: placeholder only.
- NOWPayments: placeholder only.
- YooKassa: placeholder only.
- Digiseller: placeholder only.
- Telegram Stars: disabled by runtime flag and should remain disabled until evidence.

## Decision

Keep these flags for S1 until provider evidence exists:

```text
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=false
STAGE1_PAID_PROVISIONING_ENABLED=false
```

No live paid checkout was enabled in this step.

## Remaining Blockers

- Replace or confirm the CryptoBot Crypto Pay token.
- Prove provider API auth with `getMe`.
- Configure and verify the provider webhook URL in the provider dashboard.
- Run signed webhook sample through staging/sandbox or controlled live evidence.
- Run success/failure/expired invoice evidence.
- Run duplicate webhook evidence against runtime, not only unit tests.
- Run low-value production payment only after owner approval.
- Keep all non-CryptoBot providers disabled until their credentials and evidence are real.
