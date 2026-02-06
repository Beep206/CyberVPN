# PRD: CyberVPN Mobile App — Modernization & Stability Fix

**Version**: 2.1
**Date**: 2026-02-06
**Author**: Engineering Team (mobile-lead + senior-flutter + flutter-code-reviewer Analysis)
**Status**: Draft — Pending Review
**Analyzers**: mobile-lead agent, senior-flutter skill, flutter-code-reviewer agent

---

## 1. Executive Summary

CyberVPN Mobile (Flutter) is a full-featured VPN client with **332 Dart files** (~87,600 LOC), Clean Architecture, Riverpod 3.x state management, and 15 feature modules. The app currently **hangs on the splash screen** during launch, making it unusable.

`flutter analyze` reports **2 compile errors** in production code, **10+ compile errors** in test code, **27 warnings**, and **60+ info-level issues**. Test suite cannot execute at all.

This PRD v2.1 documents **35 identified issues** (8 critical, 9 high, 7 medium, 11 low), a precise root cause analysis of the splash screen hang, and a 4-phase remediation plan organized by the senior-flutter skill's production-readiness criteria.

---

## 2. Current State Analysis

### 2.1 Tech Stack

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Framework | Flutter | **3.41.0-0.2.pre (BETA)** | RISK — should be stable |
| Language | Dart | **3.11.0-296.4.beta** | RISK — beta channel |
| State Management | flutter_riverpod | ^3.2.1 | OK |
| Navigation | go_router | ^17.0.0 | OK |
| HTTP | Dio | ^5.9.0 | OK |
| VPN Engine | flutter_v2ray_plus | ^1.0.11 | RISK — stale (Nov 2025) |
| Secure Storage | flutter_secure_storage | ^10.0.0 | DEPRECATED param |
| Local Storage | shared_preferences | ^2.5.3 | OK |
| Biometrics | local_auth | ^3.0.0 | API MISMATCH |
| IAP | purchases_flutter (RevenueCat) | ^9.10.8 | OK |
| Firebase | core / messaging / analytics | ^4.4.0 / ^16.1.1 / ^12.1.1 | OK |
| Monitoring | sentry_flutter | ^9.0.0 | DEPRECATED API |
| Sharing | share_plus | ^12.0.1 | RISK — needs patch |
| Updates | in_app_update | ^4.2.4 | OK (guarded) |
| Code Gen | freezed / json_serializable | ^3.2.5 / ^6.12.0 | DEPRECATED pattern |
| Build | Android Gradle (Kotlin DSL) | Java 17, minSdk 24 | OK |

### 2.2 Architecture

- **Pattern**: Clean Architecture (domain / data / presentation) per feature
- **Features** (15 modules): auth, vpn, servers, subscription, settings, profile, referral, diagnostics, onboarding, config_import, notifications, quick_actions, quick_setup, widgets, navigation, review
- **DI**: Riverpod Provider overrides via `buildProviderOverrides()` returning `List<Object?>` with unsafe `.cast()`
- **Localization**: ARB-based, 33 locales, RTL support (Arabic, Hebrew, Farsi)
- **Theming**: Material You / DynamicColorBuilder with cyberpunk fallback palette

### 2.3 App Startup Flow (Current — Annotated with Issues)

```
main()
  ├─ WidgetsFlutterBinding.ensureInitialized()
  ├─ EnvironmentConfig.init()               // loads .env via flutter_dotenv
  ├─ await SharedPreferences.getInstance()  // BLOCKING await (~10-50ms)
  ├─ ProviderContainer(overrides: buildProviderOverrides(prefs).cast())
  │   ├─ SecureStorageWrapper()
  │   │   └─ prewarmCache()                 // ⚠ FIRE-AND-FORGET — 3 SecureStorage reads
  │   │      └─ accessToken, refreshToken, cachedUser (parallel Future.wait)
  │   ├─ NetworkInfo()
  │   ├─ DeviceIntegrityChecker(prefs)
  │   ├─ Dio + ApiClient(dio, baseUrl)
  │   │   └─ LogInterceptor(requestBody:true, responseBody:true) // ⚠ ALWAYS ON — leaks in prod
  │   ├─ AuthInterceptor(secureStorage, dio)
  │   ├─ FcmTokenService(apiClient)
  │   ├─ 7 DataSources (eager)              // ⚠ M1: unnecessary eager init
  │   ├─ 7 Repositories (eager)             // ⚠ M1: unnecessary eager init
  │   │   └─ VpnRepositoryImpl()
  │   │       └─ _migrateOldConfigsIfNeeded() // ⚠ L2: FIRE-AND-FORGET async in constructor
  │   └─ 16 provider overrides
  │       └─ sharedPreferencesProvider override (from server_list_provider.dart ONLY)
  │           └─ ⚠ C8: quick_setup_provider.dart declares its OWN sharedPreferencesProvider — NEVER overridden
  │
  ├─ addPostFrameCallback → _initializeDeferredServices()
  │   ├─ Firebase.initializeApp()           // ✓ try-catch wrapped
  │   ├─ PushNotificationService.initialize()
  │   │   └─ AppLogger.info('FCM token: $_token')  // ⚠ H7: token logged in plaintext
  │   └─ QuickActionsService.initialize()
  │
  ├─ SentryFlutter.init() OR direct _runApp()
  └─ runApp(UncontrolledProviderScope → CyberVpnApp)
       │
       ├─ CyberVpnApp.build() watches 6 providers:  // ⚠ C2: any hang blocks entire tree
       │   ├─ quickActionsListenerProvider
       │   ├─ widgetStateListenerProvider
       │   ├─ widgetToggleHandlerProvider
       │   ├─ quickSettingsChannelProvider
       │   ├─ untrustedWifiHandlerProvider
       │   └─ fcmTopicSyncProvider
       │
       ├─ DynamicColorBuilder → MaterialApp.router
       │   └─ builder: wraps child with Directionality + MediaQuery (text scale)
       │
       └─ GoRouter redirect() watches:
            ├─ isAuthenticatedProvider → authProvider.build()
            │   └─ _checkCachedAuth()
            │       ├─ _repo.isAuthenticated() → secureStorage.read('access_token')
            │       │   └─ ⚠ C1: RACES with prewarmCache() — EncryptedSharedPreferences deadlock
            │       └─ _repo.getCurrentUser() → secureStorage.read('cached_user')
            │
            ├─ shouldShowOnboardingProvider (FutureProvider → SharedPreferences)
            │
            ├─ shouldShowQuickSetupProvider → quickSetupProvider.build()
            │   └─ ref.watch(sharedPreferencesProvider) — ⚠ C8: THROWS UnimplementedError
            │       (this is quick_setup's LOCAL provider, NOT the overridden one)
            │
            └─ quickActionsHandlerProvider (kept alive)
```

### 2.4 flutter analyze Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| **error** (lib/) | 2 | `app_lock_overlay.dart:56` — `AuthenticationOptions` doesn't exist in local_auth 3.0 |
| **error** (test/) | 10+ | Mock overrides don't match updated AuthRepository signatures; `linkOAuth` removed |
| **warning** | 27 | 22 × `inference_failure_on_function_invocation`, 3 × `unused_local_variable`, 1 × `unused_import` |
| **info** | 60+ | deprecated APIs (`Share.share`, `Radio.groupValue`, `encryptedSharedPreferences`), missing `const`, `use_build_context_synchronously` |

---

## 3. Identified Issues

### 3.1 CRITICAL — Splash Screen Hang & Build Failures (P0)

#### C1: SecureStorage race condition blocks auth resolution
**File**: `lib/core/di/providers.dart:190`, `lib/core/storage/secure_storage.dart:103-113`
**Problem**: `prewarmCache()` is fire-and-forget in `buildProviderOverrides()`. Meanwhile `authProvider.build()` → `_checkCachedAuth()` also reads the same SecureStorage keys. On Android with `encryptedSharedPreferences: true` (deprecated), EncryptedSharedPreferences can deadlock when accessed concurrently — the Android Keystore may serialize operations, causing the second access to wait indefinitely for the first to release the lock.
**Evidence**: `secure_storage.dart:39` uses deprecated `AndroidOptions(encryptedSharedPreferences: true)`. The deprecation notice states: "The Jetpack Security library is deprecated by Google."
**Impact**: Auth check never resolves → GoRouter redirect hangs → native splash screen never dismissed.

#### C2: Root widget watches 6 providers — any hang blocks entire tree
**File**: `lib/app/app.dart:48-65`
**Problem**: `CyberVpnApp.build()` calls `ref.watch()` on 6 providers simultaneously. These create platform channel listeners, stream subscriptions, and network monitors. If any provider's initialization throws or hangs (e.g., `quickSettingsChannelProvider` on devices without Quick Settings tile support, `untrustedWifiHandlerProvider` waiting for location permission), it blocks `MaterialApp.router` rendering.
**Impact**: The widget tree never builds, splash screen stays visible.

#### C3: VpnConnectionNotifier.build() does heavy async I/O
**File**: `lib/features/vpn/presentation/providers/vpn_connection_provider.dart:180-233`
**Problem**: `build()` performs: check `_repository.isConnected` (V2Ray native call), load last server from SecureStorage, check network connectivity, read vpnSettings, read authProvider state, potentially trigger auto-connect. Creates 3 stream subscriptions (state, network, WebSocket). If V2Ray engine native code hangs during `isConnected` check, this blocks the entire provider chain.
**Impact**: Blocks VPN-dependent UI from rendering.

#### C4: VPN engine re-initialized on every connect() + stream subscription leak
**File**: `lib/features/vpn/data/repositories/vpn_repository_impl.dart:44-49`, `lib/features/vpn/data/datasources/vpn_engine_datasource.dart:27-29`
**Problem**: Two issues in one:
1. `VpnRepositoryImpl.connect()` calls `_engine.initialize()` every time — creates native resources repeatedly
2. Inside `initialize()`, `v2ray.onStatusChanged.listen(...)` is called but the `StreamSubscription` is never stored or cancelled. Each `connect()` creates a new orphan subscription.
**Impact**: Growing memory leak with each reconnect. Native resource exhaustion.

#### C5: app_lock_overlay.dart — COMPILE ERROR (local_auth 3.0 API mismatch)
**File**: `lib/features/auth/presentation/widgets/app_lock_overlay.dart:54-59`
**Problem**: Uses `AuthenticationOptions` class and `options:` named parameter which **do not exist** in `local_auth 3.0.0`. Confirmed by flutter analyze:
```
error • The named parameter 'options' isn't defined • app_lock_overlay.dart:56:9
error • The name 'AuthenticationOptions' isn't a class • app_lock_overlay.dart:56:24
```
**Impact**: If app lock is enabled and biometric fails (triggering PIN fallback), calling `_attemptPinUnlock()` crashes. In release mode, R8 tree-shaking may exclude this dead code — but if the code path is reached, it's a hard crash.

#### C6: biometric_service.dart uses deprecated local_auth 2.x direct params
**File**: `lib/features/auth/domain/usecases/biometric_service.dart:57-61`
**Problem**: `authenticate()` passes `biometricOnly: true` and `persistAcrossBackgrounding: true` as direct named parameters. In `local_auth 3.0.0`, `biometricOnly` was deprecated and `persistAcrossBackgrounding` is undocumented. While this currently compiles (the parameters still exist as deprecated), the behavior is undefined and will break in future local_auth versions.
**Impact**: Biometric authentication may silently use incorrect defaults.

#### C7: Flutter SDK on beta channel (3.41.0-0.2.pre)
**Problem**: Flutter SDK is on `beta` channel (3.41.0-0.2.pre, Dart 3.11.0-296.4.beta). Beta SDKs:
- May introduce framework-level rendering regressions
- Plugins may not test against beta
- App Store / Play Store submission may fail with beta-built binaries
- `Radio.groupValue` / `Radio.onChanged` deprecation warnings only appear in Flutter 3.32+ beta
**Impact**: Unpredictable behavior across the entire app.

#### C8: Duplicate `sharedPreferencesProvider` — quick_setup NEVER overridden
**File**: `lib/features/quick_setup/presentation/providers/quick_setup_provider.dart:142-147`
**Problem**: `quick_setup_provider.dart` declares its own `sharedPreferencesProvider` (line 142). The DI override in `providers.dart:250` only overrides the one imported from `server_list_provider.dart`. These are **two different Dart symbols** with the same name from different libraries. `QuickSetupNotifier.build()` (line 57) calls `ref.watch(sharedPreferencesProvider)` which resolves to the LOCAL (unoverridden) one, throwing `UnimplementedError`.
**Chain reaction**:
1. `quickSetupProvider` goes to `AsyncError` state
2. `shouldShowQuickSetupProvider` returns `true` (default when value is null)
3. GoRouter redirects authenticated users to `/quick-setup`
4. `QuickSetupScreen` tries to use `quickSetupProvider` → same crash
5. Infinite error → redirect loop for authenticated users
**Impact**: Authenticated users are trapped in a crashing quick-setup redirect loop.

### 3.2 HIGH — Security & API Issues (P1)

#### H1: `buildProviderOverrides()` returns `List<Object?>` with unsafe `.cast()`
**File**: `lib/core/di/providers.dart:182`, `lib/main.dart:35`
**Problem**: Returns `List<Object?>`, caller does `.cast()` without type argument. This bypasses Riverpod's type-safe override system. If any entry is not a valid `Override`, runtime `CastError` crashes the app immediately on startup.
**Impact**: Fragile startup — any typo or mismatched provider crashes the entire app.

#### H2: FCM token logged in plaintext
**File**: `lib/core/services/push_notification_service.dart:116,121`
**Problem**: Full FCM device token is logged via `AppLogger.info('FCM token: $_token')` and `AppLogger.info('FCM token refreshed: $newToken')`. If logs are collected by Sentry, crash reporting, or written to disk/logcat, the token is exposed.
**Impact**: Attackers with log access can send unsolicited push notifications to user devices.

#### H3: VPN engine stream subscription never cancelled
**File**: `lib/features/vpn/data/datasources/vpn_engine_datasource.dart:27-29`
**Problem**: `v2ray.onStatusChanged.listen((status) { _lastStatus = status; })` — the `StreamSubscription` returned by `.listen()` is discarded. Each call to `initialize()` (called on every `connect()`) adds a new orphan listener. The `dispose()` method only nulls `_v2ray` and `_lastStatus`, not the subscription.
**Impact**: Memory leak growing linearly with reconnections. Old subscriptions process stale events.

#### H4: `LogInterceptor` always enabled — leaks tokens in production
**File**: `lib/core/network/api_client.dart:44-48`
**Problem**: `LogInterceptor(requestBody: true, responseBody: true)` is added unconditionally. In production:
- Logs JWT access tokens from Authorization headers
- Logs refresh tokens from refresh request bodies
- Logs user credentials during login/register
- Performance overhead: serializing full request/response bodies to string
**Impact**: Security: credentials visible in logcat. Performance: unnecessary string operations on every HTTP request.

#### H5: flutter_v2ray_plus at v1.0.11 — stale dependency (Nov 2025)
**File**: `pubspec.yaml`
**Problem**: The VPN engine plugin hasn't been updated in 3+ months. API naming (`initializeVless`, `startVless`, `stopVless`, `VlessStatus`) suggests early development. No guarantee of compatibility with Flutter 3.10+.
**Risk**: Native crashes, memory leaks, VPN tunnel failures. No upstream support for bug fixes.

#### H6: share_plus requires manual Python patch script
**File**: `scripts/patch_share_plus.py`
**Problem**: A Python script exists to patch the share_plus plugin post-install. This:
- Breaks CI/CD reproducibility (patch must run after every `flutter pub get`)
- Fragile against any share_plus version update
- Not documented in pubspec.yaml or build scripts
**Impact**: CI builds may fail silently if patch is not applied.

#### H7: `encryptedSharedPreferences` deprecated in flutter_secure_storage
**File**: `lib/core/storage/secure_storage.dart:39`
**Problem**: `AndroidOptions(encryptedSharedPreferences: true)` — deprecated. The deprecation notice states: "The Jetpack Security library is deprecated by Google. Your data will be automatically migrated to custom ciphers on first access. Remove this parameter."
**Impact**: Will stop compiling in flutter_secure_storage v11. The deprecated migration path may cause slow first-access on app update (contributing to C1 splash screen hang).

#### H8: Certificate pinning effectively disabled by default
**Files**: `lib/core/config/environment_config.dart:64-67`, `lib/core/security/certificate_pinner.dart:57-69`
**Problem**: `CERT_FINGERPRINTS` dart-define defaults to empty string, meaning certificate pinning is disabled by default. In `kDebugMode` validation is bypassed entirely. The build.gradle.kts product flavors do not set `CERT_FINGERPRINTS`, and there is no documentation of required fingerprints. Production builds are only pinned if explicitly passing `--dart-define=CERT_FINGERPRINTS=...` during build.
**Impact**: MITM attacks possible in production if fingerprints not configured during build. False sense of security from the `CertificatePinner` class existing.

#### H9: CertificatePinner logs fingerprints in debug output
**File**: `lib/core/security/certificate_pinner.dart:73-82`
**Problem**: Certificate fingerprints, subjects, and issuers are logged at debug level. On rooted devices with debug log capture, this provides attackers with the exact certificate fingerprints the app expects, making it easier to prepare MITM attacks.
**Impact**: Reduces effectiveness of certificate pinning when combined with rooted device access.

### 3.3 MEDIUM — Performance Issues (P2)

#### M1: Eager initialization of all 14 DI objects at startup
**File**: `lib/core/di/providers.dart:182-269`
**Problem**: `buildProviderOverrides()` eagerly creates 7 datasources, 7 repositories, Dio, ApiClient, NetworkInfo, DeviceIntegrityChecker, FcmTokenService — all before `runApp()`. Most are not needed until user navigates to specific features.
**Impact**: ~100-300ms added to cold start on mid-range devices. Unnecessary memory allocation.

#### M2: Root widget rebuilds entire MaterialApp on any provider change
**File**: `lib/app/app.dart:45-135`
**Problem**: `CyberVpnApp.build()` watches 10+ providers (6 listeners + theme + locale + textScale + router). Any state change in ANY of these triggers a full rebuild of `DynamicColorBuilder` → `MaterialApp.router` subtree. No `RepaintBoundary` or widget splitting.
**Impact**: Unnecessary frame drops during theme changes, locale switches, or background provider updates.

#### M3: VPN status stream has no deduplication
**File**: `lib/features/vpn/data/datasources/vpn_engine_datasource.dart:54`
**Problem**: `statusStream` returns `v2ray.onStatusChanged` directly without `.distinct()`. The V2Ray engine may emit duplicate status events (e.g., repeated "CONNECTED" states), triggering unnecessary UI rebuilds in `VpnConnectionNotifier`.
**Impact**: Unnecessary widget rebuilds and state transitions.

#### M4: No Dio retry interceptor for transient failures
**File**: `lib/core/network/api_client.dart`
**Problem**: Only `LogInterceptor` and `AuthInterceptor` are added. No retry logic for transient failures (5xx errors, timeouts, connection resets). The auth interceptor handles 401 refresh but all other errors immediately throw.
**Impact**: Flaky connections on poor networks. User sees errors for recoverable failures.

#### M5: `analysis_options.yaml` missing critical lint rules
**File**: `analysis_options.yaml`
**Problem**: Does not include `unawaited_futures` or `discarded_futures` rules. Multiple fire-and-forget async patterns exist in the codebase (prewarmCache, _migrateOldConfigs, _registerFcmToken, _performAttestation, _scheduleTokenRefresh) that would be caught by these rules.
**Impact**: Uncaught dangling futures may cause race conditions, unhandled errors, and silent failures.

#### M6: `SentryFlutter.init` options.tracesSampleRate = 1.0 in all environments
**File**: `lib/main.dart:49`
**Problem**: `options.tracesSampleRate = 1.0` sends 100% of performance traces to Sentry. In production, this adds overhead to every transaction and may exceed Sentry quota.
**Impact**: Performance overhead + Sentry cost in production.

#### M7: AppLogger ring buffer uses `List.removeAt(0)` — O(n) per eviction
**File**: `lib/core/utils/app_logger.dart:219`
**Problem**: The log ring buffer (max 1000 entries) uses `_ringBuffer.removeAt(0)` which is O(n) for a Dart `List`. With high logging volume (VPN status events, network requests), this degrades to quadratic performance. A `Queue` from `dart:collection` would be O(1).
**Impact**: Subtle performance degradation under high log volume.

### 3.4 LOW — Code Quality Issues (P3)

#### L1: Mixed provider patterns — manual vs code-generated
**Problem**: Most providers use manual `Provider`/`AsyncNotifier` declarations. `riverpod_generator` is listed as a dependency but barely used. Inconsistent patterns reduce maintainability and miss code-gen benefits (auto-dispose, type-safe families).

#### L2: VpnRepositoryImpl runs async migration in constructor
**File**: `lib/features/vpn/data/repositories/vpn_repository_impl.dart:38-41`
**Problem**: `_migrateOldConfigsIfNeeded()` is async but called from synchronous constructor. Runs as fire-and-forget. If `getLastConfig()` or `getSavedConfigs()` is called before migration completes, data may be inconsistent.

#### L3: All 7 Freezed entities use deprecated `abstract class` pattern
**Files**: `user_entity.dart:6`, `server_entity.dart:6`, `plan_entity.dart:8`, `subscription_entity.dart:8`, `vpn_config_entity.dart:8`, `connection_state_entity.dart:14`, `connection_stats_entity.dart:6`
**Problem**: All use `@freezed abstract class X with _$X`. Freezed 3.x recommends `sealed class` or plain `class`. Generates deprecation warnings during `build_runner`.

#### L4: No error boundary widgets around feature modules
**Problem**: `ErrorWidget.builder` is set to `GlobalErrorScreen`, but there are no per-feature `ErrorBoundary` widgets. A crash in diagnostics, referral, or settings crashes the entire app. With 15 feature modules, the blast radius of any uncaught error is maximized.

#### L5: `Sentry.configureScope` deprecated — used in 3 locations
**Files**: `auth_provider.dart:219,231`, `root_detection_dialog.dart:42`
**Problem**: `Sentry.configureScope()` was deprecated in sentry_flutter 8.x. Modern API uses `Sentry.getDefaultScope()` or per-event scoping with `Scope`.

#### L6: Hardcoded English strings in app_lock_overlay.dart and quick_actions_service.dart
**Files**: `app_lock_overlay.dart:134-144,203-232`, `quick_actions_service.dart:47-62`
**Problem**: Strings like 'CyberVPN Locked', 'Authenticate to continue', 'Quick Connect', 'Disconnect' bypass the ARB-based localization system. These are visible to users in all locales.

#### L7: 22 type inference warnings from ApiClient generic methods
**Files**: `auth_remote_ds.dart`, `profile_remote_ds.dart`, `server_remote_ds.dart`, `subscription_remote_ds.dart`
**Problem**: Callers of `_apiClient.get()`, `_apiClient.post()`, etc. don't provide explicit type arguments. With strict-inference enabled in `analysis_options.yaml`, this generates 22 `inference_failure_on_function_invocation` warnings.

#### L8: `BuildContext` used across async gaps in 12+ locations
**Files**: `social_accounts_screen.dart:205-290`, `debug_screen.dart:304-423`, `navigation_flow_test.dart:326-542`
**Problem**: `context` is used after `await` calls. While `mounted` checks exist, analyzer flags them as "guarded by an unrelated `mounted` check" — the check may be from a different State than the context being used.

#### L9: iOS Info.plist missing privacy usage descriptions
**File**: `ios/Runner/Info.plist`
**Problem**: The app uses `local_auth` (biometrics) and WiFi SSID detection (untrusted WiFi handler) but the iOS Info.plist is missing:
- `NSFaceIDUsageDescription` — required for Face ID biometric prompts
- `NSLocationWhenInUseUsageDescription` — required for WiFi SSID reading on iOS
Without these, biometric auth fails silently or shows a generic dialog, and WiFi detection crashes or silently returns nil on iOS.
**Impact**: iOS users cannot use biometric login; untrusted WiFi feature non-functional on iOS.

#### L10: Android Gradle — 8GB JVM heap + ManualPluginRegistrant maintenance burden
**Files**: `android/gradle.properties:1`, `ManualPluginRegistrant.kt`
**Problem**: `org.gradle.jvmargs=-Xmx8G -XX:MaxMetaspaceSize=4G` is excessive for a Flutter project. `ManualPluginRegistrant.kt` replaces auto-generated plugin registration (excluded via `build.gradle.kts:137`), requiring manual updates when adding/removing plugins.

---

## 4. Proposed Solution — Phased Approach

### Phase 1: Fix Splash Screen Hang & Critical Build Errors (P0) — 3-5 days

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 1.1 | **Switch Flutter SDK to stable channel** | Run `flutter channel stable && flutter upgrade`. Verify all plugins compile. Re-run `flutter analyze`. | System-level | C7 |
| 1.2 | **Fix app_lock_overlay.dart compile error** | Replace `options: AuthenticationOptions(...)` with local_auth 3.0 direct params: `biometricOnly: false, stickyAuth: true`. | `app_lock_overlay.dart:54-59` | C5 |
| 1.3 | **Fix biometric_service.dart deprecated API** | Replace `biometricOnly: true, persistAcrossBackgrounding: true` with correct local_auth 3.0 params. | `biometric_service.dart:57-61` | C6 |
| 1.4 | **Fix duplicate sharedPreferencesProvider** | Remove duplicate declaration in `quick_setup_provider.dart`. Import from `server_list_provider.dart` or create a shared core provider. | `quick_setup_provider.dart:142-147`, `providers.dart` | C8 |
| 1.5 | **Fix SecureStorage race condition** | Option A: `await secureStorage.prewarmCache()` before creating ProviderContainer. Option B: Remove fire-and-forget, let auth check warm cache on first read. Remove deprecated `encryptedSharedPreferences: true`. | `providers.dart:190`, `secure_storage.dart:39`, `main.dart` | C1, H7 |
| 1.6 | **Add splash/loading screen route** | Create `/splash` route with branded loading indicator. Router initial location → `/splash`. After auth + onboarding check resolves, redirect to appropriate screen. Add `Future.timeout(3s)` to `_checkCachedAuth()`. | `app_router.dart`, new `splash_screen.dart`, `auth_provider.dart:60` | C1 |
| 1.7 | **Extract root widget lifecycle providers** | Move 6 `ref.watch()` calls from `CyberVpnApp.build()` to a separate `_AppLifecycleManager` ConsumerWidget placed under MaterialApp.router. Wrap in try-catch. | `app.dart:48-65` | C2 |
| 1.8 | **Fix VPN engine initialization** | Move `_engine.initialize()` out of `connect()` — call once in provider setup. Store stream subscription in `VpnEngineDatasource` and cancel in `dispose()`. | `vpn_repository_impl.dart:44-49`, `vpn_engine_datasource.dart:14-30` | C4, H3 |
| 1.9 | **Fix flutter analyze errors** | Fix all 12+ compile errors in test files: update mock AuthRepository to match new signatures (device, rememberMe params), remove `linkOAuth`/`linkTelegram` references, fix clipboard_import_observer_test type error. | `test/features/**` | C7 (analyze) |
| 1.10 | **Add startup profiling** | Add `Stopwatch` + `AppLogger` at each initialization step. Log total startup time. Target: identify operations > 100ms. | `main.dart`, `providers.dart` | — |

### Phase 2: Security & Dependency Fixes (P1) — 2-3 days

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 2.1 | **Remove FCM token from logs** | Replace `AppLogger.info('FCM token: $_token')` with `AppLogger.debug('FCM token retrieved (${_token?.length ?? 0} chars)')`. Same for refresh log. | `push_notification_service.dart:116,121` | H2 |
| 2.2 | **Conditionally add LogInterceptor** | Only add in `kDebugMode`. Remove `requestBody: true, responseBody: true` from production. Redact Authorization header in debug logs. | `api_client.dart:44-48` | H4 |
| 2.3 | **Fix provider overrides type safety** | Investigate Riverpod 3.x proper override pattern. If `Override` type is still not exported, create `List<Override> buildTypedOverrides()` with proper typing. | `providers.dart:182`, `main.dart:35` | H1 |
| 2.4 | **Remove share_plus patch script** | Upgrade share_plus to version that doesn't need patching. Migrate all `Share.share()` → `SharePlus.instance.share()` (7 locations). Remove `scripts/patch_share_plus.py`. | `pubspec.yaml`, `scripts/`, 7 files | H6 |
| 2.5 | **Evaluate flutter_v2ray_plus alternatives** | Research `flutter_v2ray_client` or forking `flutter_v2ray_plus`. Document findings, API diff, migration effort. | Research task | H5 |
| 2.6 | **Fix certificate pinning defaults** | Document required certificate fingerprints. Add `CERT_FINGERPRINTS` to each build flavor. Redact fingerprint logging in `CertificatePinner` behind `kDebugMode`. | `environment_config.dart`, `certificate_pinner.dart`, `build.gradle.kts` | H8, H9 |

### Phase 3: Performance Optimization (P2) — 3-4 days

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 3.1 | **Lazy provider initialization** | Replace eager `buildProviderOverrides()` with lazy `Provider` instances. Only pre-create: SharedPreferences, SecureStorage, Dio, ApiClient, AuthInterceptor. All datasources and repositories created on first access. | `providers.dart` | M1 |
| 3.2 | **Split root widget providers** | Extract lifecycle listeners into a dedicated `LifecycleObserverWidget` under the router. Root widget only watches theme/locale/router. Use `RepaintBoundary` for performance isolation. | `app.dart` | M2 |
| 3.3 | **Add `distinct()` to VPN status stream** | Pipe `v2ray.onStatusChanged` through `.distinct()` to prevent duplicate events from triggering rebuilds. | `vpn_engine_datasource.dart:54` | M3 |
| 3.4 | **Add Dio retry interceptor** | Implement retry with exponential backoff for 5xx, timeouts, connection errors. Max 3 retries. Skip retry for 4xx. | `api_client.dart`, new `retry_interceptor.dart` | M4 |
| 3.5 | **Add `unawaited_futures` lint rule** | Add `unawaited_futures` and `discarded_futures` to `analysis_options.yaml`. Fix all violations (explicitly use `unawaited()` from `dart:async` where fire-and-forget is intentional). | `analysis_options.yaml`, various files | M5 |
| 3.6 | **Configure Sentry sampling per environment** | Set `tracesSampleRate` to 1.0 in dev, 0.2 in staging, 0.05 in prod. Use `EnvironmentConfig.environment` to determine. | `main.dart:49` | M6 |

### Phase 4: Code Quality & Modernization (P3) — 4-5 days

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 4.1 | **Migrate Freezed entities to modern syntax** | Update all 7 entities from `@freezed abstract class X with _$X` to `@freezed sealed class X with _$X`. Re-run `build_runner`. | 7 entity files | L3 |
| 4.2 | **Fix Sentry deprecated APIs** | Replace `Sentry.configureScope()` with modern API in 3 locations. | `auth_provider.dart:219,231`, `root_detection_dialog.dart:42` | L5 |
| 4.3 | **Localize hardcoded strings** | Move hardcoded English strings in `app_lock_overlay.dart` and `quick_actions_service.dart` to ARB localization. | 2 files + ARB files | L6 |
| 4.4 | **Add explicit type arguments to API calls** | Add `<Map<String, dynamic>>` to all `_apiClient.get()/.post()/.delete()` calls. Resolves 22 inference warnings. | 4 datasource files | L7 |
| 4.5 | **Add ErrorBoundary widgets** | Create `FeatureErrorBoundary` widget. Wrap each feature's root screen. Shows graceful fallback + "Report" button. | New widget + 15 feature screens | L4 |
| 4.6 | **Await VPN config migration** | Convert fire-and-forget `_migrateOldConfigsIfNeeded()` to proper async init with completion flag. Factory pattern: `VpnRepositoryImpl.create()` async factory. | `vpn_repository_impl.dart:38-41` | L2 |
| 4.7 | **Fix BuildContext async gaps** | Ensure all `mounted` checks reference the correct State. Capture context before async operations. | 12+ locations | L8 |
| 4.8 | **Add iOS Info.plist privacy descriptions** | Add `NSFaceIDUsageDescription` for biometric auth and `NSLocationWhenInUseUsageDescription` for WiFi SSID detection. | `ios/Runner/Info.plist` | L9 |
| 4.9 | **Reduce Gradle JVM memory** | Lower from 8G → 4G heap, 4G → 2G metaspace. Sufficient for Flutter builds. | `gradle.properties` | L10 |
| 4.10 | **Fix AppLogger ring buffer performance** | Replace `List.removeAt(0)` with `Queue` from `dart:collection` for O(1) eviction. | `app_logger.dart:219` | M7 |
| 4.11 | **Add startup integration test** | Write integration test verifying: cold start → interactive screen in < 5s. Add `flutter test integration_test/` to CI. | `integration_test/` | — |

---

## 5. Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| App launch to interactive screen | **Infinite (hangs)** | < 2s cold start |
| flutter analyze errors | **12+** (lib + test) | **0** |
| flutter analyze warnings | **27** | < 5 |
| Crash-free session rate | Unknown | > 99.5% |
| Test suite | **Cannot execute** | All tests pass |
| Dependency age (oldest direct) | 3+ months | < 2 months |
| Test coverage (core flows) | ~0% (tests broken) | > 60% |
| Provider type safety | `List<Object?>` cast | Typed overrides |
| Security: tokens in logs | **Exposed** | Redacted |
| Production LogInterceptor | **Enabled** | Disabled |

---

## 6. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Flutter stable channel breaks plugins | Build fails | Low | Test all plugins after switch; maintain compatibility matrix |
| flutter_v2ray_plus incompatible with stable Flutter | VPN core broken | Medium | Fork plugin; evaluate `flutter_v2ray_client` |
| Riverpod 3.x `Override` type not exported | Cannot fix type safety | Low | Use extension methods or submit upstream PR |
| SecureStorage deadlock is device-specific | Cannot reproduce | Medium | Timeout + fallback; remove deprecated param; test on 5+ Android OEMs |
| share_plus upgrade breaks share functionality | Share feature broken | Medium | Pin version + add integration test |
| Quick setup provider fix affects authenticated users | Users re-see setup | Low | Check SharedPreferences value persisted correctly |
| Beta→Stable SDK switch changes rendering | UI regressions | Medium | Visual regression testing; golden tests for key screens |

---

## 7. Dependencies & Constraints

- **Flutter SDK**: Must switch to stable; stay at ^3.10.8 or upgrade forward
- **Android minSdk**: 24 (Android 7.0) — required by flutter_v2ray_plus
- **No version downgrades**: All dependency changes must be forward-only
- **Backend API**: Auth endpoints must remain compatible
- **App Store**: Changes must not break Play Store / App Store listings
- **local_auth**: Must support both biometric + PIN/passcode fallback

---

## 8. Out of Scope

- iOS-specific VPN NetworkExtension implementation
- Backend API changes
- Landing page / marketing site
- New feature development (feature freeze during stabilization)
- Admin dashboard changes
- Riverpod 4.x migration (defer until stable release)

---

## 9. Appendix A: File Inventory (Key Files)

| File | Role | Issues |
|------|------|--------|
| `lib/main.dart` | App entry point, deferred services | C1, M1, M6 |
| `lib/app/app.dart` | Root ConsumerWidget | C2, M2 |
| `lib/app/router/app_router.dart` | GoRouter + redirect guards | C1, C8 |
| `lib/core/di/providers.dart` | Eager DI setup, 16 overrides | H1, M1, C1 |
| `lib/core/storage/secure_storage.dart` | SecureStorage with cache | C1, H7 |
| `lib/core/network/api_client.dart` | Dio HTTP client | H4, M4 |
| `lib/core/network/auth_interceptor.dart` | JWT refresh with queue | — (well-implemented) |
| `lib/core/services/push_notification_service.dart` | FCM setup | H2 |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Auth AsyncNotifier | C1, L5 |
| `lib/features/auth/domain/usecases/biometric_service.dart` | Biometric auth | C6 |
| `lib/features/auth/presentation/widgets/app_lock_overlay.dart` | App lock UI | C5, L6 |
| `lib/features/vpn/presentation/providers/vpn_connection_provider.dart` | VPN state (851 lines) | C3 |
| `lib/features/vpn/data/datasources/vpn_engine_datasource.dart` | V2Ray engine wrapper | C4, H3, M3 |
| `lib/features/vpn/data/repositories/vpn_repository_impl.dart` | VPN repository | C4, L2 |
| `lib/features/quick_setup/presentation/providers/quick_setup_provider.dart` | Quick setup state | C8 |
| `pubspec.yaml` | Dependencies | H5, H6 |
| `analysis_options.yaml` | Lint config | M5 |
| `android/app/build.gradle.kts` | Android build | — |
| `ios/Runner/Info.plist` | iOS config | L9 |
| `android/gradle.properties` | Gradle JVM config | L10 |

---

## 10. Appendix B: Dependency Audit

**`flutter pub outdated` result**: All direct dependencies up-to-date (2026-02-06).

| Package | Constraint | Status | Notes |
|---------|-----------|--------|-------|
| flutter_riverpod | ^3.2.1 | OK | Monitor for 4.x |
| go_router | ^17.0.0 | OK | |
| dio | ^5.9.0 | OK | |
| flutter_v2ray_plus | ^1.0.11 | **RISK** | Last update Nov 2025, low maintenance |
| local_auth | ^3.0.0 | **API MISMATCH** | biometric_service uses 2.x API, app_lock uses removed class |
| purchases_flutter | ^9.10.8 | OK | |
| firebase_core | ^4.4.0 | OK | |
| firebase_messaging | ^16.1.1 | OK | |
| firebase_analytics | ^12.1.1 | OK | |
| sentry_flutter | ^9.0.0 | **DEPRECATED API** | `configureScope` deprecated |
| flutter_secure_storage | ^10.0.0 | **DEPRECATED PARAM** | `encryptedSharedPreferences` |
| shared_preferences | ^2.5.3 | OK | |
| freezed | ^3.2.5 | OK | Entities use deprecated `abstract class` |
| freezed_annotation | ^3.0.0 | OK | |
| share_plus | ^12.0.1 | **RISK** | Needs Python patch; deprecated `Share.share()` API |
| in_app_update | ^4.2.4 | OK | Platform guards confirmed in AndroidUpdateService |
| flutter_lints | ^6.0.0 | OK | Missing `unawaited_futures` rule |

**Transitive upgradable**: `objective_c` 9.2.5 → 9.3.0

---

## 11. Appendix C: flutter analyze Error Details

### Production Code Errors (lib/)
```
error • The named parameter 'options' isn't defined
       lib/features/auth/presentation/widgets/app_lock_overlay.dart:56:9
error • The name 'AuthenticationOptions' isn't a class
       lib/features/auth/presentation/widgets/app_lock_overlay.dart:56:24
```

### Test Code Errors (test/)
```
error • 'MockAuthRepository.login' signature mismatch (missing device, rememberMe)
       test/features/auth/presentation/providers/auth_provider_test.dart:51
error • 'MockAuthRepository.register' signature mismatch (missing device)
       test/features/auth/presentation/providers/auth_provider_test.dart:63
error • 'MockAuthRepository.logout' signature mismatch (missing refreshToken, deviceId)
       test/features/auth/presentation/providers/auth_provider_test.dart:77
error • 'MockAuthRepository.refreshToken' signature mismatch (missing deviceId)
       test/features/auth/presentation/providers/auth_provider_test.dart:83
error • Too many positional arguments (3 lines)
       test/features/auth/presentation/providers/auth_provider_test.dart:371,393,407
error • argument_type_not_assignable (clipboard_import_observer_test)
       test/features/config_import/presentation/widgets/clipboard_import_observer_test.dart:19
error • argument_type_not_assignable (providers_test)
       test/core/di/providers_test.dart:35
error • undefined_method 'linkOAuth'
       test/features/profile/data/datasources/profile_remote_ds_test.dart:220
```

---

## 12. Appendix D: Project Statistics

| Metric | Value |
|--------|-------|
| Total Dart files in lib/ | 332 |
| Total Dart files in test/ | 152 |
| Total Dart files in integration_test/ | 4 |
| Lines of code (total) | ~87,600 |
| Feature modules | 15 |
| Domain entities (Freezed) | 7 |
| Repository implementations | 7 |
| Data sources | 7 |
| Provider overrides in DI | 16 |
| Supported locales | 33 |
| Android product flavors | 3 (dev, staging, prod) |
| flutter analyze errors | 12+ |
| flutter analyze warnings | 27 |
| flutter analyze infos | 60+ |

---

## 13. Appendix E: Strengths (What to Preserve)

1. **Well-structured DI pattern**: Provider overrides allow clean testing (despite the type safety issue)
2. **Proper security storage classification**: Consistent `SecureStorageWrapper` for tokens, `LocalStorageWrapper` for preferences
3. **Token refresh queue**: `AuthInterceptor` properly queues concurrent 401 requests — prevents multiple simultaneous refresh calls
4. **Deferred Firebase init**: Post-frame callback pattern correctly avoids blocking cold start
5. **VPN sealed class hierarchy**: Exhaustive pattern matching for all connection states
6. **Proper error reporting**: Both `FlutterError.onError` and `PlatformDispatcher.onError` configured with Sentry
7. **SecureStorage cache layer**: In-memory cache with proper invalidation reduces I/O from ~200ms to near-zero
8. **Certificate pinning infrastructure**: `CertificatePinner` class exists with configurable fingerprints (but currently disabled by default — see H8)
9. **Platform-aware update service**: Proper `Platform.isAndroid` guards in `AndroidUpdateService`
10. **App lock service**: Well-designed with biometric + PIN fallback, failed attempt tracking, and enrollment change detection
