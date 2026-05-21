# Stage 1 RENT-10C Telegram Stars Controlled Enablement Evidence

Date: `2026-05-20`

Stage: `S1 - Controlled Public Beta`

Scope: `STAGE1-RENT-10C`

Target: `prod-app-1`

## Purpose

Enable Telegram Stars as a controlled Telegram-only payment rail before `STAGE1-RENT-11`, without opening generic/CryptoBot checkout.

This is not full public paid-beta evidence yet. It only proves that the runtime gate and Telegram Bot API invoice-link capability are ready for the next low-value internal payment proof.

## Official Contract Reference

Telegram official documentation checked on `2026-05-20`:

- `https://core.telegram.org/bots/payments-stars`
- `https://core.telegram.org/bots/api#createinvoicelink`
- `https://core.telegram.org/bots/api#answerprecheckoutquery`
- `https://core.telegram.org/bots/api#successfulpayment`
- `https://core.telegram.org/bots/api#refundstarpayment`

S1 rules kept:

- Telegram digital goods/services use Stars with `currency="XTR"`.
- `provider_token` is empty for digital goods/services.
- `pre_checkout_query` is validation only and does not grant VPN access.
- VPN access is granted only after `successful_payment` confirmation.
- `telegram_payment_charge_id` must be stored for refund/support.
- Stars subscriptions/autoprolongation remain out of S1 scope.

## Runtime Gate Change

Before this step, `TELEGRAM_STARS_ENABLED=true` could not be used independently because `require_stage1_telegram_stars_enabled()` also required `PAYMENTS_ENABLED=true`.

That was unsafe for the current rollout because enabling `PAYMENTS_ENABLED=true` would also open generic/CryptoBot checkout surfaces.

The gate was changed to:

```text
PAYMENTS_ENABLED=false -> generic/CryptoBot checkout remains blocked
TELEGRAM_STARS_ENABLED=true -> Telegram Stars-only endpoints are open
```

Files:

```text
backend/src/presentation/api/shared/stage1_payment_runtime.py
backend/tests/security/test_stage1_payment_runtime_kill_switch.py
infra/deploy/stage1/docker-compose.stage1.yml
```

## Local Verification

```text
cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_payment_runtime_kill_switch.py tests/security/test_stage1_telegram_stars_readiness.py -q --no-cov
result: 9 passed

cd backend && PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/shared/stage1_payment_runtime.py tests/security/test_stage1_payment_runtime_kill_switch.py tests/security/test_stage1_telegram_stars_readiness.py src/presentation/api/v1/payments/telegram_stars.py src/presentation/api/v1/telegram/routes.py src/presentation/api/v1/payments/routes.py
result: all checks passed

cd services/telegram-bot && PYENV_VERSION=3.13.11 uv run pytest tests/unit/test_handlers/test_payment.py tests/unit/test_api_client.py::TestTelegramStarsAPIClient -q
result: 9 passed
```

## Deployment

Backend image:

```text
cybervpn/cybervpn-backend:stage1-rent10c-telegram-stars-enable-20260520t1505z
```

Unchanged runtime images were retagged to the same Stage 1 runtime tag for compose consistency.

Runtime containers recreated:

```text
cybervpn-backend
cybervpn-telegram-bot
```

Runtime state:

```text
backend: healthy
telegram-bot: healthy
frontend: healthy
admin: healthy
```

## Runtime Flags

Backend gate check:

```text
PAYMENTS_ENABLED=False
TELEGRAM_STARS_ENABLED=True
generic_gate=blocked:503
stars_gate=open
```

Telegram Bot runtime:

```text
CRYPTOBOT_ENABLED=false
YOOKASSA_ENABLED=false
TELEGRAM_STARS_ENABLED=true
```

## Telegram Bot API Smoke

Executed a no-payment `createInvoiceLink` smoke from the backend runtime using the production bot token.

No invoice URL, token, charge id or payment identifier was printed or stored.

```text
method=createInvoiceLink
currency=XTR
provider_token=empty
amount=1
status_code=200
ok=True
result_type=str
result_len=41
description_set=False
```

## Public Edge Check

Mini App plans route remains reachable and HTTP/3 remains enabled:

```text
GET https://cyber-vpn.net/ru-RU/miniapp/plans
HTTP/2 200
alt-svc: h3=":443"; ma=2592000
```

## Known Limitation

Production `subscription_plans` is currently empty:

```text
subscription_plans_total=0
active_subscription_plans_total=0
```

Therefore Stars is enabled at the runtime and Bot API level, but a real user-facing Stars purchase cannot be considered proven until:

1. Production pricing catalog is seeded or created through admin.
2. Selected S1 public plans have approved `telegram_stars_amount` / `prices.XTR`.
3. A real low-value internal Stars payment completes through Mini App or Telegram Bot.
4. `pre_checkout_query` is accepted.
5. `successful_payment` stores `telegram_payment_charge_id`.
6. Post-payment provisioning creates or extends VPN access through Remnawave.
7. Duplicate successful-payment/idempotency is proven.
8. Refund/support evidence is captured.

## Result

```text
PASS: Telegram Stars gate enabled.
PASS: Generic/CryptoBot checkout remains blocked.
PASS: Telegram Bot runtime sees TELEGRAM_STARS_ENABLED=true.
PASS: Telegram Bot API createInvoiceLink accepts XTR invoice payload.
PASS: No secrets, invoice links or payment identifiers stored in evidence.
PARTIAL: Real paid Stars purchase/provisioning proof remains blocked by missing production catalog/XTR plan pricing.
```
