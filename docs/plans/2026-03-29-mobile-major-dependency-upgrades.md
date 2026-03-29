# Mobile Major Dependency Upgrades Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Safely upgrade the remaining high-risk mobile runtime dependencies without regressing auth, notifications, maps, database access, or startup stability.

**Architecture:** Execute the upgrades in isolated batches instead of a single giant dependency jump. Start with the smallest surface area (`flutter_map`), then auth SDKs, then notifications, then the SQLite/Drift stack and related codegen dependencies. Each batch must finish with targeted tests and a clean `flutter analyze` before moving to the next one.

**Tech Stack:** Flutter, Dart, go_router, flutter_map, google_sign_in, sign_in_with_apple, flutter_local_notifications, drift, sqlite3_flutter_libs, json_serializable

---

### Task 1: Upgrade `flutter_map` 7 -> 8

**Files:**
- Modify: `cybervpn_mobile/pubspec.yaml`
- Modify: `cybervpn_mobile/pubspec.lock`
- Modify: `cybervpn_mobile/lib/features/servers/presentation/screens/server_map_screen.dart`
- Test: `cybervpn_mobile/test/features/servers/presentation/screens/server_map_screen_test.dart` (create if missing)

**Step 1: Update dependency constraint**

Set `flutter_map` to the latest resolvable v8 line in `cybervpn_mobile/pubspec.yaml`.

**Step 2: Refresh packages**

Run:

```bash
flutter pub upgrade flutter_map
```

Expected: `pubspec.lock` updates cleanly.

**Step 3: Fix map API breakages**

- Audit `cybervpn_mobile/lib/features/servers/presentation/screens/server_map_screen.dart`
- Update `MapOptions`, layer declarations, markers, or controller APIs if v8 changed signatures.

**Step 4: Add focused map smoke coverage**

- Ensure the server map screen builds and renders markers without exceptions.

**Step 5: Verify**

Run:

```bash
flutter analyze
flutter test test/features/servers/presentation/screens/server_map_screen_test.dart
```

---

### Task 2: Upgrade `google_sign_in` 6 -> 7

**Files:**
- Modify: `cybervpn_mobile/pubspec.yaml`
- Modify: `cybervpn_mobile/pubspec.lock`
- Modify: `cybervpn_mobile/lib/features/auth/domain/usecases/google_sign_in_service.dart`
- Modify: `cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart`
- Modify: `cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart`
- Test: `cybervpn_mobile/test/features/auth/presentation/screens/login_screen_oauth_test.dart`

**Step 1: Update dependency constraint**

Set `google_sign_in` to the latest resolvable v7 line in `cybervpn_mobile/pubspec.yaml`.

**Step 2: Refresh packages**

Run:

```bash
flutter pub upgrade google_sign_in
```

**Step 3: Fix wrapper/service API changes**

- Update `GoogleSignInService` to the new account/auth/token API.
- Preserve backend OAuth needs: `serverAuthCode` must still be obtained or replaced by a supported flow.
- Keep login/register screens unchanged at the UX layer if possible.

**Step 4: Verify native-wrapper contract**

- Update widget tests to match any changed result objects or cancellation behavior.

**Step 5: Verify**

Run:

```bash
flutter analyze
flutter test test/features/auth/presentation/screens/login_screen_oauth_test.dart
```

---

### Task 3: Upgrade `sign_in_with_apple` 6 -> 7

**Files:**
- Modify: `cybervpn_mobile/pubspec.yaml`
- Modify: `cybervpn_mobile/pubspec.lock`
- Modify: `cybervpn_mobile/lib/features/auth/domain/usecases/apple_sign_in_service.dart`
- Modify: platform config only if required by package upgrade
- Test: targeted auth wrapper tests if present

**Step 1: Update dependency constraint**

Set `sign_in_with_apple` to the latest resolvable v7 line in `cybervpn_mobile/pubspec.yaml`.

**Step 2: Refresh packages**

Run:

```bash
flutter pub upgrade sign_in_with_apple
```

**Step 3: Fix Apple service wrapper**

- Update `SignInWithApple.isAvailable()` and credential APIs if signatures changed.
- Preserve the current “kept in code but disabled in active UI” behavior.

**Step 4: Verify**

Run:

```bash
flutter analyze
flutter test test/features/auth/presentation/screens/login_screen_oauth_test.dart
```

---

### Task 4: Upgrade `flutter_local_notifications` 20 -> 21

**Files:**
- Modify: `cybervpn_mobile/pubspec.yaml`
- Modify: `cybervpn_mobile/pubspec.lock`
- Modify: `cybervpn_mobile/lib/core/services/push_notification_service.dart`
- Test: add/update `cybervpn_mobile/test/core/services/push_notification_service_test.dart`

**Step 1: Update dependency constraint**

Set `flutter_local_notifications` to the latest v21 line in `cybervpn_mobile/pubspec.yaml`.

**Step 2: Refresh packages**

Run:

```bash
flutter pub upgrade flutter_local_notifications
```

**Step 3: Fix notification init and channel APIs**

- Audit `FlutterLocalNotificationsPlugin`, `InitializationSettings`, `AndroidNotificationChannel`, and platform-specific initialization calls.
- Validate foreground notification display still works.

**Step 4: Verify**

Run:

```bash
flutter analyze
flutter test test/core/services/push_notification_service_test.dart
```

---

### Task 5: Upgrade `sqlite3_flutter_libs`, `drift`, `json_annotation`, `meta`

**Files:**
- Modify: `cybervpn_mobile/pubspec.yaml`
- Modify: `cybervpn_mobile/pubspec.lock`
- Modify: `cybervpn_mobile/lib/core/data/database/app_database.dart`
- Regenerate: `cybervpn_mobile/lib/core/data/database/app_database.g.dart`
- Modify: `cybervpn_mobile/lib/features/vpn_profiles/data/datasources/profile_local_ds.dart`
- Modify: `cybervpn_mobile/lib/features/vpn_profiles/data/mappers/profile_mapper.dart`
- Modify: `cybervpn_mobile/lib/features/vpn_profiles/data/repositories/profile_repository_impl.dart`
- Test: `cybervpn_mobile/test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart`

**Step 1: Update dependency constraints**

- Raise `drift`, `sqlite3_flutter_libs`, `json_annotation`, and `meta` to the latest resolvable versions.

**Step 2: Refresh packages**

Run:

```bash
flutter pub upgrade drift sqlite3_flutter_libs json_annotation meta
```

**Step 3: Regenerate database/codegen outputs**

Run:

```bash
dart run build_runner build --delete-conflicting-outputs
```

**Step 4: Fix drift breakages**

- Audit DSL/table changes, `Companion.insert`, `Value(...)`, query/watch methods, and database creation code.
- Keep profile local persistence fully compatible.

**Step 5: Verify**

Run:

```bash
flutter analyze
flutter test test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart
```

---

### Task 6: Final regression and release checklist

**Files:**
- Modify only if regressions require it

**Step 1: Run broad mobile regression suite**

Run:

```bash
flutter analyze
flutter test test/integration/deep_link_integration_test.dart test/perf/startup_smoke_test.dart test/perf/navigation_smoke_test.dart test/app/router/app_router_test.dart test/features/quick_setup/presentation/screens/quick_setup_screen_test.dart test/features/servers/presentation/screens/server_list_screen_test.dart test/features/vpn/presentation/screens/connection_screen_test.dart test/features/vpn/presentation/screens/connection_screen_smoke_test.dart test/shared/widgets/glitch_text_test.dart test/core/auth/token_refresh_coordinator_test.dart test/core/network/auth_interceptor_test.dart test/core/network/websocket_provider_test.dart test/core/network/websocket_client_test.dart test/core/utils/app_logger_test.dart test/features/auth/data/repositories/auth_repository_impl_test.dart test/features/subscription/data/repositories/subscription_repository_impl_test.dart test/features/subscription/data/datasources/subscription_local_ds_test.dart test/features/referral/data/datasources/referral_remote_ds_test.dart test/features/vpn_profiles/data/repositories/profile_repository_impl_test.dart
```

**Step 2: Run final outdated audit**

Run:

```bash
flutter pub outdated --no-dev-dependencies
```

**Step 3: Commit**

```bash
git add cybervpn_mobile/pubspec.yaml cybervpn_mobile/pubspec.lock cybervpn_mobile/lib cybervpn_mobile/test
git commit -m "chore(mobile): upgrade major runtime dependencies"
```
