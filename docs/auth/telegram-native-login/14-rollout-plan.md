# Rollout Plan

## Feature Flags

- `telegram_native_login_enabled`
- `telegram_native_login_ios_enabled`
- `telegram_native_login_android_enabled`
- `telegram_native_login_phone_scope_enabled`
- `telegram_native_login_2fa_required`

## Release Phases

### Phase 0 — Backend Only

- deploy OIDC endpoint
- deploy JWKS validation
- deploy metrics and logs
- mobile app still does not use native path

### Phase 1 — Internal Mobile Build

- enable native login only for internal builds or internal users
- verify iOS and Android callback behavior
- verify 2FA branch

### Phase 2 — Staging

- use staging Telegram bot/client configuration
- test account creation, login, linking, logout, refresh and TOTP
- keep legacy path available

### Phase 3 — Limited Production Rollout

- enable for a small production cohort
- monitor failure metrics
- monitor fallback usage
- monitor support tickets

### Phase 4 — Broad Production Rollout

- expand to all supported mobile users
- keep legacy fallback for older app versions

### Phase 5 — Legacy Decommission Preparation

- collect version adoption data
- confirm legacy path usage is below threshold
- communicate deprecation date

## Success Metrics

- native Telegram login success rate meets threshold
- no platform-specific callback regression
- no increase in duplicate account incidents
- no increase in TOTP bypass incidents

## Rollback Strategy

Primary rollback:

- disable native login feature flag

Expected rollback effect:

- new app builds fall back to legacy Telegram flow or hide the button according to client policy
- backend OIDC endpoint can remain deployed safely

## Rollback Triggers

- validation failures spike above threshold
- callback return failures spike on one platform
- account-linking conflicts exceed threshold
- pending 2FA branch fails

## Communication

- release notes for mobile team
- support team briefing
- backend on-call briefing
- deprecation notice before removing legacy endpoint

## Go/No-Go Checklist

Native production rollout is blocked unless:

- backend OIDC validation is complete
- TOTP branch works
- iOS callback works on a physical device
- Android callback works on a release-signed build
- legacy fallback is verified
- rollback flag is tested
- metrics dashboard exists
