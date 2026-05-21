# Stage 1 RENT-10B Crypto Pay Key And Webhook Closure Evidence

Date: `2026-05-20`

Stage: `S1 - Controlled Public Beta`

Scope: `STAGE1-RENT-10B`

Target: `prod-app-1`

## Purpose

Close the `STAGE1-RENT-10` Crypto Pay credential blocker after the owner recorded the real provider key.

Payments remain disabled during this evidence step. The goal is to prove provider auth, invoice creation contract, webhook schema storage and public webhook safety before enabling any paid checkout.

## Official Contract Reference

Crypto Pay API documentation checked on `2026-05-20`:

- `https://help.send.tg/en/articles/10279948-crypto-pay-api`

Relevant S1 contract points:

- `getMe` validates the app API token.
- `createInvoice` supports `currency_type=fiat` with `fiat=USD`.
- `pay_url` is deprecated; invoice links should prefer `bot_invoice_url`, `mini_app_invoice_url` or `web_app_invoice_url`.
- Webhooks are enabled manually in CryptoBot app settings with an HTTPS URL.
- Webhook authenticity is verified through `crypto-pay-api-signature`, HMAC-SHA-256 over the raw body using SHA-256 of the app token.

## Runtime Safety State

```text
PAYMENTS_ENABLED=false
CRYPTOBOT_ENABLED=false
TELEGRAM_STARS_ENABLED=false
CRYPTOBOT_NETWORK=mainnet
```

No live paid checkout was enabled during this step.

No provider token, signature, payment URL, invoice URL or secret value is stored in this evidence.

## Provider Auth Evidence

Crypto Pay mainnet API auth was retested from `prod-app-1`.

```text
GET https://pay.crypt.bot/api/getMe
status=200
ok=true
app_name=CyberVPN
```

Additional redacted token-shape checks:

```text
token_present=true
token_shape=provider_api_token
token_is_not_telegram_bot_token=true
network=mainnet
```

## Code Contract Fixes Applied

The backend and worker were adjusted to match the current Crypto Pay API invoice contract.

```text
USD/EUR/RUB/etc -> currency_type=fiat + fiat=<currency>
USDT/TON/BTC/etc -> currency_type=crypto + asset=<asset>
```

Checkout invoice URL preference was updated:

```text
mini_app_invoice_url
bot_invoice_url
web_app_invoice_url
pay_url
```

This avoids using deprecated `pay_url` as the first-choice link for Telegram/Mini App flows.

## Local Verification

Backend:

```text
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_cryptobot_sandbox_runtime.py -q --no-cov
result: 8 passed

PYENV_VERSION=3.13.11 uv run ruff check src/infrastructure/payments/cryptobot/client.py src/application/use_cases/payments/commit_checkout.py src/application/use_cases/payments/crypto_payment.py tests/security/test_stage1_cryptobot_sandbox_runtime.py
result: all checks passed
```

Task worker:

```text
PYENV_VERSION=3.13.11 uv run pytest tests/test_services.py::test_cryptobot_client_create_invoice tests/test_services.py::test_cryptobot_client_create_invoice_uses_fiat_contract_for_usd -q
result: 2 passed

PYENV_VERSION=3.13.11 uv run ruff check src/services/cryptobot_client.py tests/test_services.py
result: all checks passed
```

Migration:

```text
PYENV_VERSION=3.13.11 uv run ruff check alembic/env.py alembic/versions/20260520_stage1_webhook_logs.py
result: all checks passed

PYENV_VERSION=3.13.11 uv run alembic heads
result: 20260520_stage1_webhook_logs (head)
```

## Provider Invoice Smoke

A low-value Crypto Pay invoice smoke was executed from the backend runtime, then the invoice was deleted immediately.

```text
create_ok=true
invoice_id_set=true
status=active
currency_type=fiat
fiat=USD
asset=None
bot_invoice_url_set=true
mini_app_invoice_url_set=true
delete_ok=true
```

No invoice URL or provider identifier is stored here.

## Webhook Storage Blocker Found

Valid signed synthetic CryptoBot webhook initially failed:

```text
POST https://cyber-vpn.net/api/v1/webhooks/cryptobot
status=500
cause=relation "webhook_logs" does not exist
```

Root cause:

```text
WebhookLog ORM model existed, but the production schema did not contain webhook_logs.
```

## Webhook Storage Fix

Added migration:

```text
backend/alembic/versions/20260520_stage1_webhook_logs.py
```

Also fixed Alembic runtime DB URL selection:

```text
backend/alembic/env.py now uses DATABASE_URL or CYBERVPN_DATABASE_URL when present.
alembic.ini remains local fallback only.
```

Pre-migration backup:

```text
file=/srv/cybervpn/backups/pre-stage1-rent10-webhooklogs-20260520T144009Z.sql.gz
sha256=7fe238b0179715070f37081692dc69b925df100d9357d672e87e84c155d373fb
gzip_test=passed
```

Production migration:

```text
before_current=20260423_p27_partner_events
head=20260520_stage1_webhook_logs
upgrade=head
after_current=20260520_stage1_webhook_logs
```

Schema check:

```text
webhook_logs.id=uuid
webhook_logs.source=character varying
webhook_logs.event_type=character varying
webhook_logs.payload=jsonb
webhook_logs.signature=character varying
webhook_logs.is_valid=boolean
webhook_logs.processed_at=timestamp with time zone
webhook_logs.error_message=text
webhook_logs.created_at=timestamp with time zone
```

## Webhook Smoke After Fix

Valid signed synthetic CryptoBot webhook after migration:

```text
POST https://cyber-vpn.net/api/v1/webhooks/cryptobot
status=200
response={"status":"processed","warning":"payment_not_found"}
```

This is the expected synthetic result because the invoice does not correspond to a real CyberVPN payment row.

Webhook log storage proof:

```text
source=cryptobot
event_type=invoice_paid
is_valid=true
count=1
```

## Current Decision

`STAGE1-RENT-10B` closes the original invalid-key blocker and the newly found `webhook_logs` schema blocker.

Paid checkout is still not enabled automatically.

Before enabling paid beta, capture the remaining live-path evidence:

1. Owner enables Crypto Pay Webhooks in CryptoBot app settings with `https://cyber-vpn.net/api/v1/webhooks/cryptobot`.
2. A real low-value invoice is created from CyberVPN checkout.
3. The invoice is paid by an internal owner/beta tester.
4. The webhook maps to the CyberVPN payment row.
5. Subscription/order/provisioning state updates correctly.
6. Duplicate webhook/idempotency is proven.
7. Paid-but-no-access/orphan escalation remains empty or is handled within 24 hours.

## Result

```text
PASS: real Crypto Pay token accepted by provider API.
PASS: USD invoice creation uses fiat contract.
PASS: invoice URL preference follows current Crypto Pay fields.
PASS: webhook_logs table exists in production.
PASS: valid signed synthetic webhook returns 200.
PASS: payments remain disabled until real checkout payment evidence is captured.
```
