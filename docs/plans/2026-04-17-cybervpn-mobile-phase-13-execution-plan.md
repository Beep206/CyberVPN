# CyberVPN Mobile Phase 13 Execution Plan

## Goal

Close Phase 13 from the Happ advanced-settings roadmap by shipping formal reset flows and documenting the final rollout/QA contract for the expanded advanced-settings scope.

Phase 13 scope was intentionally limited to:

- formal `Other Settings > Reset` IA instead of debug-only reset entrypoints
- `Reset Settings` with non-destructive settings-only semantics
- `Full App Reset` with an explicit local-data wipe contract
- safe orchestration for VPN disconnect, auth/session cleanup, local profile cleanup, and log cleanup
- a manual QA matrix for Android, iOS reduced subset, upgrade path, and rollback path
- an observability checklist for runtime, subscription, ping, and reset flows

## Planned Tasks

1. Implement secure wipe primitives so `Full App Reset` can clear feature-specific secure-storage keys instead of only auth tokens.
2. Add a dedicated reset service that wipes `SharedPreferences`, secure storage, Drift profile data, and file-backed logs according to an explicit product contract.
3. Add a reset controller that disconnects VPN, resets SDK/session state, and invalidates app-scoped providers safely.
4. Add `Other Settings > Reset` screen and router/search wiring.
5. Verify the phase with targeted analyze and targeted tests.
6. Document QA matrix, observability checklist, and rollout guidance.

## Status

Phase 13 is complete.

Completed implementation:

- extended secure wipe semantics in `cybervpn_mobile/lib/core/storage/secure_storage.dart`
- added destructive reset service in `cybervpn_mobile/lib/features/settings/data/services/app_reset_service.dart`
- added reset orchestration providers in `cybervpn_mobile/lib/features/settings/presentation/providers/app_reset_providers.dart`
- added formal reset UI in `cybervpn_mobile/lib/features/settings/presentation/screens/reset_settings_screen.dart`
- wired reset into `Other Settings` in:
  - `cybervpn_mobile/lib/features/settings/presentation/screens/other_settings_screen.dart`
  - `cybervpn_mobile/lib/features/settings/presentation/widgets/settings_search.dart`
  - `cybervpn_mobile/lib/app/router/app_router.dart`
- added and updated targeted tests in:
  - `cybervpn_mobile/test/core/storage/secure_storage_test.dart`
  - `cybervpn_mobile/test/features/settings/data/services/app_reset_service_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/reset_settings_screen_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/other_settings_screen_test.dart`

## Acceptance Criteria

| Acceptance Item | Result |
|---|---|
| `Reset Settings` exists in formal settings IA and does not touch local profiles, imported configs, logs, or auth/session data | Passed |
| `Full App Reset` exists in formal settings IA and clears only the explicitly contracted local areas | Passed |
| `Full App Reset` disconnects active VPN before wiping local state | Passed |
| destructive actions require explicit confirmation dialogs | Passed |
| secure wipe covers feature-specific secure-storage keys such as OAuth temp state and encryption master keys | Passed |
| rollout/QA guidance documents Android-first support and reduced iOS subset clearly | Passed |
| Phase 13 passes targeted analysis and tests | Passed |

## Implementation Details

### 1. Reset Contract

Phase 13 formalizes two different reset behaviors instead of conflating them:

- `Reset Settings`
  - resets only the `settings.*` contract handled by `SettingsRepository`
  - preserves:
    - imported configs
    - VPN profiles
    - logs
    - auth/session data
- `Full App Reset`
  - clears:
    - settings
    - imported configs
    - VPN profiles
    - subscription metadata and local caches
    - in-memory and persistent logs
    - auth/session data
  - preserves:
    - device identity

Device identity is intentionally preserved because CyberVPN still relies on a stable local device identifier for backend/device-registration semantics. This is an explicit part of the reset contract, not an accident.

### 2. Secure Wipe Primitive

Before this phase, `SecureStorageWrapper.clearAll()` was logout-oriented and did not wipe every feature-specific secure key.

Phase 13 added `wipeAll(...)`, which clears the full secure-storage namespace and can optionally restore the device ID afterward.

That closes a real gap for:

- `oauth_state`
- `oauth_provider`
- `encrypted_field_master_key`
- biometric feature flags and related secure data

This keeps `Full App Reset` honest for the advanced-settings scope that now spans subscriptions, encrypted profile URLs, and richer auth integrations.

### 3. Full Reset Orchestration

`AppResetController` now coordinates the destructive flow:

1. disconnect active VPN if needed
2. cancel token refresh
3. disconnect WebSocket
4. reset RevenueCat user best-effort
5. wipe local state via `AppResetService`
6. clear device-service cache
7. invalidate app-scoped providers so router/state rebuild from the wiped storage baseline

This prevents partial reset states where storage is empty but long-lived providers still expose stale in-memory data.

### 4. Formal Settings IA

Reset is now available through:

- `Settings > Other Settings > Reset`

The screen exposes:

- `Reset Settings`
- `Full App Reset`
- explicit scope explanation for what full reset removes
- explicit note that device identity is preserved

This closes the old debug-only gap while keeping the existing debug utilities intact for engineering use.

## Manual QA Matrix

### Android Supported Path

- Confirm `Settings > Other Settings > Reset` is reachable from both phone and tablet layouts.
- Confirm `Reset Settings` restores VPN/ping/subscription/appearance toggles to defaults without deleting profiles or imported configs.
- Connect VPN, trigger `Full App Reset`, and confirm:
  - active tunnel disconnects
  - local profiles are removed
  - imported configs are removed
  - logs are removed
  - app returns to onboarding/login flow
- Reopen app and confirm state is fresh except for preserved device identity behavior.

### iOS Reduced Subset

- Confirm reset screen is reachable and confirmation dialogs work.
- Confirm `Reset Settings` still behaves as settings-only reset.
- Confirm `Full App Reset` clears local settings/data and returns app to onboarding/login flow.
- Confirm reduced-capability VPN settings remain hidden/reduced exactly as in Phase 4 support matrix after reset.

### Upgrade / Migration Path

- Install build with populated settings, imported configs, VPN profiles, and logs.
- Upgrade to Phase 13 build.
- Confirm reset screen reflects the correct scope without migration crashes.
- Execute `Reset Settings` first, then verify existing user data still remains.
- Execute `Full App Reset` and verify no stale provider state survives across app restart.

### Rollback Path

- Install Phase 13 build, populate advanced settings, then downgrade to the previous build candidate.
- Verify the previous build tolerates missing reset-route state and wiped storage without startup failure.
- Verify the app remains usable after Phase 13 `Full App Reset` followed by downgrade.

## Observability Checklist

- Runtime logs:
  - confirm VPN disconnect prior to full reset when a tunnel is active
  - confirm no stale runtime-connect state remains afterward
- Subscription actions:
  - confirm provider-managed profiles and imported subscription metadata disappear after full reset
- Ping actions:
  - confirm `Ping Settings` revert to defaults after `Reset Settings`
- Reset audit:
  - confirm the reset screen is the only formal destructive surface under `Other Settings`
  - confirm persistent logs are actually cleared by `Full App Reset`

## Verification

### Static Analysis

- `dart analyze lib/core/storage/secure_storage.dart lib/features/settings/data/services/app_reset_service.dart lib/features/settings/presentation/providers/app_reset_providers.dart lib/features/settings/presentation/screens/reset_settings_screen.dart lib/features/settings/presentation/screens/other_settings_screen.dart lib/features/settings/presentation/widgets/settings_search.dart lib/app/router/app_router.dart test/core/storage/secure_storage_test.dart test/features/settings/data/services/app_reset_service_test.dart test/features/settings/presentation/screens/reset_settings_screen_test.dart test/features/settings/presentation/screens/other_settings_screen_test.dart`
  - Result: `No issues found!`

### Tests

- `flutter test test/core/storage/secure_storage_test.dart test/features/settings/data/services/app_reset_service_test.dart test/features/settings/presentation/screens/reset_settings_screen_test.dart test/features/settings/presentation/screens/other_settings_screen_test.dart`
  - Result: `All tests passed!`

## Rollout Notes

- Android remains the primary supported path for the broader advanced-settings parity surface.
- iOS continues to ship the reduced subset already defined in Phase 4; Phase 13 does not widen runtime capability claims.
- `Full App Reset` is local-only. It does not delete the backend account or remote provider data.
- `App Auto Start` semantics remain the Phase 11 contract: Android handoff to OS/OEM settings. Phase 13 did not change that behavior.

## Residuals

- `Full App Reset` intentionally preserves device identity; if product later wants a true “fresh install” semantics, that requires a separate contract change.
- legacy debug utilities still contain reset/cache tooling, but reset is no longer debug-only because the formal surface now exists under `Other Settings`.
- full on-device E2E for Android/iOS destructive reset, app relaunch, and OEM-specific app-state restoration was not run in this session.

## References

- Happ App Management: https://www.happ.su/main/ru/dev-docs/app-management
- Happ Routing: https://www.happ.su/main/ru/dev-docs/routing
- Happ Ping: https://www.happ.su/main/ru/dev-docs/ping
