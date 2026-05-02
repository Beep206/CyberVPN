# Post-Implementation Open Items — Telegram Native Login

## Purpose

This document tracks the remaining open items after the code-side implementation of Telegram Native Login for `cybervpn_mobile`.

It exists to separate:

- already mitigated repository-level risks
- remaining external, environment, rollout and device-validation tails

## Current Status

As of `2026-04-21`, the repository implementation is functionally in place:

- backend validates Telegram OIDC `id_token`
- backend issues first-party mobile sessions
- pending mobile TOTP flow is implemented
- Telegram link and unlink are implemented for mobile users
- Flutter, iOS and Android native integrations are implemented
- iOS and Android native SDK code is currently integrated from repository-side sources, not from runtime package download
- metrics and structured logs are in place
- Telegram-specific Grafana dashboard and Prometheus alert rules are in place

The remaining work is no longer centered on core repository logic. The tails are primarily operational, environment-specific and release-oriented.

## Repository-Level Risks Already Removed

The following risks should be treated as closed in the current repository state:

- Mobile auth endpoints are aligned to `/api/v1/mobile/auth/*`.
- Mobile `me` and device management now use mobile auth routes, not web-auth routes.
- Telegram link and unlink flows now exist in the mobile auth namespace.
- Flutter auth parsing normalizes snake_case mobile backend responses before mapping models.
- Unsupported mobile social providers are no longer shown as active login/link options; Telegram remains the supported mobile-native provider.
- Mobile UI entry points that depended on web-only 2FA and delete-account flows were removed from the visible app surface.
- Username-only registration mode is disabled for the mobile contract.
- OTP redirect behavior is disabled for the current mobile registration contract.
- Profile dashboard tests were updated to match the current localized UI contract.

## Relevant Implementation References

Backend:

- `backend/src/presentation/api/v1/mobile_auth/routes.py`
- `backend/src/application/use_cases/mobile_auth/telegram_oidc_auth.py`
- `backend/src/application/use_cases/mobile_auth/complete_two_factor.py`
- `backend/src/application/use_cases/mobile_auth/telegram_oidc_link.py`
- `backend/src/application/use_cases/mobile_auth/telegram_oidc_unlink.py`
- `backend/src/application/use_cases/mobile_auth/list_devices.py`
- `backend/src/application/use_cases/mobile_auth/remove_device.py`

Mobile:

- `cybervpn_mobile/lib/core/constants/api_constants.dart`
- `cybervpn_mobile/lib/core/services/telegram_auth_service.dart`
- `cybervpn_mobile/lib/features/auth/data/datasources/auth_remote_ds.dart`
- `cybervpn_mobile/lib/features/profile/data/datasources/profile_remote_ds.dart`
- `cybervpn_mobile/lib/features/profile/presentation/screens/social_accounts_screen.dart`
- `cybervpn_mobile/lib/features/profile/presentation/screens/profile_dashboard_screen.dart`
- `cybervpn_mobile/lib/features/settings/presentation/screens/settings_screen.dart`
- `cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart`

## Remaining External And Operational Tails

### 1. BotFather And Telegram Environment Setup

Still required:

- final Telegram `client_id` per environment
- final BotFather `Web Login` / `Login Widget` configuration per environment
- final Telegram-managed redirect and login domains
- confirmation of final `tg.dev` host values for iOS and Android

Risk if left unresolved:

- native login may work in local code but fail during real redirect or callback handling in staging/production

### 2. iOS Build And Real Device Validation

Still required:

- macOS + Xcode build verification
- physical iOS device validation with Telegram installed
- final Apple Team ID confirmation
- final Associated Domains value using the real Telegram `app<client_id>-login.tg.dev` host
- final BotFather iOS app registration validation

Risk if left unresolved:

- callback flow may fail only on real hardware or release signing

### 3. Android Release Validation

Still required:

- staging and production signing SHA-256 fingerprints
- BotFather Android package registration using final signing artifacts
- release-signed device verification of App Link callback
- validation on a physical Android device with Telegram installed

Risk if left unresolved:

- debug builds may pass while release callbacks fail because of mismatched package or fingerprint registration

### 4. Feature Flag Rollout

Still required:

- staging environment enablement
- internal-user rollout using feature flags
- limited production rollout
- rollback rehearsal

Risk if left unresolved:

- first production activation may behave as an uncontrolled launch rather than a measured rollout

### 5. Device QA Matrix

Still required:

- iOS device with Telegram installed
- iOS device without Telegram installed
- Android device with Telegram installed
- Android device without Telegram installed
- cancellation path validation
- invalid configuration failure-path validation
- pending TOTP path validation on real devices

Risk if left unresolved:

- edge-case failures will be discovered by users rather than during controlled QA

### 6. Production Operations

Still required:

- staging verification of the Telegram dashboard panels with real traffic
- alert routing verification in Alertmanager for the Telegram-specific auth alerts
- runbook verification during staging rollout

Risk if left unresolved:

- the team may have the right observability artifacts in the repo but still miss operational wiring or noisy thresholds during rollout

## Explicitly Not Open Anymore

These should not be tracked as remaining blockers unless new regressions appear:

- missing mobile OIDC backend endpoint
- missing pending 2FA support for Telegram login
- missing Telegram native SDK bridge in Flutter
- missing iOS callback handling in app code
- missing Android callback handling in app code
- missing Android GitHub Packages access for Telegram SDK resolution in CI for the current repo state
- missing Telegram link and unlink API support
- mobile auth/profile mismatch between supported Telegram flow and visible UI options

## Done Criteria

Telegram Native Login can be treated as fully closed only when all of the following are true:

1. BotFather configuration is finalized for staging and production.
2. iOS real-device callback flow is validated end-to-end.
3. Android release-signed callback flow is validated end-to-end.
4. Feature-flag rollout has been exercised in staging and then limited production.
5. Metrics and rollback procedures are verified by the team operating the release.

## Relationship To Other Documents

- Use [14-rollout-plan.md](14-rollout-plan.md) for phased enablement strategy.
- Use [13-observability-and-runbook.md](13-observability-and-runbook.md) for metrics and incident handling.
- Use [12-testing-and-qa-plan.md](12-testing-and-qa-plan.md) for QA coverage expectations.
- Use [15-implementation-plan.md](15-implementation-plan.md) for the original implementation sequence.
