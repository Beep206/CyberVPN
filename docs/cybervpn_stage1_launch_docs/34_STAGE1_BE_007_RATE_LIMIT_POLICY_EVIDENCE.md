> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата фиксации: 2026-05-04
> Backlog ID: `S1-BE-007`
> Статус: local rate-limit policy and ASGI 429 proof completed; deployed Redis/ingress/edge evidence remains required before go-live.

# S1-BE-007 Rate Limit Policy Evidence

## Purpose

Этот документ фиксирует `S1-BE-007`: auth/payment/trial/referral/support rate limits must exist or be explicitly accepted before S1 Controlled Public Beta.

S1 accepts a simple backend-first policy: one Redis-backed global limiter plus stricter category buckets for launch-critical abuse surfaces. Edge/WAF limits remain desirable, but they are not a blocker for no-cost local implementation.

## Source References

Starlette middleware docs: https://www.starlette.io/middleware/

redis-py asyncio docs: https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html

Pydantic validator docs: https://pydantic.dev/docs/validation/latest/concepts/validators/

Important rules reflected in this implementation:

- middleware should remain configured at initialization and keep request-local state in request handling;
- Redis-backed counters can be used safely through async clients/pipelines;
- settings-derived limits must be explicit and testable.

## Implementation

Updated `backend/src/presentation/middleware/rate_limit.py`.

S1-specific changes:

- `RATE_LIMIT_WINDOW` is now passed into `RateLimitMiddleware` and used as the sliding-window duration;
- auth refresh is no longer exempt from rate limiting;
- route-category buckets were added for S1-critical surfaces;
- category buckets are shared across related paths, so abusive checkout attempts cannot bypass limits by alternating quote/commit paths;
- existing Helix admin read polling budget remains high and separate;
- existing global fallback remains `RATE_LIMIT_REQUESTS` per IP + path + window.

Updated `backend/src/main.py` so production runtime wiring passes the S1 category limits into the middleware.

Updated `backend/.env.example` with the S1 rate-limit environment variables.

## S1 Backend Rate Limit Policy

| Surface | Bucket | Default limit | Applies to |
|---|---:|---:|---|
| Global fallback | request path | `100 / 60s` | Any non-exempt route without a stricter S1 bucket |
| Auth sensitive | `s1_auth_sensitive` | `20 / 60s` | Web login/register/refresh/logout, OTP resend, magic link, Telegram auth, mobile login/register/refresh/logout, OAuth callbacks |
| Payment write | `s1_payment_write` | `30 / 60s` | Payment checkout quote/commit, invoice creation, checkout sessions, payment attempts, Telegram Stars payment writes, Telegram bot checkout quote/commit |
| Trial activation | `s1_trial_activate` | `10 / 60s` | Web/mobile/Mini App/Telegram bot trial activation paths |
| Growth/referral sensitive | `s1_growth_sensitive` | `60 / 60s` | Referral reads/generation, promo validation, gift quote/commit/redeem, growth rewards |
| Support write actions | `s1_support_write` | `30 / 60s` | Admin support actions under mobile-user/customer-operation write paths |
| Helix admin reads | request path | `1500 / 60s` | Existing lab/admin polling reads only |

Additional existing S1 protections remain in place:

- mobile login dependency: `5/min` per device or fallback IP;
- mobile registration dependency: `3/min` per IP;
- Telegram auth dependencies: `10/min` auth, `5/min` generated login link;
- magic link service: `5/hour` per email;
- OTP resend: `3/hour` per email;
- trial activation endpoint: `3/hour` per authenticated user;
- subscription cancel/password change/2FA endpoints keep their own Redis counters where already implemented.

## Local Evidence Summary

| Check | Result |
|---|---|
| Auth sensitive routes map to `s1_auth_sensitive` | Passed |
| `/api/v1/auth/refresh` is rate-limited, not exempt | Passed |
| Payment write routes map to `s1_payment_write` | Passed |
| Telegram Stars and Telegram bot checkout writes map to payment bucket | Passed |
| Trial activation routes map to `s1_trial_activate` | Passed |
| Referral/promo/gift sensitive routes map to `s1_growth_sensitive` | Passed |
| Admin support write routes map to `s1_support_write` | Passed |
| Non-critical routes keep default path bucket | Passed |
| Helix admin GET polling budget remains high | Passed |
| ASGI feature test returns `429` after shared payment bucket is exceeded | Passed |
| Existing rate limiter circuit-breaker/fail-open/fail-closed tests | Passed |
| Settings tests still pass | Passed |

## ASGI 429 Evidence

Feature test used an in-memory fake Redis client against a real ASGI app with `RateLimitMiddleware`.

Scenario:

1. Set `s1_payment_write` budget to `2 / 60s`.
2. `POST /api/v1/payments/checkout/quote`.
3. `POST /api/v1/payments/checkout/commit`.
4. `POST /api/v1/payments/checkout/quote`.

Observed result:

```json
{
  "statuses": [200, 200, 429],
  "third_body": {"detail": "Too many requests"},
  "retry_after": "60"
}
```

Interpretation: quote and commit share the same S1 payment-write category bucket, so alternating paths does not bypass the payment abuse control.

## Regression Tests

Added:

```text
backend/tests/security/test_stage1_rate_limit_policy.py
```

Reused:

```text
backend/tests/security/test_rate_limiter.py
backend/tests/unit/config/test_settings.py
```

Targeted result:

```text
62 passed in 0.29s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-BE-007` local auth/payment/trial/referral/support rate-limit proof | Closed locally |
| Missing route-category limits for S1 critical paths | Mitigated |
| `RATE_LIMIT_WINDOW` ignored by middleware | Fixed |
| Unlimited web auth refresh endpoint | Fixed |
| Payment quote/commit alternating-path bypass of per-path limits | Mitigated through shared category bucket |

## What Remains Open

| Item | Why still open |
|---|---|
| Deployed Redis-backed 429 evidence | Requires staging/prod Redis and deployed backend |
| Edge/WAF rate-limit evidence | Local baseline recorded in `119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md`; real DNS/TLS/WAF/security-event proof remains required |
| Provider webhook load/rate behavior | Must be handled under `S1-PAY-*` with provider fixture/live evidence |
| Telegram bot spam controls | Telegram-specific local evidence is completed in `59_STAGE1_TG_007_TELEGRAM_RATE_LIMITING_EVIDENCE.md`; deployed Redis/webhook/client evidence remains open |
| Production tuning | Defaults are conservative S1 values; adjust only with observed beta traffic and support impact |

## Regeneration Command

```bash
ENVIRONMENT=test \
REMNAWAVE_TOKEN='<redacted-placeholder>' \
JWT_SECRET='<redacted-placeholder>' \
CRYPTOBOT_TOKEN='<redacted-placeholder>' \
TOTP_ENCRYPTION_KEY='<redacted-placeholder>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-placeholder>' \
PYTHONPATH=backend \
PYENV_VERSION=3.13.11 \
python -m pytest \
  backend/tests/security/test_stage1_rate_limit_policy.py \
  backend/tests/security/test_rate_limiter.py \
  backend/tests/unit/config/test_settings.py \
  -q --no-cov
```
