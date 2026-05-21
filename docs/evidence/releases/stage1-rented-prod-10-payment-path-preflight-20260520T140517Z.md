# Stage 1 RENT-10 Payment Path Preflight Evidence

Date: `2026-05-20`

Stage: `S1 - Controlled Public Beta`

Scope: `STAGE1-RENT-10`

Target: `prod-app-1`

## Purpose

`STAGE1-RENT-10` checks whether the first Stage 1 paid path can be enabled safely.

The selected first paid-path candidate remains:

```text
CryptoBot / Crypto Pay
```

This stage is intentionally conservative: if real provider credentials and webhook evidence are not proven, payments stay disabled and the beta remains trial-only.

## Owner Retest Carry-In

Owner confirmed after `STAGE1-RENT-09J`:

```text
Telegram Mini App opens and works.
```

This closes the owner/client retest dependency for moving from `09J` to `10`.

## Runtime State

Redacted server-side runtime inspection:

```text
Backend:
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=false
CRYPTOBOT_NETWORK=mainnet
CRYPTOBOT_TOKEN_LEN=set

Telegram Bot:
CRYPTOBOT_ENABLED=false
TELEGRAM_STARS_ENABLED=false
YOOKASSA_ENABLED=false
CRYPTOBOT_NETWORK=mainnet
CRYPTOBOT_TOKEN_SET=true
```

No secret values were printed or stored in this evidence.

## Provider Credential Preflight

CryptoBot / Crypto Pay API auth check against mainnet:

```text
GET https://pay.crypt.bot/api/getMe
status=http_403
ok=false
```

Interpretation:

```text
The configured token is present but is not accepted by the Crypto Pay API.
```

Most likely operational meaning:

```text
The runtime has a token-shaped value, but not a valid Crypto Pay API token for the selected provider account.
```

## Public Safety Checks

CryptoBot webhook without a valid signature:

```text
POST https://cyber-vpn.net/api/v1/webhooks/cryptobot
HTTP/2 401
{"detail":"Invalid webhook signature"}
```

Public checkout commit without authenticated customer token:

```text
POST https://cyber-vpn.net/api/v1/payments/checkout/commit
HTTP/2 401
{"detail":{"code":"INVALID_TOKEN","message":"Invalid token"}}
```

HTTP/3/QUIC remains enabled on the edge during this check:

```text
alt-svc: h3=":443"; ma=2592000
```

## Decision

Payments were not enabled.

Stage 1 remains:

```text
trial-only controlled beta
```

Paid checkout remains blocked until all of the following are available as redacted evidence:

1. Valid Crypto Pay API token from the real CryptoBot/Crypto Pay app.
2. Provider API `getMe` or equivalent account/auth check succeeds without exposing values.
3. Production webhook/callback registration is proven without exposing secrets.
4. Valid CryptoBot webhook signature sample is accepted.
5. Invalid signature sample is rejected.
6. Duplicate webhook/idempotency proof is captured against durable storage.
7. Low-value invoice lifecycle evidence exists: created, paid, expired/cancel-equivalent.
8. `paid -> CyberVPN payment -> subscription/order -> Remnawave provisioning` evidence exists.
9. Paid-but-no-access/orphan payment support escalation is proven.
10. Payment rollback/kill-switch evidence remains available.

## Result

`STAGE1-RENT-10` is completed as a safe preflight with a live-provider blocker:

```text
PASS: payments stayed disabled.
PASS: unsafe webhook request rejected.
PASS: unauthenticated checkout rejected.
BLOCKED FOR PAID BETA: CryptoBot provider credential preflight returned HTTP 403.
```

## Follow-Up

Do not enable `PAYMENTS_ENABLED=true`, `CRYPTOBOT_ENABLED=true` or `TELEGRAM_STARS_ENABLED=true` until the provider evidence above is captured.

Update:

```text
The initial Crypto Pay credential blocker in this document is superseded by:
docs/evidence/releases/stage1-rented-prod-10b-cryptopay-key-webhook-closure-20260520T144900Z.md

Payments still remain disabled until real paid checkout -> provider callback -> CyberVPN payment row -> Remnawave provisioning evidence exists.
```

The next runtime stage can proceed as trial-only stabilization:

```text
STAGE1-RENT-11: Observability/stabilization loop for the first cohort
```
