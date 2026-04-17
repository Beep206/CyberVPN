# CyberVPN Mobile Phase 10 Execution Plan

## Goal

Close Phase 10 from the Happ parity roadmap by turning subscription settings into a real policy layer instead of a storage-only screen.

Phase 10 scope was intentionally limited to:

- effective subscription policy resolution from app settings
- subscription fetch/import requests using the configured `User-Agent`
- due-refresh automation on app startup/resume
- ping-on-open latency refresh for provider-managed profiles
- local update notifications after automatic refresh
- subscription sorting and duplicate-import policy enforcement
- a modular `Subscriptions` settings hub that exposes the new controls honestly

## Planned Tasks

1. Add a runtime service that resolves Happ-like subscription policies from `AppSettings`.
2. Use the effective policy in remote subscription fetch/import flows.
3. Apply duplicate-import behavior and sorting rules at repository/parser level.
4. Extend profile repository refresh flows so ping ordering can be persisted after latency updates.
5. Rebuild `ProfileUpdateNotifier` into a lifecycle policy runner for startup/resume refresh and ping.
6. Add local notification support for automatic subscription updates.
7. Rework `VPN Settings > Subscriptions` into a full operational hub.
8. Verify the phase with targeted analyze plus unit/provider/widget tests.

## Status

Phase 10 is complete.

Completed implementation:

- added subscription runtime policy service in `cybervpn_mobile/lib/features/vpn_profiles/domain/services/subscription_policy_runtime.dart`
- wired policy DI in `cybervpn_mobile/lib/core/di/providers.dart`
- extended subscription URL parsing/import flows in:
  - `cybervpn_mobile/lib/features/config_import/data/parsers/subscription_url_parser.dart`
  - `cybervpn_mobile/lib/features/config_import/data/repositories/config_import_repository_impl.dart`
  - `cybervpn_mobile/lib/features/config_import/presentation/providers/config_import_provider.dart`
- extended provider-profile subscription fetching in:
  - `cybervpn_mobile/lib/features/vpn_profiles/data/datasources/subscription_fetcher.dart`
  - `cybervpn_mobile/lib/features/vpn_profiles/data/repositories/profile_repository_impl.dart`
  - `cybervpn_mobile/lib/features/vpn_profiles/domain/repositories/profile_repository.dart`
  - `cybervpn_mobile/lib/features/vpn_profiles/di/profile_providers.dart`
- added automatic refresh/ping lifecycle runner in `cybervpn_mobile/lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart`
- hooked lifecycle execution into app startup/resume in `cybervpn_mobile/lib/app/app.dart`
- added safe local notification API in `cybervpn_mobile/lib/core/services/push_notification_service.dart`
- rebuilt the subscriptions UX in `cybervpn_mobile/lib/features/settings/presentation/screens/subscription_settings_screen.dart`
- added/updated targeted tests in:
  - `cybervpn_mobile/test/features/vpn_profiles/domain/services/subscription_policy_runtime_test.dart`
  - `cybervpn_mobile/test/features/vpn_profiles/presentation/providers/profile_update_notifier_test.dart`
  - `cybervpn_mobile/test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart`
  - `cybervpn_mobile/test/features/config_import/data/repositories/config_import_repository_impl_test.dart`
  - `cybervpn_mobile/test/features/settings/presentation/screens/subscription_settings_screen_test.dart`

## Acceptance Criteria

| Acceptance Item | Result |
|---|---|
| Effective subscription policy is derived from `AppSettings` and exposes interval, notifications, ping-on-open, sort mode, duplicate policy, connect strategy, `No Filter`, and effective `User-Agent` | Passed |
| Subscription HTTP requests use the effective `User-Agent` and explicit `Accept` headers | Passed |
| Imported config dedupe respects the `Prevent Duplicate Imports` toggle | Passed |
| Subscription payload ordering respects the selected sort mode where runtime data exists | Passed |
| Provider-profile latency refresh can persist ping ordering back to storage | Passed |
| App startup/resume can refresh due provider profiles and imported subscription sources | Passed |
| App startup/resume can optionally refresh provider-profile latencies when `Ping on Open` is enabled | Passed |
| Automatic refresh can raise a local notification when notifications are enabled | Passed |
| `VPN Settings > Subscriptions` exposes the new Happ-like controls and inventory sections | Passed |

## Implementation Details

### 1. Subscription Policy Runtime

`SubscriptionPolicyRuntime` now provides a single runtime snapshot for subscription behavior.

Implemented policy fields:

- `autoUpdateEnabled`
- `autoUpdateInterval`
- `updateNotificationsEnabled`
- `autoUpdateOnOpen`
- `pingOnOpenEnabled`
- `connectStrategy`
- `preventDuplicateImports`
- `collapseSubscriptions`
- `noFilter`
- `userAgentMode`
- `customUserAgent`
- `effectiveUserAgent`
- `sortMode`

Important behavior:

- default `User-Agent` resolves to `${AppConstants.appName}/${AppConstants.appVersion}`
- custom `User-Agent` is only used when mode is `custom` and the value is non-empty
- interval is normalized into `Duration` and clamped into a safe hour range
- sort helpers are centralized so import, fetch, and latency reorder paths behave consistently

### 2. Subscription Fetch and Import Policy

Phase 10 pushed policy into both subscription entry paths:

- imported subscription URLs
- provider-managed remote profiles

`SubscriptionUrlParser` and `SubscriptionFetcher` now send:

- `User-Agent: <effective policy UA>`
- `Accept: */*`

`ConfigImportRepositoryImpl` now:

- applies duplicate prevention only when enabled
- preserves duplicates when the policy disables dedupe
- sorts imported configs for predictable ordering

`ProfileRepositoryImpl.updateSubscription()` now passes existing server metadata into the fetcher so `sort by ping` can reuse stored latency data instead of randomizing server order on refresh.

### 3. Lifecycle Automation

`ProfileUpdateNotifier` is no longer just a manual refresh helper. It now acts as the subscription lifecycle policy runner.

Implemented behavior:

- startup/resume entrypoint via `handleAppOpen(...)`
- debounce guard to avoid repeated runs during rapid lifecycle churn
- skip automation while VPN is connected
- refresh due remote provider profiles
- refresh due imported subscription snapshots
- optionally ping remote profile servers on open
- persist latency maps via `updateProfileServerLatencies(...)`
- emit local notifications after successful automatic refresh
- structured logging of applied policy state

`app.dart` now triggers the lifecycle runner:

- once after first frame on app startup
- again on app resume before websocket reconnect logic

### 4. Subscription Settings Hub

`VPN Settings > Subscriptions` is now a proper operational surface instead of a thin link-out.

The screen now includes:

- summary cards for effective `User-Agent`, automation, startup behavior, and ordering
- automation toggles:
  - auto update
  - interval
  - update notifications
  - update on open
  - ping on open
- behavior controls:
  - connect strategy
  - prevent duplicates
  - collapse sections
  - `No Filter`
  - subscription server sort mode
- `User-Agent` mode selector and custom value editor
- inventory sections for:
  - provider profiles
  - imported subscription snapshots
- existing billing entry points

This gives the app a Happ-like subscription policy hub while staying aligned with current mobile capabilities.

### 5. Notification API Adjustment

`PushNotificationService` now exposes `showLocalNotification(...)` and tracks plugin readiness before attempting to show a local notification.

This phase also updated the local notification callsite to the current named-argument `show(...)` contract used by `flutter_local_notifications`.

## Verification

### Static Analysis

- `dart analyze lib/features/vpn_profiles/domain/services/subscription_policy_runtime.dart lib/core/di/providers.dart lib/features/config_import/data/parsers/subscription_url_parser.dart lib/features/config_import/data/repositories/config_import_repository_impl.dart lib/features/config_import/presentation/providers/config_import_provider.dart lib/features/vpn_profiles/data/datasources/subscription_fetcher.dart lib/features/vpn_profiles/di/profile_providers.dart lib/features/vpn_profiles/domain/repositories/profile_repository.dart lib/features/vpn_profiles/data/repositories/profile_repository_impl.dart lib/core/services/push_notification_service.dart lib/features/vpn_profiles/presentation/providers/profile_update_notifier.dart lib/app/app.dart lib/features/settings/presentation/screens/subscription_settings_screen.dart test/features/settings/presentation/screens/subscription_settings_screen_test.dart test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart test/features/vpn_profiles/domain/services/subscription_policy_runtime_test.dart test/features/vpn_profiles/presentation/providers/profile_update_notifier_test.dart test/features/config_import/data/repositories/config_import_repository_impl_test.dart`
  - Result: `No issues found!`

### Tests

- `flutter test test/features/config_import/data/repositories/config_import_repository_impl_test.dart test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart test/features/vpn_profiles/domain/services/subscription_policy_runtime_test.dart test/features/vpn_profiles/presentation/providers/profile_update_notifier_test.dart test/features/settings/presentation/screens/subscription_settings_screen_test.dart`
  - Result: `All tests passed!`

## Residuals

- `Connect To` is now persisted and exposed in the UI, but full subscription-driven auto-connect orchestration for:
  - last used
  - lowest latency
  - random
  is not yet wired into the global connection entrypoints.
- `No Filter` is now a real policy field with UX and logging, but there is still no deeper client-side filter engine to disable; this is semantics groundwork, not a completed filtering subsystem.
- automatic updates currently run on app lifecycle entrypoints, not through OS-level scheduled background execution.
- on-device E2E for local notification delivery, resume behavior, and real provider subscription refresh was not run in this session.

## References

- Happ App Management: https://www.happ.su/main/ru/dev-docs/app-management
- Happ Ping: https://www.happ.su/main/ru/dev-docs/ping
- `flutter_local_notifications` `show(...)` API: https://pub.dev/documentation/flutter_local_notifications/latest/flutter_local_notifications/FlutterLocalNotificationsPlugin/show.html
- Riverpod `StreamProvider.overrideWithValue(...)`: https://pub.dev/documentation/riverpod/latest/riverpod/StreamProvider-class.html
