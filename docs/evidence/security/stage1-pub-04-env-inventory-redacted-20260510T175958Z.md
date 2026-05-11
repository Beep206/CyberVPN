# STAGE1-PUB-04 Runtime Secrets And Env Evidence

Date: 2026-05-10 17:59:58 UTC
Stage: STAGE1-PUB-04
Release candidate: `stage1-beta-rc.1`
Approved snapshot commit: `cb042eb77fbc71bec69f4410149e44b4986960bd`
Server: `10.10.10.34` / `cybervpn-h-ops`
Evidence type: redacted runtime env inventory

## Result

`/srv/cybervpn-h/secrets` exists on the server with closed permissions:

| Path | Owner | Mode |
|---|---:|---:|
| `/srv/cybervpn-h/secrets` | `root:root` | `0700` |

The Stage 1 runtime env categories were created or verified as root-owned files with `0600` mode. Secret values are not recorded in this evidence.

## S1 Runtime Env Files

| File | Status | Owner | Mode | Key count | Placeholder count | Notes |
|---|---|---:|---:|---:|---:|---|
| `app.env` | created placeholder | `root:root` | `0600` | 28 | 10 | Backend/API core runtime config. |
| `payments.env` | created placeholder | `root:root` | `0600` | 14 | 9 | Provider credentials are placeholders until live provider setup. |
| `telegram-bot.env` | created placeholder | `root:root` | `0600` | 21 | 7 | Telegram runtime config with Stars disabled pending evidence. |
| `remnawave.env` | created placeholder | `root:root` | `0600` | 5 | 4 | Remnawave API/provisioning secrets are placeholders. |
| `sentry-runtime.env` | created placeholder | `root:root` | `0600` | 7 | 3 | Runtime Sentry/observability config. |
| `frontend.env` | created placeholder | `root:root` | `0600` | 9 | 2 | Public web runtime config. |
| `admin.env` | created placeholder | `root:root` | `0600` | 12 | 5 | Admin runtime config with 2FA-required flag. |

## Existing Server Env Files Preserved

These files already existed in the server secret directory and were not overwritten. Only metadata and key names were inventoried.

| File | Owner | Mode | Key count | Placeholder count |
|---|---:|---:|---:|---:|
| `alertmanager.env` | `root:root` | `0600` | 10 | 0 |
| `observability.env` | `root:root` | `0600` | 3 | 0 |
| `restic.env` | `root:root` | `0600` | 5 | 0 |
| `sentry-geoip.env` | `root:root` | `0600` | 3 | 0 |
| `sentry-smoke.env` | `root:root` | `0600` | 1 | 0 |
| `sentry.env` | `root:root` | `0600` | 10 | 0 |

## Redacted Key Inventory

### `app.env`

```text
ENVIRONMENT
DEBUG
SWAGGER_ENABLED
LOG_LEVEL
DATABASE_URL
REDIS_URL
JWT_SECRET
TOTP_ENCRYPTION_KEY
OAUTH_TOKEN_ENCRYPTION_KEY
CORS_ORIGINS
REGISTRATION_ENABLED
REGISTRATION_INVITE_REQUIRED
ADMIN_2FA_REQUIRED
ADMIN_HOST_PROTECTION_ENABLED
ADMIN_ALLOWED_HOSTS
RATE_LIMIT_ENABLED
RATE_LIMIT_FAIL_OPEN
MOBILE_RATE_LIMIT_FAIL_OPEN
REMNAWAVE_URL
REMNAWAVE_TOKEN
REMNAWAVE_WEBHOOK_SECRET
REMNAWAVE_DEFAULT_USER_EXPIRE_DAYS
STAGE1_TRIAL_PROVISIONING_ENABLED
STAGE1_PAID_PROVISIONING_ENABLED
FRONTEND_OBSERVABILITY_INTERNAL_SECRET
SENTRY_DSN
SENTRY_RELEASE
SENTRY_ENVIRONMENT
```

### `payments.env`

```text
CRYPTOBOT_TOKEN
CRYPTOBOT_NETWORK
PAYRAM_API_KEY
PAYRAM_WEBHOOK_SECRET
NOWPAYMENTS_API_KEY
NOWPAYMENTS_IPN_SECRET
YOOKASSA_SHOP_ID
YOOKASSA_SECRET_KEY
DIGISELLER_SELLER_ID
DIGISELLER_API_KEY
TELEGRAM_STARS_ENABLED
PAYMENT_ORPHAN_MAX_AGE_HOURS
PAYMENT_RECONCILIATION_ENABLED
PAYMENT_AUTORENEWAL_ENABLED
```

### `telegram-bot.env`

```text
ENVIRONMENT
BOT_MODE
BOT_TOKEN
BOT_USERNAME
TELEGRAM_MINIAPP_URL
WEBHOOK_URL
WEBHOOK_PATH
WEBHOOK_SECRET_TOKEN
BACKEND_API_URL
BACKEND_API_KEY
REDIS_URL
CRYPTOBOT_ENABLED
CRYPTOBOT_TOKEN
TELEGRAM_STARS_ENABLED
TRIAL_ENABLED
REFERRAL_ENABLED
ADMIN_IDS
SUPPORT_USERNAME
PROMETHEUS_ENABLED
SENTRY_DSN
SENTRY_RELEASE
```

### `remnawave.env`

```text
REMNAWAVE_URL
REMNAWAVE_TOKEN
REMNAWAVE_WEBHOOK_SECRET
REMNAWAVE_DEFAULT_INTERNAL_SQUAD_UUID
REMNAWAVE_PROVISIONING_EVIDENCE_REQUIRED
```

### `sentry-runtime.env`

```text
SENTRY_DSN
SENTRY_RELEASE
SENTRY_ENVIRONMENT
SENTRY_TRACES_SAMPLE_RATE
SENTRY_PROFILES_SAMPLE_RATE
FRONTEND_OBSERVABILITY_INTERNAL_SECRET
TELEGRAM_BOT_OBSERVABILITY_INTERNAL_SECRET
```

### `frontend.env`

```text
NODE_ENV
NEXT_TELEMETRY_DISABLED
NEXT_PUBLIC_SITE_URL
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_ADMIN_URL
NEXT_PUBLIC_DEFAULT_LOCALE
NEXT_PUBLIC_SENTRY_DSN
SENTRY_RELEASE
FRONTEND_OBSERVABILITY_INTERNAL_SECRET
```

### `admin.env`

```text
NODE_ENV
NEXT_TELEMETRY_DISABLED
NEXT_PUBLIC_SITE_URL
NEXT_PUBLIC_API_URL
API_URL
NEXT_PUBLIC_SENTRY_DSN
SENTRY_RELEASE
ADMIN_2FA_REQUIRED
PENDING_2FA_SECRET
OAUTH_TRANSACTION_SECRET
FRONTEND_OBSERVABILITY_INTERNAL_SECRET
TELEGRAM_BOT_INTERNAL_SECRET
```

## Validation

- Required Stage 1 env files exist under `/srv/cybervpn-h/secrets`.
- Required key presence was validated for the seven Stage 1 runtime files.
- Files are owned by `root:root` and are not world-readable.
- The server read validation was executed as root, matching Docker/host runtime secret loading expectations.
- `.private/cybervpn-h-10.10.10.34-access.md` is ignored by Git through `.private/`.
- Secret values were not written to this evidence file.

## Security Decisions Captured

- `REGISTRATION_ENABLED=false` and `REGISTRATION_INVITE_REQUIRED=true` remain fail-closed until owner go/no-go opens the beta cohort.
- `STAGE1_TRIAL_PROVISIONING_ENABLED=false` and `STAGE1_PAID_PROVISIONING_ENABLED=false` remain fail-closed until Remnawave/provisioning evidence is live-ready.
- `TELEGRAM_STARS_ENABLED=false` remains disabled until Telegram paid-flow evidence is complete.
- `PAYMENT_AUTORENEWAL_ENABLED=false` follows DEC-S1-020: no automatic renewal promise in S1.

## Remaining Before Live Use

The files intentionally contain `__REPLACE_BEFORE_LIVE_*` placeholders for app/payment/Telegram/Remnawave/Sentry runtime secrets. Before live traffic, the placeholders must be replaced through the approved secrets process, then re-inventoried without exposing values.
