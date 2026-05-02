# Current State and Gap Analysis

## Current Internal Baseline

См. полный auth-срез:

- [../2026-04-21-registration-auth-current-state.md](../2026-04-21-registration-auth-current-state.md)

Этот документ фиксирует только то, что важно именно для Telegram Native Login.

## Existing Mobile Auth

Текущее мобильное приложение уже использует отдельную mobile token model:

- `cybervpn_mobile` хранит `access_token` и `refresh_token` в secure storage
- `AuthInterceptor` добавляет `Authorization: Bearer ...`
- при `401` мобильный клиент делает refresh
- refresh зависит от `device_id`
- backend already has `/api/v1/mobile/auth/*`

Current code references:

- `cybervpn_mobile/lib/core/network/auth_interceptor.dart`
- `cybervpn_mobile/lib/features/auth/data/datasources/auth_remote_ds.dart`
- `cybervpn_mobile/lib/features/auth/data/repositories/auth_repository_impl.dart`
- `backend/src/presentation/api/v1/mobile_auth/routes.py`

## Existing Mobile Telegram Auth

Current flow:

1. Mobile app checks whether Telegram is installed.
2. App opens `https://oauth.telegram.org/auth?...` in external app/browser.
3. App waits for deep link callback.
4. App receives legacy `auth_data`.
5. App sends `auth_data` to `POST /api/v1/mobile/auth/telegram/callback`.
6. Backend validates legacy Telegram Login Widget / Web Login HMAC payload.
7. Backend creates or finds `MobileUserModel`.
8. Backend registers or updates device.
9. Backend issues mobile `access_token` and `refresh_token`.

Current code references:

- `cybervpn_mobile/lib/core/services/telegram_auth_service.dart`
- `cybervpn_mobile/lib/features/auth/presentation/providers/telegram_auth_provider.dart`
- `cybervpn_mobile/lib/core/config/environment_config.dart`
- `backend/src/application/services/telegram_auth.py`
- `backend/src/application/use_cases/mobile_auth/telegram_auth.py`

## Existing Deep Link And Native Foundations

У проекта уже есть полезная инфраструктура для нативного Telegram login:

- custom scheme `cybervpn://...`
- App Links / Universal Links on `https://cybervpn.app`
- device-aware session model
- secure storage model
- mobile login screen with Telegram entry point
- iOS and Android platform code already handle deep link routing

Current code references:

- `cybervpn_mobile/lib/core/routing/deep_link_parser.dart`
- `cybervpn_mobile/android/app/src/main/AndroidManifest.xml`
- `cybervpn_mobile/ios/Runner/Info.plist`
- `cybervpn_mobile/ios/Runner/Runner.entitlements`

Current readiness snapshot:

- iOS Associated Domains are already enabled, but only for `applinks:cybervpn.app`
- Android already accepts custom scheme and `https://cybervpn.app` links
- current mobile Telegram entry point is configured through `TELEGRAM_BOT_USERNAME`
- current app does not yet expose native SDK config inputs such as Telegram `clientId` and environment-specific `redirectUri`

## Target Flow

Target flow should use:

- official Telegram Native SDK for iOS
- official Telegram Native SDK for Android
- Telegram OIDC `id_token`
- backend validation through Telegram JWKS
- claim validation for `iss`, `aud`, `exp`, `iat`, `sub`
- optional `phone_number` claim when `phone` scope is requested
- first-party mobile token issuance only after backend verification

## Gap Summary

| Area | Current | Target | Gap |
|---|---|---|---|
| Mobile Telegram auth source | Legacy `auth_data` payload | OIDC `id_token` from native SDK | Major |
| Telegram trust model | HMAC widget verification | JWT signature verification via JWKS | Major |
| Primary Telegram identity key | `telegram_id` | OIDC `sub` as primary, `telegram_id` as compatibility field | Major |
| Mobile 2FA behavior | Incomplete for mobile social login | Consistent pending 2FA flow | Major |
| Mobile endpoint shape | Hybrid `/auth/*` and `/mobile/auth/*` usage | Clean mobile namespace for Telegram native login | Medium |
| iOS integration | No official SDK bridge | Native iOS SDK bridge to Flutter | Major |
| Android integration | No official SDK bridge | Native Android SDK bridge to Flutter | Major |
| Observability | No dedicated Telegram native metrics | Dedicated metrics, logs, alerts | Medium |
| Migration strategy | Legacy only | Dual-stack with feature flags and deprecation plan | Medium |

## Known Issues

- Mobile Telegram flow uses legacy `auth_data`, not OIDC `id_token`.
- Backend lacks Telegram OIDC validation layer.
- Mobile login-time 2FA policy is not aligned with web auth.
- Current mobile Telegram endpoint validates legacy HMAC payload and therefore cannot safely accept OIDC `id_token` without a separate validator.
- Some mobile auth paths remain hybrid between `/auth/*` and `/mobile/auth/*`.
- Current mobile model still assumes an email-backed user, while Telegram-only identity should be treated as first-class.
- Current Telegram-only user representation relies on placeholder email; Phase 1 must preserve or explicitly replace this behavior.
- Current mobile client is prepared for `cybervpn://telegram/callback` and `https://cybervpn.app`, but not yet for Telegram-generated `tg.dev` callback surfaces.
- Current mobile Telegram configuration contract is legacy-widget-oriented because it depends on `TELEGRAM_BOT_USERNAME`, not native SDK `clientId` plus `redirectUri`.

## BotFather UI Naming

Telegram core docs currently refer to the relevant BotFather area as `Web Login`, while SDK README files may still call it `Login Widget`.

For implementation purposes, treat these names as the same configuration area.

## Recommended Phase 1 Scope

Phase 1 should solve only the minimum production-grade native Telegram login:

- native login for iOS and Android
- backend `id_token` validation
- account creation and login by Telegram identity
- optional account linking for already authenticated users
- consistent device session registration
- consistent pending 2FA
- legacy endpoint preserved during rollout

Phase 1 should not try to solve:

- every mobile social provider
- reworking web Telegram flows
- full generic identity provider platform for all channels

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
- Telegram OIDC discovery: <https://oauth.telegram.org/.well-known/openid-configuration>
