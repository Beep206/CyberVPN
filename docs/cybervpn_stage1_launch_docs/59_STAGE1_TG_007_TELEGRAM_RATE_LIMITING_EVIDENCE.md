# 59. Stage 1 Evidence - S1-TG-007 Telegram Rate Limiting

Date: 2026-05-04

Backlog ID: `S1-TG-007`

Status: completed locally for Telegram Bot anti-spam/rate-abuse controls and Mini App/backend rate-limit linkage. Real BotFather token, deployed webhook/polling, live Redis/Valkey and real Telegram client evidence remain required before S1 go-live.

## Objective

Prove that Stage 1 Telegram surfaces cannot be abused by unlimited message/callback spam:

- Telegram Bot message events are rate-limited per user;
- Telegram Bot callback events are rate-limited separately per user;
- admin users bypass user throttle for launch operations;
- Redis-backed sliding-window state is used for distributed bot instances;
- Redis throttling failure is fail-closed by default for S1 staging/production;
- fail-open and disable modes exist only as explicit local/smoke overrides;
- Telegram Mini App public backend calls remain covered by `S1-BE-007` backend rate-limit buckets.

## Official Docs Checked

| Surface | Source |
|---|---|
| aiogram middleware propagation/stop-processing contract | https://docs.aiogram.dev/en/latest/dispatcher/middlewares.html |
| Redis sorted set operations used for sliding-window limits | https://redis.io/docs/latest/develop/data-types/sorted-sets/ |

## Implemented Policy

| Rule | Local implementation |
|---|---|
| Bot anti-spam is enabled by default | `TELEGRAM_THROTTLE_ENABLED=true` default in settings and `.env.example` |
| Redis failure blocks abuse by default | `TELEGRAM_THROTTLE_FAIL_OPEN=false` default; Redis errors stop non-admin events |
| Message and callback budgets are separate | message defaults: `5 / 10s`; callback defaults: `3 / 3s` |
| Limits are configurable without code change | `TELEGRAM_MESSAGE_RATE_*` and `TELEGRAM_CALLBACK_RATE_*` env settings |
| Admin launch operations are not blocked | `settings.is_admin(user_id)` bypass remains in middleware |
| Throttled callbacks get lightweight UX feedback | callback throttle answers with a short wait message |
| Throttled messages are dropped silently | avoids creating more spam from anti-spam itself |
| Mini App is not handled inside bot middleware | Mini App calls are backend HTTPS/API calls and remain covered by `S1-BE-007` category buckets |

## Repository Changes

Telegram bot runtime:

- `services/telegram-bot/src/config.py`
  - added `TELEGRAM_THROTTLE_ENABLED`;
  - added `TELEGRAM_THROTTLE_FAIL_OPEN`;
  - added message/callback window and max-request settings.
- `services/telegram-bot/src/middlewares/throttling.py`
  - switched middleware defaults from hard-coded constants to `BotSettings`;
  - added explicit throttle disable path for local smoke;
  - changed Redis failure behavior to settings-driven, fail-closed by default.
- `services/telegram-bot/.env.example`
  - documented S1 Telegram anti-spam defaults.
- `services/telegram-bot/README.md`
  - documented public throttle environment variables.
- `services/telegram-bot/docs/telegram-bot-service.md`
  - documented throttle variables in the service env table.

Tests:

- `services/telegram-bot/tests/unit/test_middlewares/test_throttling.py`
  - covers per-user message throttling, callback throttling, admin bypass, settings-backed limits, Redis fail-open when explicitly configured, Redis fail-closed by default, local disable override and dispatcher middleware registration.
- `services/telegram-bot/tests/unit/test_main.py`
  - covers environment parsing for throttle settings.

No real Telegram token, BotFather call, Telegram API call, webhook call, Redis server, Remnawave call or payment provider call was used.

## Evidence Matrix

| Flow | Proof |
|---|---|
| First user message | Allowed |
| Message spam | Excess messages are dropped and handler is not called |
| Callback spam | Excess callbacks are dropped and callback receives wait answer |
| Separate users | One user's spam does not block another user |
| Admin user | Admin events bypass user throttling |
| No Telegram user ID | Event passes through because no per-user key can be built |
| Redis sliding window | Old entries expire and the user can act again after the window |
| Identical high-speed timestamps | Redis ZSET members are unique, so same-timestamp events still count separately |
| Redis down, default S1 behavior | Non-admin callback is blocked and handler is not called |
| Redis down, explicit fail-open | Handler is called only when `TELEGRAM_THROTTLE_FAIL_OPEN=true` |
| Explicit local disable | Handler is called when `TELEGRAM_THROTTLE_ENABLED=false` |
| Dispatcher wiring | `register_middlewares` attaches `ThrottlingMiddleware` to message and callback observers |
| Mini App/backend path | Backend S1 rate-limit tests pass for critical public buckets |

## Local Evidence Commands

Telegram Bot component and wiring suite:

```bash
cd services/telegram-bot
uv run pytest tests/unit/test_middlewares/test_throttling.py tests/unit/test_main.py -q
```

Result:

```text
24 passed in 1.69s
```

Static check for changed Telegram Bot files:

```bash
cd services/telegram-bot
uv run ruff check \
  src/config.py \
  src/middlewares/throttling.py \
  tests/unit/test_middlewares/test_throttling.py \
  tests/unit/test_main.py
```

Result:

```text
All checks passed!
```

Backend Mini App/API rate-limit linkage suite:

```bash
cd backend
ENVIRONMENT=test \
REMNAWAVE_TOKEN='<redacted-placeholder-token-that-is-long-enough>' \
JWT_SECRET='<redacted-placeholder-jwt-secret-that-is-at-least-32-chars>' \
CRYPTOBOT_TOKEN='<redacted-placeholder-token-that-is-long-enough>' \
TOTP_ENCRYPTION_KEY='<redacted-placeholder-totp-key-that-is-at-least-32-chars>' \
OAUTH_TOKEN_ENCRYPTION_KEY='<redacted-placeholder-oauth-key-that-is-at-least-32-chars>' \
uv run pytest --no-cov \
  tests/security/test_stage1_rate_limit_policy.py \
  tests/security/test_rate_limiter.py \
  -q
```

Result:

```text
37 passed in 0.41s
```

## What This Closes

| Item | Status |
|---|---|
| `S1-TG-007` local Telegram Bot message/callback anti-spam proof | Closed locally |
| Settings-backed Telegram Bot throttle policy | Closed locally |
| Redis failure bypass risk in bot middleware | Mitigated by fail-closed default |
| Dispatcher wiring evidence | Closed locally |
| Mini App/backend rate-limit linkage | Covered locally through `S1-BE-007` tests |

## Remaining Evidence Before Go-Live

| Evidence item | Status |
|---|---|
| Real staging bot token stored through approved secret process | Open |
| Real webhook/polling update delivery through deployed bot runtime | Open |
| Deployed Redis/Valkey-backed throttle keys and TTL evidence | Open |
| Real Telegram client proof that throttled callbacks receive expected answer | Open |
| Real Telegram Bot abuse smoke against staging bot with redacted transcript | Open |
| Deployed Mini App/browser rate-limit behavior against staging backend | Open |
| Alert/observability evidence for Redis throttle failures | Open |
| Production smoke after RC tag | Open |

## Security Review Notes

| Check | Result |
|---|---|
| Secret handling | No real bot token, webhook secret, provider secret or initData was added |
| Abuse control | Non-admin bot messages/callbacks are limited per user |
| Redis outage behavior | S1 default is fail-closed; fail-open requires explicit env override |
| User experience | Callback spam gets one lightweight answer; message spam remains silent |
| Admin operations | Admin bypass is preserved for launch/support operations |
| Production side effects | Tests use mocks/fakeredis only; no live Telegram/API/provider calls |

## Next ID

Next ID to execute: `S1-ADM-001` - admin domain/access protection.
