# BotFather and Environment Configuration

## Purpose

Собрать все environment-specific настройки, без которых Telegram Native Login нельзя надежно внедрить и поддерживать.

## Telegram Bot Matrix

| Environment | Telegram bot | Client ID | Client Secret location (optional in Phase 1) | Status |
|---|---|---|---|---|
| dev/local | `TBD` | `TBD` | secret manager or local dev secret file | External blocker |
| staging | `TBD` | `TBD` | secret manager | External blocker |
| production | `TBD` | `TBD` | secret manager | External blocker |

Recommended rule:

- staging and production should use separate Telegram bot/client credentials
- local should not use production client secret

## iOS Matrix

| Environment | Bundle ID | Team ID | Redirect URI | Associated Domain | Status |
|---|---|---|---|---|---|
| dev/local | `com.cybervpn.app.dev` | `TBD` | `TBD` | `TBD` | Bundle ID confirmed from repo |
| staging | `com.cybervpn.app.staging` | `TBD` | `TBD` | `TBD` | Bundle ID confirmed from repo |
| production | `com.cybervpn.app` | `TBD` | `TBD` | `TBD` | Bundle ID confirmed from repo |

Recommended production pattern:

- redirect URI: `https://app{appid}-login.tg.dev`
- associated domain: `applinks:app{appid}-login.tg.dev`

Current repo evidence:

- bundle IDs are defined in `cybervpn_mobile/ios/Flutter/*.xcconfig`
- Fastlane references `TEAM_ID` via environment variable
- actual Apple Team ID is not committed to the repository
- current `Runner.entitlements` already contains `com.apple.developer.associated-domains`
- the currently committed associated domain is `applinks:cybervpn.app`
- Telegram `tg.dev` associated domains are not yet configured in the repo

## Android Matrix

| Environment | Package Name | SHA-256 Fingerprint | Redirect URI | App Link Host | Status |
|---|---|---|---|---|---|
| dev/local | `com.cybervpn.cybervpn_mobile.dev` | machine-specific debug fingerprint | `TBD` | `TBD` | Application ID confirmed from repo |
| staging | `com.cybervpn.cybervpn_mobile.staging` | `TBD` | `TBD` | `TBD` | Application ID confirmed, signing fingerprint external |
| production | `com.cybervpn.cybervpn_mobile` | `TBD` | `TBD` | `TBD` | Application ID confirmed, signing fingerprint external |

Recommended production pattern:

- redirect URI: `https://app{appid}-login.tg.dev/tglogin`
- app link host: `app{appid}-login.tg.dev`

Current repo evidence:

- base Android `applicationId` is `com.cybervpn.cybervpn_mobile`
- `dev` and `staging` use `applicationIdSuffix`
- release keystore is supplied through CI or local `key.properties`
- production and staging SHA-256 values are not committed to the repository
- current manifest already contains `cybervpn://telegram/callback`
- current manifest already contains `https://cybervpn.app`
- Telegram `tg.dev` App Link hosts are not yet configured in the repo

## BotFather Checklist

In `@BotFather`, open the bot settings and find the `Web Login` / `Login Widget` section.

Telegram core docs and SDK READMEs currently use both names for the same configuration area.

1. Select the correct bot for the environment.
2. Record the environment-specific `client_id`.
3. Record the environment-specific `client_secret`.
4. Register iOS identifiers:
   - Bundle ID
   - Team ID
   - redirect URI
5. Register Android identifiers:
   - Package Name
   - signing SHA-256 fingerprint
   - redirect URI
6. Confirm allowed URLs and callback domains are exact.

## iOS Setup Notes

Based on the official iOS SDK README:

- install via Swift Package Manager
- register app in BotFather with exact `Bundle ID` and `Team ID`
- prefer the generated `tg.dev` Universal Link
- add `Associated Domains` capability
- route callback URL to `TelegramLogin.handle(url)`

Recommended checklist:

- verify Bundle ID matches the actual app target
- verify Team ID matches the signing team
- add `applinks:` entry exactly as provided by BotFather
- if developer mode is needed during testing, document and isolate that setup from production
- ensure `?mode=developer` is never present in production entitlements or production release setup

## Android Setup Notes

Based on the official Android SDK README:

- add GitHub Packages Maven repository
- add dependency `org.telegram:login-sdk:1.0.0`
- register app in BotFather with exact `Package Name` and signing `SHA-256`
- prefer the generated `tg.dev` App Link
- add an `intent-filter` with `android:autoVerify="true"`
- handle callback through `TelegramLogin.handleLoginResponse(...)`

Recommended checklist:

- capture separate debug and release SHA-256 fingerprints
- do not mix debug keystore values with production registration
- document release signing ownership and renewal process
- verify the SDK artifact can be resolved in CI before rollout work starts

Phase 0 recommendation:

- do not rely on debug SHA-256 for staging or production rollout decisions
- use release-signed staging builds for Telegram callback validation

## Backend Environment Variables

Required for Phase 1 `id_token` validation:

- `TELEGRAM_OIDC_CLIENT_ID`
- `TELEGRAM_OIDC_ISSUER=https://oauth.telegram.org`
- `TELEGRAM_OIDC_JWKS_URL=https://oauth.telegram.org/.well-known/jwks.json`
- `TELEGRAM_OIDC_ALLOWED_AUDIENCE=<client_id>`

Optional or reserved for backend-side code exchange:

- `TELEGRAM_OIDC_CLIENT_SECRET`

Feature flags:

- `TELEGRAM_NATIVE_LOGIN_ENABLED`
- `TELEGRAM_NATIVE_LOGIN_IOS_ENABLED`
- `TELEGRAM_NATIVE_LOGIN_ANDROID_ENABLED`
- `TELEGRAM_NATIVE_LOGIN_PHONE_SCOPE_ENABLED`

Phase 1 note:

Phase 1 does not require backend-side authorization code exchange unless we explicitly decide to move away from the official native SDK token result.

## Current Mobile Config Contract

Current mobile Telegram login is enabled through legacy config:

- `TELEGRAM_BOT_USERNAME`

Current repo behavior:

- when `TELEGRAM_BOT_USERNAME` is empty, Telegram login is unavailable
- `TelegramAuthService` builds a legacy `https://oauth.telegram.org/auth?...` URL
- callback target is `cybervpn://telegram/callback`

Phase 0 implication:

- native Telegram login must introduce environment-specific config for `clientId`
- native Telegram login must introduce environment-specific config for `redirectUri`
- the app must support migration from bot-username-only config to SDK-oriented config without breaking legacy fallback

## CI/CD Requirements

### Android

- GitHub Packages username and token must be available in CI.
- Token must have `read:packages`.
- Debug and release SHA-256 fingerprints must be registered separately if both are tested.
- Release build must be able to resolve `org.telegram:login-sdk:1.0.0` in CI before rollout work starts.
- current repository workflows do not yet include Telegram SDK package credentials, so this remains an explicit Phase 0 blocker

### iOS

- Associated Domains must be configured per target and environment.
- `?mode=developer` must not be present in production entitlements.
- Physical-device callback testing must be part of staging exit criteria.

## Current Repo-Derived Values

### iOS

- `dev/local`: `com.cybervpn.app.dev`
- `staging`: `com.cybervpn.app.staging`
- `production`: `com.cybervpn.app`
- current associated domain in repo: `applinks:cybervpn.app`

### Android

- `dev/local`: `com.cybervpn.cybervpn_mobile.dev`
- `staging`: `com.cybervpn.cybervpn_mobile.staging`
- `production`: `com.cybervpn.cybervpn_mobile`
- current committed deep link host: `cybervpn://telegram/callback`
- current committed universal/app link host: `https://cybervpn.app`

## Secrets Handling

- If provisioned, Client Secret must live in secret manager, not in repo.
- Mobile apps must never embed Telegram Client Secret.
- Backend is the only component allowed to know Telegram Client Secret.
- Rotate secrets via runbook and environment-by-environment update.

## Ownership

| Artifact | Owner |
|---|---|
| Telegram bot | `TBD` |
| BotFather config | `TBD` |
| iOS Bundle ID and Team ID | `TBD` |
| Android Package Name and SHA-256 fingerprints | `TBD` |
| Mobile env contract for Telegram native login | `TBD` |
| Backend env vars and secrets | `TBD` |
| App Link / Universal Link verification | `TBD` |

## External References

- Telegram Login docs: <https://core.telegram.org/bots/telegram-login>
- Telegram Login SDK for iOS: <https://github.com/TelegramMessenger/telegram-login-ios>
- Telegram Login SDK for Android: <https://github.com/TelegramMessenger/telegram-login-android>
