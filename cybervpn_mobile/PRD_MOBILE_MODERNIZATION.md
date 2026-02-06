# PRD: CyberVPN Mobile App — Modernization & Stability Fix

**Version**: 1.1
**Date**: 2026-02-06
**Author**: Engineering Team (Automated Analysis + Code Review)
**Status**: Draft — Pending Review

---

## 1. Executive Summary

CyberVPN Mobile (Flutter) is a full-featured VPN client with 332 Dart files, Clean Architecture, Riverpod state management, and a feature-rich codebase. The app currently **hangs on the splash screen** during launch, making it unusable. This PRD documents all identified issues and proposes a phased remediation plan to achieve production-grade stability, performance, and code quality.

---

## 2. Current State Analysis

### 2.1 Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Flutter | **3.41.0-0.2.pre (beta)** — pubspec SDK constraint: ^3.10.8 |
| Language | Dart | **3.11.0** (beta) — pubspec constraint: ^3.10.8 |
| State Management | Riverpod 3.x | flutter_riverpod ^3.2.1 |
| Navigation | go_router | ^17.0.0 |
| HTTP | Dio | ^5.9.0 |
| VPN Engine | flutter_v2ray_plus | ^1.0.11 |
| Storage | flutter_secure_storage / shared_preferences | ^10.0.0 / ^2.5.3 |
| Auth | local_auth (biometrics) | ^3.0.0 |
| IAP | purchases_flutter (RevenueCat) | ^9.10.8 |
| Firebase | firebase_core / messaging / analytics | ^4.4.0 / ^16.1.1 / ^12.1.1 |
| Error Monitoring | sentry_flutter | ^9.0.0 |
| Code Gen | freezed / json_serializable / riverpod_generator | ^3.2.5 / ^6.12.0 / ^4.0.3 |
| Build | Android Gradle (Kotlin DSL) | Java 17, minSdk 24 |

### 2.2 Architecture

- **Pattern**: Clean Architecture (domain / data / presentation) per feature
- **Features** (13 modules): auth, vpn, servers, subscription, settings, profile, referral, diagnostics, onboarding, config_import, notifications, quick_actions, quick_setup, widgets, navigation, review
- **DI**: Riverpod Provider overrides via `buildProviderOverrides()` in `providers.dart`
- **Localization**: ARB-based, 33 locales, RTL support (Arabic, Hebrew, Farsi)
- **Theming**: Material You / Dynamic Color with cyberpunk fallback palette

### 2.3 App Startup Flow (Current)

```
main()
  ├─ WidgetsFlutterBinding.ensureInitialized()
  ├─ EnvironmentConfig.init()               // loads .env via flutter_dotenv
  ├─ SharedPreferences.getInstance()         // BLOCKING await
  ├─ ProviderContainer(overrides: ...)       // Eager DI — creates ALL repos, datasources, services
  │   ├─ SecureStorageWrapper()
  │   │   └─ prewarmCache()                  // fire-and-forget async (3 secure storage reads)
  │   ├─ NetworkInfo()
  │   ├─ DeviceIntegrityChecker()
  │   ├─ Dio + ApiClient + AuthInterceptor
  │   ├─ FcmTokenService
  │   ├─ All DataSources (7 concrete instances)
  │   └─ All Repositories (7 concrete instances)
  ├─ addPostFrameCallback → _initializeDeferredServices()
  │   ├─ Firebase.initializeApp()
  │   ├─ PushNotificationService.initialize()
  │   └─ QuickActionsService.initialize()
  ├─ SentryFlutter.init() OR direct _runApp()
  └─ runApp(UncontrolledProviderScope → CyberVpnApp)
       ├─ CyberVpnApp.build() watches 6 providers simultaneously
       │   ├─ quickActionsListenerProvider
       │   ├─ widgetStateListenerProvider
       │   ├─ widgetToggleHandlerProvider
       │   ├─ quickSettingsChannelProvider
       │   ├─ untrustedWifiHandlerProvider
       │   └─ fcmTopicSyncProvider
       └─ GoRouter redirect() watches:
            ├─ isAuthenticatedProvider → authProvider.build()
            │   └─ _checkCachedAuth() → repo.isAuthenticated() → repo.getCurrentUser()
            ├─ shouldShowOnboardingProvider (FutureProvider)
            └─ shouldShowQuickSetupProvider
```

---

## 3. Identified Issues

### 3.1 CRITICAL — Splash Screen Hang (P0)

#### C1: GoRouter redirect depends on unresolved async providers
**File**: `lib/app/router/app_router.dart:150-164`
**Problem**: `appRouterProvider` synchronously watches `isAuthenticatedProvider`, which derives from `authProvider` (an `AsyncNotifier`). While `authProvider.build()` is loading (performing async I/O to check cached tokens), `isAuthenticatedProvider` returns `false`, causing the router to redirect to `/login`. But if the auth check never completes (e.g., SecureStorage hangs on Android), the app stays stuck.
**Root Cause Hypothesis**: `SecureStorageWrapper.prewarmCache()` is fire-and-forget but `authProvider.build()` also reads from `SecureStorage` via `_localDataSource.getCachedToken()`. On some devices, `EncryptedSharedPreferences` can deadlock if accessed concurrently from multiple isolates or threads.

#### C2: Six providers watched in root widget build
**File**: `lib/app/app.dart:48-66`
**Problem**: `CyberVpnApp.build()` calls `ref.watch()` on 6 providers. Several of these create listeners, stream subscriptions, and platform channel calls during initialization. If any of these throws or hangs (e.g., `quickSettingsChannelProvider` on devices without Quick Settings support, `untrustedWifiHandlerProvider` requiring location permission), it blocks the entire widget tree.

#### C3: VpnConnectionNotifier.build() does network I/O
**File**: `lib/features/vpn/presentation/providers/vpn_connection_provider.dart:180-233`
**Problem**: The VPN notifier's `build()` method performs multiple async operations: checks `_repository.isConnected`, loads last server from SecureStorage, checks network connectivity, and potentially starts auto-connect. If the VPN engine initialization hangs (flutter_v2ray_plus native code), this blocks the provider resolution chain.

#### C4: VPN engine re-initialized on every connect
**File**: `lib/features/vpn/data/repositories/vpn_repository_impl.dart:44-52`
**Problem**: `VpnRepositoryImpl.connect()` calls `_engine.initialize()` every time a connection is made, rather than initializing once. This can cause native resource leaks and unpredictable behavior.

#### C5: BiometricService uses deprecated local_auth API — COMPILE ERROR
**File**: `lib/features/auth/domain/usecases/biometric_service.dart:57-60`
**Problem**: The `authenticate()` call passes `biometricOnly` and `persistAcrossBackgrounding` as **direct named parameters** (local_auth 2.x API). In local_auth 3.0.0, these parameters were moved to `AuthenticationOptions`. The code in `biometric_service.dart` does NOT use `AuthenticationOptions`:
```dart
// biometric_service.dart — BROKEN (local_auth 2.x API)
_localAuth.authenticate(
  localizedReason: reason,
  biometricOnly: true,              // ← NOT a valid param in 3.0
  persistAcrossBackgrounding: true,  // ← NOT a valid param in 3.0
);
```
Meanwhile, `app_lock_overlay.dart:54-59` uses the **correct 3.0 API**:
```dart
// app_lock_overlay.dart — CORRECT (local_auth 3.0 API)
localAuth.authenticate(
  localizedReason: '...',
  options: const AuthenticationOptions(
    stickyAuth: true,
    biometricOnly: false,
  ),
);
```
**Impact**: This inconsistency likely causes a compile error or runtime crash during biometric authentication, which can be triggered during startup if app lock is enabled.

#### C6: Flutter SDK on beta channel (3.41.0) — potential instability
**Problem**: The installed Flutter SDK is `3.41.0-0.2.pre` on the **beta channel** while the pubspec constraint is `^3.10.8`. While this satisfies the version constraint, beta SDKs can introduce breaking changes in framework APIs, rendering, and plugin compatibility that are not present in stable releases.
**Risk**: Unpredictable behavior, plugins may not support beta SDK, app store submission may be rejected.

#### C7: `flutter analyze` reports compilation errors
**Problem**: Running `flutter analyze` reveals multiple errors:
- `linkOAuth` method doesn't exist on `ProfileRemoteDataSourceImpl` / `ProfileRepositoryImpl` (6+ errors in tests)
- `linkTelegram` method doesn't exist on `ProfileNotifier` (1 error in test)
- `quick_setup` prefix references undefined name (1 error in test)
- Various `argument_type_not_assignable` errors
**Impact**: Tests cannot run. Profile OAuth features may have incomplete implementations or were removed without updating tests.

### 3.2 HIGH — Dependency & API Issues (P1)

#### H1: `buildProviderOverrides()` returns `List<Object?>` with `.cast()`
**File**: `lib/core/di/providers.dart:182`, `lib/main.dart:35`
**Problem**: The function returns `List<Object?>` and the call site uses `.cast()`. This is a Riverpod 3.x workaround for the `Override` type not being publicly exported, but it's fragile and can cause runtime `CastError` if any override is malformed. This pattern also prevents compile-time type checking.

#### H2: flutter_v2ray_plus at v1.0.11 — last updated Nov 2025
**File**: `pubspec.yaml`
**Problem**: The VPN engine plugin has not been updated in 3+ months and may have compatibility issues with Flutter 3.10.x. The API surface (`initializeVless`, `startVless`, `stopVless`) uses a non-standard naming convention suggesting early development stage.
**Risk**: Native crashes, memory leaks, VPN tunnel failures.

#### H3: `local_auth` — deprecated parameter usage
**File**: `lib/features/auth/domain/usecases/biometric_service.dart:57-60`
**Problem**: `authenticate()` is called with `biometricOnly: true` and `persistAcrossBackgrounding: true`. The `biometricOnly` parameter was deprecated in favor of `AuthenticationOptions`. While it still works, it may be removed in future versions.

#### H4: share_plus requires manual patching
**File**: `cybervpn_mobile/scripts/patch_share_plus.py`
**Problem**: A Python script exists to patch the share_plus plugin, indicating the current version has known issues that require post-install modification. This is fragile and breaks CI/CD reproducibility.

#### H5: in_app_update is Android-only
**File**: `pubspec.yaml` — `in_app_update: ^4.2.4`
**Problem**: This package only supports Android. On iOS, calling any of its methods will throw or return null. No platform guard was found in the codebase.

### 3.3 MEDIUM — Performance Issues (P2)

#### M1: Eager initialization of all 7 repositories + 7 datasources at startup
**File**: `lib/core/di/providers.dart:182-269`
**Problem**: `buildProviderOverrides()` eagerly creates every datasource, repository, Dio client, and service during app launch, regardless of whether they are needed. This adds ~100-300ms to cold start on mid-range devices.
**Fix**: Lazy initialization — only create instances when first accessed.

#### M2: No widget rebuilding optimization
**File**: `lib/app/app.dart`
**Problem**: The root `CyberVpnApp` widget watches multiple providers. Any change to theme, locale, text scale, or any of the 6 listener providers triggers a full rebuild of the `MaterialApp.router` subtree.

#### M3: VPN engine status stream has no `distinct()`
**File**: `lib/features/vpn/data/datasources/vpn_engine_datasource.dart:27`
**Problem**: The status stream listener fires for every status event, including duplicate values. This causes unnecessary UI rebuilds and state updates.

#### M4: `LogInterceptor` in production ApiClient
**File**: `lib/core/network/api_client.dart:44-48`
**Problem**: `LogInterceptor(requestBody: true, responseBody: true)` is always added to Dio, even in production. This logs full request/response bodies (including tokens) to the debug console, impacting both performance and security.

#### M5: No connection pooling or retry logic in ApiClient
**File**: `lib/core/network/api_client.dart`
**Problem**: Each request creates a new connection. No retry interceptor for transient failures (5xx, timeouts). Auth token refresh via `AuthInterceptor` is the only interceptor besides logging.

### 3.4 LOW — Code Quality Issues (P3)

#### L1: Mixed provider patterns — manual vs code-generated
**Problem**: Some providers use `riverpod_generator` (annotation-based) while most use manual `Provider`/`AsyncNotifier` declarations. This inconsistency makes the codebase harder to maintain and prevents leveraging code generation benefits (auto-dispose, type safety).

#### L2: VpnRepositoryImpl runs migration in constructor
**File**: `lib/features/vpn/data/repositories/vpn_repository_impl.dart:38-41`
**Problem**: `_migrateOldConfigsIfNeeded()` is called in the constructor but is async. It runs fire-and-forget, meaning the repository may be used before migration completes, leading to inconsistent state.

#### L3: Freezed entities use `abstract class` (deprecated in Freezed 3.x)
**File**: `lib/features/auth/domain/entities/user_entity.dart:6`
**Problem**: `@freezed abstract class UserEntity with _$UserEntity` — Freezed 3.x recommends `sealed class` or `class` instead of `abstract class`. While still functional, this generates deprecation warnings during code generation.

#### L4: No error boundary widgets
**Problem**: The app uses `ErrorWidget.builder` and `GlobalErrorScreen` for framework errors, but there are no `ErrorBoundary` widgets around individual feature modules. A crash in one feature (e.g., diagnostics) will crash the entire app.

#### L5: `Sentry.configureScope` is deprecated
**File**: `lib/features/auth/presentation/providers/auth_provider.dart:219-226`
**Problem**: `Sentry.configureScope()` was deprecated in sentry_flutter 8.x in favor of `Sentry.getDefaultScope()` or per-event scoping.

#### L6: analysis_options.yaml uses `flutter_lints` instead of `flutter_lints` latest
**File**: `analysis_options.yaml`
**Problem**: Using `flutter_lints: ^6.0.0`. Should verify this is the latest version and all rules are still valid.

#### L7: Android Gradle — no namespace in `build.gradle.kts` for plugins
**File**: `android/build.gradle.kts:24-40`
**Problem**: The root `build.gradle.kts` contains a workaround to extract namespace from `AndroidManifest.xml` for library plugins that don't declare one. This is a known Gradle 8.x migration issue and should be resolved upstream.

---

## 4. Proposed Solution — Phased Approach

### Phase 1: Fix Splash Screen Hang & Critical Build Errors (P0) — 3-4 days

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | **Switch Flutter SDK to stable channel** — Run `flutter channel stable && flutter upgrade`. The current beta channel (3.41.0-0.2.pre) may introduce instability. Stable channel ensures plugin compatibility and app store acceptance. | System-level |
| 1.2 | **Fix BiometricService local_auth API** — Replace deprecated direct named parameters (`biometricOnly`, `persistAcrossBackgrounding`) with `AuthenticationOptions` in `biometric_service.dart`. Match the pattern already used in `app_lock_overlay.dart`. | `biometric_service.dart` |
| 1.3 | **Add splash/loading screen route** — Create a dedicated `/splash` route that shows a branded loading indicator. Router initial location changes from `/` to `/splash`. After auth check resolves, redirect to appropriate screen. | `app_router.dart`, new `splash_screen.dart` |
| 1.4 | **Fix SecureStorage race condition** — Remove `prewarmCache()` fire-and-forget. Instead, `await` it before creating ProviderContainer. Alternatively, make `authProvider.build()` use the pre-warmed cache exclusively. | `main.dart`, `secure_storage.dart`, `providers.dart` |
| 1.5 | **Add timeouts to auth check** — Wrap `_checkCachedAuth()` in `Future.timeout(Duration(seconds: 3))`. On timeout, treat as unauthenticated and proceed to login. | `auth_provider.dart` |
| 1.6 | **Guard root widget providers** — Move 6 `ref.watch()` calls from `CyberVpnApp.build()` to a separate `_AppLifecycleManager` widget that handles errors gracefully. Use `try-catch` and log failures instead of propagating. | `app.dart` |
| 1.7 | **Initialize VPN engine once** — Move `_engine.initialize()` from `VpnRepositoryImpl.connect()` to a one-time initialization (in provider setup or lazy singleton). | `vpn_repository_impl.dart`, `vpn_engine_datasource.dart` |
| 1.8 | **Fix flutter analyze errors** — Fix all compilation errors found by `flutter analyze`: remove references to `linkOAuth`/`linkTelegram` in tests (methods no longer exist), fix `quick_setup` test prefix, fix `argument_type_not_assignable` errors. | `test/features/profile/**`, `test/features/quick_setup/**` |
| 1.9 | **Add startup profiling** — Add `Stopwatch` logs at each initialization step to identify slow operations on real devices. | `main.dart` |

### Phase 2: Dependency Upgrades & API Fixes (P1) — 2-3 days

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | **Audit & upgrade all dependencies** — Run `flutter pub outdated`, upgrade to latest compatible versions. Special attention to: `go_router`, `flutter_riverpod`, `sentry_flutter`, `firebase_*`. Do NOT downgrade any package. | `pubspec.yaml` |
| 2.2 | **Fix provider overrides type safety** — Investigate Riverpod 3.x proper override pattern. If `Override` type is still not exported, create a typed wrapper function. | `providers.dart`, `main.dart` |
| 2.3 | **Remove share_plus patch script** — Either upgrade share_plus to a version that doesn't need patching, or pin to a known-good version. Remove `scripts/patch_share_plus.py`. | `pubspec.yaml`, `scripts/` |
| 2.4 | **Guard in_app_update for iOS** — Add `Platform.isAndroid` check around all `in_app_update` usage. | Search for `in_app_update` imports |
| 2.5 | **Evaluate flutter_v2ray_plus alternatives** — Research `flutter_v2ray_client` (v2.0.0+) as a potential replacement with better maintenance. Document findings and migration path. | Research task |

### Phase 3: Performance Optimization (P2) — 3-4 days

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | **Lazy provider initialization** — Replace eager creation in `buildProviderOverrides()` with lazy `Provider` instances that create resources on first access. Only pre-create: SharedPreferences, SecureStorage, Dio, ApiClient. | `providers.dart` |
| 3.2 | **Split root widget providers** — Extract lifecycle listeners into a `ProviderObserver` or a separate widget subtree that doesn't rebuild the router. | `app.dart` |
| 3.3 | **Add `distinct()` to VPN status stream** — Prevent duplicate status events from causing unnecessary rebuilds. | `vpn_engine_datasource.dart` |
| 3.4 | **Conditionally add LogInterceptor** — Only add in debug/dev builds. Remove `requestBody: true` and `responseBody: true` from production. | `api_client.dart` |
| 3.5 | **Add Dio retry interceptor** — Implement retry with exponential backoff for transient network errors (5xx, timeouts). Max 3 retries. | `api_client.dart`, new `retry_interceptor.dart` |
| 3.6 | **Profile and reduce startup time** — Target: cold start < 2 seconds on mid-range device. Measure with `flutter run --profile`. | All initialization files |

### Phase 4: Code Quality & Modernization (P3) — 4-5 days

| Task | Description | Files |
|------|-------------|-------|
| 4.1 | **Migrate to Riverpod code generation** — Convert manual providers to `@riverpod` annotation-based providers where beneficial. Focus on notifiers and async providers first. | All provider files |
| 4.2 | **Fix Freezed abstract class warnings** — Update entity classes from `abstract class` to `sealed class` per Freezed 3.x guidelines. Re-run `build_runner`. | All `*.freezed.dart` entities |
| 4.3 | **Add ErrorBoundary widgets** — Wrap each feature's root widget with an error boundary that catches rendering errors and shows a feature-specific fallback. | Feature screen files |
| 4.4 | **Fix Sentry deprecated APIs** — Replace `configureScope` with modern Sentry API. | `auth_provider.dart`, any Sentry usage |
| 4.5 | **Await migration in VpnRepositoryImpl** — Convert fire-and-forget migration to proper async initialization with completion tracking. | `vpn_repository_impl.dart` |
| 4.6 | **Update analysis_options.yaml** — Upgrade to latest `flutter_lints`, add stricter rules: `unawaited_futures`, `discarded_futures`, `unnecessary_await_in_return`. | `analysis_options.yaml` |
| 4.7 | **Add startup integration test** — Write a test that verifies the app launches from cold start to the login/connection screen within 5 seconds without hanging. | `integration_test/` |

---

## 5. Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| App launch to interactive screen | **Infinite (hangs)** | < 2 seconds (cold start) |
| Crash-free session rate | Unknown | > 99.5% |
| Flutter analyze warnings | Unknown (many expected) | 0 errors, < 10 warnings |
| Dependency age (oldest package) | 3+ months | < 2 months |
| Test coverage (unit + integration) | Minimal | > 60% for core flows |
| Provider type safety | `List<Object?>` cast | Typed overrides |

---

## 6. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| flutter_v2ray_plus incompatible with Flutter 3.10.x | VPN core broken | Medium | Evaluate `flutter_v2ray_client` as backup; maintain fork if needed |
| Riverpod 3.x `Override` type still not exported | Cannot fix type safety | Low | Use extension methods or submit upstream PR |
| SecureStorage deadlock is device-specific | Cannot reproduce | Medium | Add timeout + fallback; test on multiple Android OEMs |
| Firebase initialization blocks on missing config | Crash on fresh install | Low | Already wrapped in try-catch (good) |
| share_plus breaking changes on upgrade | Share feature broken | Medium | Pin version + add integration test |

---

## 7. Dependencies & Constraints

- **Flutter SDK**: Must stay at ^3.10.8 or upgrade forward
- **Android minSdk**: 24 (Android 7.0) — required by flutter_v2ray_plus
- **No version downgrades**: All dependency changes must be forward-only
- **Backend API**: Auth endpoints must remain compatible during migration
- **App Store**: Changes must not break existing Play Store / App Store listings

---

## 8. Out of Scope

- iOS-specific VPN NetworkExtension implementation
- Backend API changes
- Landing page / marketing site
- New feature development (features freeze during stabilization)
- Admin dashboard changes

---

## 9. Appendix A: File Inventory (Key Files)

| File | Role | Issues |
|------|------|--------|
| `lib/main.dart` | App entry point | C1, M1 |
| `lib/app/app.dart` | Root widget | C2, M2 |
| `lib/app/router/app_router.dart` | Navigation & auth guards | C1 |
| `lib/core/di/providers.dart` | Dependency injection | H1, M1 |
| `lib/core/storage/secure_storage.dart` | Encrypted storage | C1 |
| `lib/core/network/api_client.dart` | HTTP client | M4, M5 |
| `lib/core/config/environment_config.dart` | Environment settings | — |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Auth state | C1, L5 |
| `lib/features/auth/domain/usecases/biometric_service.dart` | Biometrics | H3 |
| `lib/features/vpn/presentation/providers/vpn_connection_provider.dart` | VPN state | C3 |
| `lib/features/vpn/data/datasources/vpn_engine_datasource.dart` | V2Ray engine | C4, M3 |
| `lib/features/vpn/data/repositories/vpn_repository_impl.dart` | VPN repository | C4, L2 |
| `pubspec.yaml` | Dependencies | H2, H4, H5 |
| `android/app/build.gradle.kts` | Android build config | — |
| `analysis_options.yaml` | Lint rules | L6 |

---

## 10. Appendix B: Dependency Audit

**`dart pub outdated` result**: All direct dependencies are up-to-date (as of 2026-02-06).

| Package | Current Version | Status | Notes |
|---------|----------------|--------|-------|
| flutter_riverpod | ^3.2.1 | UP-TO-DATE | Monitor for 4.x |
| go_router | ^17.0.0 | UP-TO-DATE | Stable, feature-complete |
| dio | ^5.9.0 | UP-TO-DATE | |
| flutter_v2ray_plus | ^1.0.11 | RISK | Last update Nov 2025, low maintenance |
| local_auth | ^3.0.0 | API MISMATCH | `biometric_service.dart` uses 2.x API |
| purchases_flutter | ^9.10.8 | UP-TO-DATE | |
| firebase_core | ^4.4.0 | UP-TO-DATE | |
| firebase_messaging | ^16.1.1 | UP-TO-DATE | |
| firebase_analytics | ^12.1.1 | UP-TO-DATE | |
| sentry_flutter | ^9.0.0 | UPGRADE | 9.11.0-beta available |
| flutter_secure_storage | ^10.0.0 | UP-TO-DATE | |
| shared_preferences | ^2.5.3 | UP-TO-DATE | |
| freezed | ^3.2.5 | UP-TO-DATE | |
| freezed_annotation | ^3.0.0 | UP-TO-DATE | |
| share_plus | ^12.0.1 | RISK | Requires Python patch script |
| in_app_update | ^4.2.4 | RISK | Android-only, no iOS guard |
| flutter_lints | ^6.0.0 | UP-TO-DATE | |

**Flutter SDK**: 3.41.0-0.2.pre (beta) — **Should switch to stable channel**
**Dart SDK**: 3.11.0 (beta)
**Transitive upgradable**: `objective_c` 9.2.5 → 9.3.0

---

## 11. Appendix C: Project Statistics

| Metric | Value |
|--------|-------|
| Total Dart files in lib/ | 332 |
| Feature modules | 15 |
| Domain entities | 13+ |
| Repository implementations | 7 |
| Data sources | 7 |
| Provider overrides in DI | 16 |
| Supported locales | 33 |
| Android product flavors | 3 (dev, staging, prod) |
| Integration test files | 1 (auth_flow_test.dart) |
| Lines of code (est.) | ~20,000+ |
