# Telegram Native Login — Documentation Index

## Goal

Внедрить официальный Telegram Native Login для мобильного приложения `cybervpn_mobile` на базе нового Telegram OIDC flow.

Итоговая целевая модель:

- мобильное приложение использует официальный Telegram Native SDK для iOS и Android
- мобильный клиент получает `id_token` от Telegram SDK
- backend валидирует `id_token` через Telegram JWKS
- backend выпускает только first-party mobile `access_token` и `refresh_token`
- существующая device-aware mobile session model сохраняется

## Scope

- Flutter mobile app
- iOS native integration
- Android native integration
- Backend mobile auth namespace
- Telegram OIDC ID Token validation
- Device-aware mobile sessions
- TOTP/2FA integration for mobile Telegram login
- Migration from legacy Telegram mobile auth flow

## Out Of Scope

- Полный рефактор всего web auth
- Замена Telegram Mini App auth для web
- Переработка всех mobile social providers вне Telegram
- Массовая миграция старых web Telegram flow за пределами mobile login

## Why This Is A New Workstream

Текущий mobile Telegram flow не является целевым:

- `cybervpn_mobile` сейчас отправляет legacy `auth_data`
- backend сейчас валидирует HMAC payload старого Telegram Login Widget
- новый Telegram Login для mobile документируется как OIDC flow
- Telegram отдельно дает Native SDK для iOS и Android

Следовательно, это не “допилить текущую кнопку”, а отдельный auth-workstream с новыми backend, mobile, security и rollout решениями.

## Reading Order

1. [01-current-state-and-gap-analysis.md](01-current-state-and-gap-analysis.md)
2. [02-product-requirements.md](02-product-requirements.md)
3. [03-target-architecture.md](03-target-architecture.md)
4. [04-botfather-and-environments.md](04-botfather-and-environments.md)
5. [05-backend-oidc-contract.md](05-backend-oidc-contract.md)
6. [06-mobile-sdk-integration.md](06-mobile-sdk-integration.md)
7. [07-user-identity-and-linking.md](07-user-identity-and-linking.md)
8. [08-session-device-and-2fa-policy.md](08-session-device-and-2fa-policy.md)
9. [09-security-threat-model.md](09-security-threat-model.md)
10. [10-privacy-consent-and-phone-number.md](10-privacy-consent-and-phone-number.md)
11. [11-migration-from-legacy-telegram-auth.md](11-migration-from-legacy-telegram-auth.md)
12. [12-testing-and-qa-plan.md](12-testing-and-qa-plan.md)
13. [13-observability-and-runbook.md](13-observability-and-runbook.md)
14. [14-rollout-plan.md](14-rollout-plan.md)
15. [15-implementation-plan.md](15-implementation-plan.md)
16. [16-post-implementation-open-items.md](16-post-implementation-open-items.md)

## Key Decisions Captured In This Package

- Phase 1 mobile Telegram login uses official native SDKs plus backend `id_token` validation.
- Backend remains the only trust authority for Telegram identity.
- Phase 1 requests `openid profile` by default.
- `phone` scope is optional and gated behind product decision and rollout flag.
- Telegram login does not bypass TOTP if the user has 2FA enabled.
- Legacy mobile endpoint remains temporarily supported during migration.

## Implementation Readiness

Before development starts, the following must be finalized:

- endpoint path convention using full public API paths
- BotFather staging and production credentials
- SDK `nonce` or `state` support check
- Telegram-only storage policy
- mobile config migration from `TELEGRAM_BOT_USERNAME` to native SDK config inputs
- Android GitHub Packages CI access

## Phase 0 Status

Resolved from the current repository and official Telegram docs:

- public API path convention is frozen on `/api/v1/...`
- Phase 1 strategy is frozen as `id_token` validation on backend
- iOS bundle identifiers are known from the repo
- Android application IDs are known from the repo
- public SDK examples expose `clientId`, `redirectUri`, `scopes` and `idToken`
- public SDK examples do not document `nonce` or `state`
- current mobile client is wired for legacy `cybervpn://telegram/callback`, not Telegram `tg.dev`
- current iOS entitlements contain `applinks:cybervpn.app`, not Telegram `tg.dev` domains
- current Android manifest contains `cybervpn://telegram/callback` and `https://cybervpn.app`, not Telegram `tg.dev` App Links
- current mobile feature gate is driven by `TELEGRAM_BOT_USERNAME`, which is legacy-flow-specific

Still external or secret-backed:

- BotFather client IDs and redirect domains per environment
- Apple Team ID
- production and staging Android signing SHA-256 fingerprints
- GitHub Packages credentials for Android SDK resolution in CI

## BotFather UI Naming

Telegram documentation currently uses both `Web Login` and `Login Widget` for the same BotFather area.

In this package:

- `Web Login` is the name used in core Telegram docs
- `Login Widget` is the name still used in some SDK README examples

## Existing Internal Sources

- [../2026-04-21-registration-auth-current-state.md](../2026-04-21-registration-auth-current-state.md)
- [../oauth-setup-guide.md](../oauth-setup-guide.md)
- `cybervpn_mobile/ios/Runner/Runner.entitlements`
- `cybervpn_mobile/android/app/src/main/AndroidManifest.xml`
- `cybervpn_mobile/lib/core/config/environment_config.dart`
- `cybervpn_mobile/lib/core/services/telegram_auth_service.dart`

## External Sources

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
- Telegram OIDC discovery: <https://oauth.telegram.org/.well-known/openid-configuration>
- Telegram Login SDK for iOS: <https://github.com/TelegramMessenger/telegram-login-ios>
- Telegram Login SDK for Android: <https://github.com/TelegramMessenger/telegram-login-android>

## Status

Draft architecture and implementation package based on code analysis and official Telegram documentation as of `2026-04-21`.

Post-implementation residual tails are tracked in [16-post-implementation-open-items.md](16-post-implementation-open-items.md).
