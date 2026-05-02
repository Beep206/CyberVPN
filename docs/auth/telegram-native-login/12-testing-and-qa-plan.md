# Testing and QA Plan

## Backend Unit Tests

- Valid `id_token` accepted.
- Invalid signature rejected.
- Wrong issuer rejected.
- Wrong audience rejected.
- Expired token rejected.
- Missing `sub` rejected.
- Missing optional claims accepted.
- Optional phone claim stored only when present.
- Existing linked Telegram user resolved correctly.
- New Telegram user created correctly.
- Identity conflict rejected.
- TOTP-enabled user returns `requires_2fa=true`.

## Backend JWKS Tests

- Token with known `kid` uses cached key.
- Token with unknown `kid` triggers JWKS refresh.
- Unknown `kid` after refresh is rejected.
- JWKS network failure fails closed.
- Unsupported `alg` is rejected.
- `alg=none` is rejected.
- Token signed by a non-Telegram key is rejected.
- Token with valid signature but wrong `aud` is rejected.
- Token with valid signature but wrong `iss` is rejected.

## Backend Integration Tests

- `POST /api/v1/mobile/auth/telegram/oidc` success path.
- Device registration on first login.
- Device update on repeated login.
- Refresh works after Telegram OIDC login.
- Logout revokes refresh session.
- `POST /api/v1/mobile/auth/2fa/complete` success path.
- Legacy endpoint still works while migration flag is enabled.

## Identity Migration Tests

- Existing legacy user with `telegram_id` logs in through OIDC and receives populated `telegram_subject`.
- Existing user with `telegram_subject` logs in again and no duplicate account is created.
- Existing user A has legacy `telegram_id`; user B attempts to link the same Telegram OIDC subject; backend rejects.
- Phone number returned by Telegram does not auto-merge accounts.

## Flutter Tests

- Telegram button triggers provider.
- Provider calls native bridge.
- Provider exchanges `id_token` with backend.
- Success stores first-party tokens.
- Error surfaces user-friendly message.
- `requires_2fa` routes to TOTP UI.
- Feature flag fallback uses legacy path when expected.

## iOS Manual QA

- Telegram installed.
- Telegram not installed.
- Universal Link callback works.
- User cancels authorization.
- Wrong Associated Domain config fails gracefully.
- App restart after callback does not lose auth flow state.

## Android Manual QA

- Telegram installed.
- Telegram not installed.
- App Link callback works.
- `onNewIntent` path works.
- Wrong SHA-256 fingerprint fails gracefully.
- Release and debug build behavior both verified.

## Real Device Requirements

- iOS physical device with Telegram installed
- iOS physical device without Telegram installed
- Android physical device with Telegram installed
- Android physical device without Telegram installed
- release-signed Android build
- debug-signed Android build

## Environment QA Matrix

| Environment | iOS | Android | Backend validation | 2FA | Legacy fallback |
|---|---|---|---|---|---|
| local | Required | Required | Required | Optional early, required before staging exit | Optional |
| staging | Required | Required | Required | Required | Required |
| production limited rollout | Required | Required | Required | Required | Required |

## Regression Areas

- existing password mobile login
- existing refresh flow
- existing logout flow
- existing biometric flow
- existing legacy Telegram flow

## Pre-Release Exit Criteria

- backend unit tests green
- backend integration tests green
- Flutter auth tests green
- iOS manual checklist passed
- Android manual checklist passed
- staging rollout metrics within expected error budget
