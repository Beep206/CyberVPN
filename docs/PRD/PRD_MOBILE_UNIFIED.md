# PRD: CyberVPN Mobile App — Unified Modernization Plan

**Version**: 1.0
**Date**: 2026-02-06
**Author**: Engineering Team
**Status**: Draft
**Sources**: PRD_MOBILE_MODERNIZATION v2.1, prd-mobile-i18n-completion v1.0, prd-mobile-improvements v1.0
**Scope**: Stability + Security + Architecture + Internationalization + Performance + Quality

---

## 1. Executive Summary

CyberVPN Mobile (Flutter) is a full-featured VPN client with **332 Dart files** (~87,600 LOC), Clean Architecture, Riverpod 3.x state management, 15 feature modules, and 27 supported locales. The app is currently **non-functional in production**: it hangs on the splash screen during launch, the test suite cannot compile, and nearly all localization is English-only despite claiming 27-language support.

This document unifies three separate engineering analyses into a single actionable plan:

1. **Stability & Security** (PRD_MOBILE_MODERNIZATION v2.1): 35 identified issues (8 critical, 9 high, 7 medium, 11 low) causing splash screen hang, compile errors, security vulnerabilities, and degraded performance. 37 remediation tasks across 4 phases.

2. **Internationalization** (prd-mobile-i18n-completion v1.0): Only 4 out of ~305 Dart files use `AppLocalizations`. 574+ hardcoded English strings across ~39 files. 4 stub locales at 82% incomplete. 20 locales with English placeholder text. CLDR plural violations in ru, pl, uk, cs.

3. **Architecture Modernization** (prd-mobile-improvements v1.0): 13 architecture recommendations covering Result<T> type adoption, Riverpod code generation, offline-first data layer, CI/CD, structured errors, and more. Plus performance, security hardening, and UX improvements.

**Key numbers:**
- **35+ issues** across stability, security, and code quality
- **574+ hardcoded strings** requiring localization across ~39 files
- **13 architecture recommendations** for long-term maintainability
- **0 working tests** (test suite does not compile)
- **23/27 locales** are effectively untranslated
- **2 compile errors** in production code, **10+ in test code**
- **27 warnings** and **60+ info-level issues** from `flutter analyze`

The unified plan is organized into **6 sequential phases** with clear dependencies, deduplication of overlapping concerns, and constraint compliance (no library version downgrades, no new library additions).

---

## 2. Current State Analysis

### 2.1 Tech Stack

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Framework | Flutter | **3.41.0-0.2.pre (BETA)** | RISK -- should be stable |
| Language | Dart | **3.11.0-296.4.beta** | RISK -- beta channel |
| State Management | flutter_riverpod | ^3.2.1 | OK |
| Navigation | go_router | ^17.0.0 | OK |
| HTTP | Dio | ^5.9.0 | OK |
| VPN Engine | flutter_v2ray_plus | ^1.0.11 | RISK -- stale (Nov 2025) |
| Secure Storage | flutter_secure_storage | ^10.0.0 | DEPRECATED param |
| Local Storage | shared_preferences | ^2.5.3 | OK |
| Biometrics | local_auth | ^3.0.0 | API MISMATCH |
| IAP | purchases_flutter (RevenueCat) | ^9.10.8 | OK |
| Firebase | core / messaging / analytics | ^4.4.0 / ^16.1.1 / ^12.1.1 | OK |
| Monitoring | sentry_flutter | ^9.0.0 | DEPRECATED API |
| Sharing | share_plus | ^12.0.1 | RISK -- needs patch |
| Updates | in_app_update | ^4.2.4 | OK (guarded) |
| Code Gen | freezed / json_serializable | ^3.2.5 / ^6.12.0 | DEPRECATED pattern |
| Build | Android Gradle (Kotlin DSL) | Java 17, minSdk 24 | OK |

### 2.2 Architecture Overview

**Pattern**: Clean Architecture (domain / data / presentation) per feature

**Features** (15 modules): auth, vpn, servers, subscription, settings, profile, referral, diagnostics, onboarding, config_import, notifications, quick_actions, quick_setup, widgets, navigation, review

**DI**: Riverpod Provider overrides via `buildProviderOverrides()` returning `List<Object?>` with unsafe `.cast()`

**Localization**: ARB-based, 33 locales, RTL support (Arabic, Hebrew, Farsi)

**Theming**: Material You / DynamicColorBuilder with cyberpunk fallback palette

#### Strengths to Preserve

| Area | Details | Source |
|------|---------|--------|
| **Architecture** | Clean Architecture with Feature-Sliced Design, proper layer separation | DOC1 + DOC3 |
| **DI Pattern** | Provider overrides allow clean testing (despite the type safety issue) | DOC1 |
| **Type Safety** | Strict analyzer rules (strict-casts, strict-raw-types, strict-inference), freezed entities, sealed classes for state | DOC3 |
| **Security Infrastructure** | Certificate pinning, SecureStorage for credentials, jailbreak detection, biometric enrollment change detection, screen protection | DOC1 + DOC3 |
| **Token Refresh Queue** | `AuthInterceptor` properly queues concurrent 401 requests -- prevents multiple simultaneous refresh calls | DOC1 |
| **Error Handling** | Layered exceptions -> failures mapping, NetworkErrorHandler mixin with retry + backoff, rate-limit parsing | DOC3 |
| **VPN Sealed States** | Exhaustive pattern matching for all connection states (`VpnConnectionState` sealed hierarchy) | DOC1 + DOC3 |
| **Deferred Firebase Init** | Post-frame callback pattern correctly avoids blocking cold start | DOC1 + DOC3 |
| **Observability** | Sentry integration, structured logging (AppLogger), Firebase Analytics abstraction, performance profiling | DOC3 |
| **Testing Infrastructure** | 95+ test files covering unit, widget, integration, and E2E layers | DOC3 |
| **SecureStorage Cache** | In-memory cache with proper invalidation reduces I/O from ~200ms to near-zero | DOC1 |
| **Platform-Aware Updates** | Proper `Platform.isAndroid` guards in `AndroidUpdateService` | DOC1 |
| **App Lock Service** | Well-designed with biometric + PIN fallback, failed attempt tracking, and enrollment change detection | DOC1 |

### 2.3 App Startup Flow (Current -- Annotated with Issues)

```
main()
  |- WidgetsFlutterBinding.ensureInitialized()
  |- EnvironmentConfig.init()               // loads .env via flutter_dotenv
  |- await SharedPreferences.getInstance()  // BLOCKING await (~10-50ms)
  |- ProviderContainer(overrides: buildProviderOverrides(prefs).cast())
  |   |- SecureStorageWrapper()
  |   |   '- prewarmCache()                 // ! FIRE-AND-FORGET -- 3 SecureStorage reads
  |   |      '- accessToken, refreshToken, cachedUser (parallel Future.wait)
  |   |- NetworkInfo()
  |   |- DeviceIntegrityChecker(prefs)
  |   |- Dio + ApiClient(dio, baseUrl)
  |   |   '- LogInterceptor(requestBody:true, responseBody:true) // ! ALWAYS ON -- leaks in prod
  |   |- AuthInterceptor(secureStorage, dio)
  |   |- FcmTokenService(apiClient)
  |   |- 7 DataSources (eager)              // ! M1: unnecessary eager init
  |   |- 7 Repositories (eager)             // ! M1: unnecessary eager init
  |   |   '- VpnRepositoryImpl()
  |   |       '- _migrateOldConfigsIfNeeded() // ! L2: FIRE-AND-FORGET async in constructor
  |   '- 16 provider overrides
  |       '- sharedPreferencesProvider override (from server_list_provider.dart ONLY)
  |           '- ! C8: quick_setup_provider.dart declares its OWN sharedPreferencesProvider -- NEVER overridden
  |
  |- addPostFrameCallback -> _initializeDeferredServices()
  |   |- Firebase.initializeApp()           // try-catch wrapped
  |   |- PushNotificationService.initialize()
  |   |   '- AppLogger.info('FCM token: $_token')  // ! H2: token logged in plaintext
  |   '- QuickActionsService.initialize()
  |
  |- SentryFlutter.init() OR direct _runApp()
  '- runApp(UncontrolledProviderScope -> CyberVpnApp)
       |
       |- CyberVpnApp.build() watches 6 providers:  // ! C2: any hang blocks entire tree
       |   |- quickActionsListenerProvider
       |   |- widgetStateListenerProvider
       |   |- widgetToggleHandlerProvider
       |   |- quickSettingsChannelProvider
       |   |- untrustedWifiHandlerProvider
       |   '- fcmTopicSyncProvider
       |
       |- DynamicColorBuilder -> MaterialApp.router
       |   '- builder: wraps child with Directionality + MediaQuery (text scale)
       |
       '- GoRouter redirect() watches:
            |- isAuthenticatedProvider -> authProvider.build()
            |   '- _checkCachedAuth()
            |       |- _repo.isAuthenticated() -> secureStorage.read('access_token')
            |       |   '- ! C1: RACES with prewarmCache() -- EncryptedSharedPreferences deadlock
            |       '- _repo.getCurrentUser() -> secureStorage.read('cached_user')
            |
            |- shouldShowOnboardingProvider (FutureProvider -> SharedPreferences)
            |
            |- shouldShowQuickSetupProvider -> quickSetupProvider.build()
            |   '- ref.watch(sharedPreferencesProvider) -- ! C8: THROWS UnimplementedError
            |       (this is quick_setup's LOCAL provider, NOT the overridden one)
            |
            '- quickActionsHandlerProvider (kept alive)
```

### 2.4 flutter analyze Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| **error** (lib/) | 2 | `app_lock_overlay.dart:56` -- `AuthenticationOptions` doesn't exist in local_auth 3.0 |
| **error** (test/) | 10+ | Mock overrides don't match updated AuthRepository signatures; `linkOAuth` removed |
| **warning** | 27 | 22 x `inference_failure_on_function_invocation`, 3 x `unused_local_variable`, 1 x `unused_import` |
| **info** | 60+ | deprecated APIs (`Share.share`, `Radio.groupValue`, `encryptedSharedPreferences`), missing `const`, `use_build_context_synchronously` |

### 2.5 Internationalization State

#### Locale Coverage Matrix

**Tier 1 -- Near-Complete (Real Translations)**

| Locale | Keys | Missing | Untranslated | Plural Quality |
|--------|------|---------|-------------|---------------|
| ru (Russian) | 272/275 | 3 | 2 | `=1{}` bug |
| ar (Arabic) | 258/275 | 17 | 0 | Excellent |
| fa (Farsi) | 258/275 | 17 | 0 | Good |
| he (Hebrew) | 258/275 | 17 | ~5 | Good |

**Tier 2 -- Structure Present, English Placeholders**

| Locale | Keys | Missing | Untranslated (English) |
|--------|------|---------|----------------------|
| de (German) | 261/275 | 14 | ~253 |
| es (Spanish) | 261/275 | 14 | ~253 |
| fr (French) | 261/275 | 14 | ~253 |
| pt (Portuguese) | 261/275 | 14 | ~260 |
| it (Italian) | 261/275 | 14 | ~260 |
| ja (Japanese) | 261/275 | 14 | ~253 |
| ko (Korean) | 261/275 | 14 | ~253 |
| zh (Chinese Simplified) | 261/275 | 14 | ~253 |
| tr (Turkish) | 261/275 | 14 | ~253 |
| nl (Dutch) | 261/275 | 14 | ~260 |
| pl (Polish) | 261/275 | 14 | ~260 |
| uk (Ukrainian) | 261/275 | 14 | ~260 |
| hi (Hindi) | 261/275 | 14 | ~260 |
| th (Thai) | 261/275 | 14 | ~260 |
| vi (Vietnamese) | 261/275 | 14 | ~260 |
| id (Indonesian) | 261/275 | 14 | ~260 |
| ms (Malay) | 261/275 | 14 | ~260 |
| ro (Romanian) | 261/275 | 14 | ~260 |

**Tier 3 -- Severely Incomplete (Stubs)**

| Locale | Keys | Missing | Notes |
|--------|------|---------|-------|
| cs (Czech) | 50/275 | 225 | Only base keys, all English |
| da (Danish) | 50/275 | 225 | Only base keys, all English |
| sv (Swedish) | 50/275 | 225 | Only base keys, all English |
| zh_Hant (Trad. Chinese) | 50/275 | 225 | Only base keys, all English |

#### Missing Keys (14 keys absent from most locales)

These keys exist in `app_en.arb` but are missing from non-English ARB files:

```
errorTelegramAuthCancelled
errorTelegramAuthFailed
errorTelegramAuthExpired
errorTelegramNotInstalled
errorTelegramAuthInvalid
errorBiometricUnavailable
errorBiometricNotEnrolled
errorBiometricFailed
errorBiometricLocked
errorSessionExpired
errorAccountDisabled
errorRateLimitedWithCountdown    (plural)
errorOfflineLoginRequired
errorOfflineSessionExpired
```

**3 additional keys** missing from ar, fa, he, ru:
```
rootDetectionDialogTitle
rootDetectionDialogDescription
rootDetectionDialogDismiss
```

#### Hardcoded Strings by Feature Area

| Feature Area | Hardcoded Strings | Files Affected |
|-------------|-------------------|----------------|
| `features/settings/` | ~60 | 8+ screens |
| `features/profile/` | ~49 | 6+ screens |
| `features/config_import/` | ~39 | 4+ screens |
| `features/auth/` | ~23 | 5+ screens |
| `features/subscription/` | ~19 | 3+ screens |
| `features/onboarding/` | ~8 | 2 screens |
| `features/servers/` | ~7 | 2 screens |
| `features/notifications/` | ~5 | 2 screens |
| `features/referral/` | ~4 | 1 screen |
| `features/diagnostics/` | ~4 | 2 screens |
| `shared/widgets/` | ~4 | 3 widgets |
| Providers/Services | ~20 | 5+ files |
| **Total** | **~574+** | **~39 files** |

**Worst offending files:**
- `features/auth/presentation/screens/register_screen.dart` -- 12+ hardcoded strings
- `features/auth/presentation/screens/biometric_settings_screen.dart` -- 10+ hardcoded strings
- `features/config_import/presentation/screens/import_list_screen.dart` -- 7+ hardcoded strings
- `features/subscription/presentation/screens/purchase_screen.dart` -- 8+ hardcoded strings
- `features/subscription/presentation/screens/plans_screen.dart` -- 6+ hardcoded strings

#### Plural Form Issues

| Locale | Issue | Severity |
|--------|-------|----------|
| **ru** | Uses `=1{...}` instead of `one{...}` in all 8 plural messages. Causes incorrect forms for 21, 31, 101, etc. | P1 |
| **pl** | All 7 plural messages are English copies. Needs `one/few/many/other` forms. | P0 |
| **uk** | All 7 plural messages are English copies. Needs `one/few/many/other` forms. | P0 |
| **cs** | `daysRemaining` is English copy. Needs `one/few/many/other` forms. Only 1 plural message exists (file is a stub). | P0 |
| **de, es** | Correctly use `one/other` for their small set of translated plurals. Remaining plurals are English copies. | P1 |
| **ar** | Excellent -- uses all 6 CLDR categories (`zero/one/two/few/many/other`). | OK |
| **fa** | Correct -- uses `one/other` (Farsi plural rules). | OK |

### 2.6 Architecture Health

| Risk | Severity | Probability | Impact |
|------|----------|-------------|--------|
| DI Boilerplate Explosion | Medium | High | Maintenance burden grows with every new feature |
| Missing Either/Result in Repositories | High | High | Exceptions leak across layer boundaries |
| No Offline-First Data Layer | High | Medium | VPN app must work reliably with poor connectivity |
| Test Coverage Gaps in Presentation Layer | Medium | High | UI regressions undetected |
| No CI/CD Pipeline for Mobile | Critical | High | Manual builds, no automated quality gates |

---

## 3. Identified Issues (UNIFIED -- Deduplicated)

### 3.1 CRITICAL (P0) -- 8 Items

#### C1: SecureStorage race condition blocks auth resolution
**File**: `lib/core/di/providers.dart:190`, `lib/core/storage/secure_storage.dart:103-113`
**Problem**: `prewarmCache()` is fire-and-forget in `buildProviderOverrides()`. Meanwhile `authProvider.build()` -> `_checkCachedAuth()` also reads the same SecureStorage keys. On Android with `encryptedSharedPreferences: true` (deprecated), EncryptedSharedPreferences can deadlock when accessed concurrently -- the Android Keystore may serialize operations, causing the second access to wait indefinitely for the first to release the lock.
**Evidence**: `secure_storage.dart:39` uses deprecated `AndroidOptions(encryptedSharedPreferences: true)`. The deprecation notice states: "The Jetpack Security library is deprecated by Google."
**Impact**: Auth check never resolves -> GoRouter redirect hangs -> native splash screen never dismissed.

#### C2: Root widget watches 6 providers -- any hang blocks entire tree
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
1. `VpnRepositoryImpl.connect()` calls `_engine.initialize()` every time -- creates native resources repeatedly
2. Inside `initialize()`, `v2ray.onStatusChanged.listen(...)` is called but the `StreamSubscription` is never stored or cancelled. Each `connect()` creates a new orphan subscription.
**Impact**: Growing memory leak with each reconnect. Native resource exhaustion.

#### C5: app_lock_overlay.dart -- COMPILE ERROR (local_auth 3.0 API mismatch)
**File**: `lib/features/auth/presentation/widgets/app_lock_overlay.dart:54-59`
**Problem**: Uses `AuthenticationOptions` class and `options:` named parameter which **do not exist** in `local_auth 3.0.0`. Confirmed by flutter analyze:
```
error - The named parameter 'options' isn't defined - app_lock_overlay.dart:56:9
error - The name 'AuthenticationOptions' isn't a class - app_lock_overlay.dart:56:24
```
**Impact**: If app lock is enabled and biometric fails (triggering PIN fallback), calling `_attemptPinUnlock()` crashes. In release mode, R8 tree-shaking may exclude this dead code -- but if the code path is reached, it's a hard crash.

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

#### C8: Duplicate `sharedPreferencesProvider` -- quick_setup NEVER overridden
**File**: `lib/features/quick_setup/presentation/providers/quick_setup_provider.dart:142-147`
**Problem**: `quick_setup_provider.dart` declares its own `sharedPreferencesProvider` (line 142). The DI override in `providers.dart:250` only overrides the one imported from `server_list_provider.dart`. These are **two different Dart symbols** with the same name from different libraries. `QuickSetupNotifier.build()` (line 57) calls `ref.watch(sharedPreferencesProvider)` which resolves to the LOCAL (unoverridden) one, throwing `UnimplementedError`.
**Chain reaction**:
1. `quickSetupProvider` goes to `AsyncError` state
2. `shouldShowQuickSetupProvider` returns `true` (default when value is null)
3. GoRouter redirects authenticated users to `/quick-setup`
4. `QuickSetupScreen` tries to use `quickSetupProvider` -> same crash
5. Infinite error -> redirect loop for authenticated users
**Impact**: Authenticated users are trapped in a crashing quick-setup redirect loop.

### 3.2 HIGH (P1) -- 10 Items

#### H1: `buildProviderOverrides()` returns `List<Object?>` with unsafe `.cast()`
**File**: `lib/core/di/providers.dart:182`, `lib/main.dart:35`
**Problem**: Returns `List<Object?>`, caller does `.cast()` without type argument. This bypasses Riverpod's type-safe override system. If any entry is not a valid `Override`, runtime `CastError` crashes the app immediately on startup.
**Impact**: Fragile startup -- any typo or mismatched provider crashes the entire app.

#### H2: FCM token logged in plaintext
**File**: `lib/core/services/push_notification_service.dart:116,121`
**Problem**: Full FCM device token is logged via `AppLogger.info('FCM token: $_token')` and `AppLogger.info('FCM token refreshed: $newToken')`. If logs are collected by Sentry, crash reporting, or written to disk/logcat, the token is exposed.
**Impact**: Attackers with log access can send unsolicited push notifications to user devices.

#### H3: VPN engine stream subscription never cancelled
**File**: `lib/features/vpn/data/datasources/vpn_engine_datasource.dart:27-29`
**Problem**: `v2ray.onStatusChanged.listen((status) { _lastStatus = status; })` -- the `StreamSubscription` returned by `.listen()` is discarded. Each call to `initialize()` (called on every `connect()`) adds a new orphan listener. The `dispose()` method only nulls `_v2ray` and `_lastStatus`, not the subscription.
**Impact**: Memory leak growing linearly with reconnections. Old subscriptions process stale events.

#### H4: `LogInterceptor` always enabled -- leaks tokens in production
**File**: `lib/core/network/api_client.dart:44-48`
**Problem**: `LogInterceptor(requestBody: true, responseBody: true)` is added unconditionally. In production:
- Logs JWT access tokens from Authorization headers
- Logs refresh tokens from refresh request bodies
- Logs user credentials during login/register
- Performance overhead: serializing full request/response bodies to string
**Impact**: Security: credentials visible in logcat. Performance: unnecessary string operations on every HTTP request.

#### H5: flutter_v2ray_plus at v1.0.11 -- stale dependency (Nov 2025)
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
**Problem**: `AndroidOptions(encryptedSharedPreferences: true)` -- deprecated. The deprecation notice states: "The Jetpack Security library is deprecated by Google. Your data will be automatically migrated to custom ciphers on first access. Remove this parameter."
**Impact**: Will stop compiling in flutter_secure_storage v11. The deprecated migration path may cause slow first-access on app update (contributing to C1 splash screen hang).

#### H8: Certificate pinning effectively disabled by default
**Files**: `lib/core/config/environment_config.dart:64-67`, `lib/core/security/certificate_pinner.dart:57-69`
**Problem**: `CERT_FINGERPRINTS` dart-define defaults to empty string, meaning certificate pinning is disabled by default. In `kDebugMode` validation is bypassed entirely. The build.gradle.kts product flavors do not set `CERT_FINGERPRINTS`, and there is no documentation of required fingerprints. Production builds are only pinned if explicitly passing `--dart-define=CERT_FINGERPRINTS=...` during build.
**Impact**: MITM attacks possible in production if fingerprints not configured during build. False sense of security from the `CertificatePinner` class existing.

#### H9: CertificatePinner logs fingerprints in debug output
**File**: `lib/core/security/certificate_pinner.dart:73-82`
**Problem**: Certificate fingerprints, subjects, and issuers are logged at debug level. On rooted devices with debug log capture, this provides attackers with the exact certificate fingerprints the app expects, making it easier to prepare MITM attacks.
**Impact**: Reduces effectiveness of certificate pinning when combined with rooted device access.

#### H10: Result<T> type pattern missing -- exceptions leak across layer boundaries
**Source**: DOC3 3.1 (reclassified from CRITICAL to HIGH -- foundational but not blocking launch)
**Problem**: Repositories throw exceptions (`NetworkFailure`, `AuthFailure`) which are caught in presentation layer catch blocks. This violates Clean Architecture principles -- exceptions are not part of the domain contract and make error handling fragile.
**Current pattern** (anti-pattern):
```dart
// auth_repository_impl.dart
@override
Future<(UserEntity, String)> login({...}) async {
  if (!await _networkInfo.isConnected) {
    throw const NetworkFailure(message: 'No internet connection');
  }
  // ... throws on failure
}

// auth_provider.dart
try {
  final (user, _) = await _repo.login(...);
} catch (e) {
  state = AsyncValue.data(AuthError(e.toString())); // loses type info
}
```
**Scope**: All 7 repository interfaces + implementations.
**Impact**: Exceptions leak across layer boundaries, error handling is fragile, type information is lost.

### 3.3 MEDIUM (P2) -- 12 Items

#### M1: Eager initialization of all 14 DI objects at startup (MERGED: DOC1 M1 + DOC3 4.1)
**File**: `lib/core/di/providers.dart:182-269`
**Problem**: `buildProviderOverrides()` eagerly creates 7 datasources, 7 repositories, Dio, ApiClient, NetworkInfo, DeviceIntegrityChecker, FcmTokenService -- all before `runApp()`. Most are not needed until user navigates to specific features.
**Note**: DOC3 4.1 (Lazy Provider Initialization) identified the same issue and recommended using Riverpod's lazy initialization (default behavior with `@riverpod`). Only `authRepository`, `vpnRepository`, and `secureStorage` need eager initialization.
**Impact**: ~100-300ms added to cold start on mid-range devices. Unnecessary memory allocation.

#### M2: Root widget rebuilds entire MaterialApp on any provider change
**File**: `lib/app/app.dart:45-135`
**Problem**: `CyberVpnApp.build()` watches 10+ providers (6 listeners + theme + locale + textScale + router). Any state change in ANY of these triggers a full rebuild of `DynamicColorBuilder` -> `MaterialApp.router` subtree. No `RepaintBoundary` or widget splitting.
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

#### M7: AppLogger ring buffer uses `List.removeAt(0)` -- O(n) per eviction
**File**: `lib/core/utils/app_logger.dart:219`
**Problem**: The log ring buffer (max 1000 entries) uses `_ringBuffer.removeAt(0)` which is O(n) for a Dart `List`. With high logging volume (VPN status events, network requests), this degrades to quadratic performance. A `Queue` from `dart:collection` would be O(1).
**Impact**: Subtle performance degradation under high log volume.

#### M8: No offline-first data layer
**Source**: DOC3 3.3
**Problem**: Most repositories check `_networkInfo.isConnected` and throw immediately on no network. A VPN app's users frequently have degraded connectivity. Server list, user profile, subscription status, and settings should all be available offline.
**Current gap**: `ServerRepositoryImpl` and `SubscriptionRepositoryImpl` have a `localDataSource` but no stale-while-revalidate pattern. `AuthRepositoryImpl.getCurrentUser()` returns `null` on no network with no attempt to refresh from cache.
**Impact**: VPN app users on poor connectivity see errors instead of cached data.

#### M9: No CI/CD pipeline (MERGED: DOC3 3.4 + DOC2 Phase 4)
**Source**: DOC3 3.4 + DOC2 Phase 4
**Problem**: No automated build, test, or release pipeline exists. Manual builds are error-prone and slow. Additionally, no CI checks exist for i18n coverage (missing keys, hardcoded strings, untranslated values).
**Impact**: Manual builds, no automated quality gates, i18n regressions go undetected.

#### M10: VPN connect/connectFromCustomServer code duplication
**Source**: DOC3 3.5
**File**: `lib/features/vpn/presentation/providers/vpn_connection_provider.dart:238-373`
**Problem**: `connect()` and `connectFromCustomServer()` share ~80% identical logic (settings resolution, kill switch, persist, auto-reconnect, device registration, review prompt). Violates DRY. Two 65-line methods with nearly identical structure.
**Impact**: Maintenance burden, risk of divergent behavior between the two code paths.

#### M11: WebSocket reconnection without jitter
**Source**: DOC3 3.8
**Problem**: `WebSocketClient._calculateBackoff()` uses pure exponential backoff without jitter. When the server restarts, all clients reconnect at the same exact intervals, causing a thundering herd.
**Current**: `1s, 2s, 4s, 8s, 16s, 30s` (capped)
**Impact**: Thundering herd on server restart overloads the backend.

#### M12: i18n adoption critically low -- 4/305 files
**Source**: DOC2 (entire scope)
**Problem**: Only 4 out of ~305 Dart files use `AppLocalizations`. 574+ hardcoded English strings remain across ~39 files. The app claims 27-language support but delivers English to nearly all users. Non-English users in censored regions (Iran, China, Russia) -- the app's primary target -- cannot use the app in their native language.
**Impact**: App store rejection risk, low ratings in non-English markets, competitive disadvantage.

### 3.4 LOW (P3) -- 16 Items

#### L1: Riverpod code gen unused (MERGED: DOC1 L1 + DOC3 3.2/3.7)
**Problem**: Most providers use manual `Provider`/`AsyncNotifier` declarations. `riverpod_generator` is listed as a dependency but barely used. Inconsistent patterns reduce maintainability and miss code-gen benefits (auto-dispose, type-safe families). DOC3 3.7 additionally notes the mix of legacy `Provider((...) => ...)` and modern `@riverpod` patterns across `BiometricService`, analytics, and utility providers.
**Current state**: 270 lines of manual wiring in `core/di/providers.dart`, providers scattered across feature files with `throw UnimplementedError()` stubs.

#### L2: VpnRepositoryImpl runs async migration in constructor
**File**: `lib/features/vpn/data/repositories/vpn_repository_impl.dart:38-41`
**Problem**: `_migrateOldConfigsIfNeeded()` is async but called from synchronous constructor. Runs as fire-and-forget. If `getLastConfig()` or `getSavedConfigs()` is called before migration completes, data may be inconsistent.

#### L3: All 7 Freezed entities use deprecated `abstract class` pattern
**Files**: `user_entity.dart:6`, `server_entity.dart:6`, `plan_entity.dart:8`, `subscription_entity.dart:8`, `vpn_config_entity.dart:8`, `connection_state_entity.dart:14`, `connection_stats_entity.dart:6`
**Problem**: All use `@freezed abstract class X with _$X`. Freezed 3.x recommends `sealed class` or plain `class`. Generates deprecation warnings during `build_runner`.

#### L4: No error boundary widgets around feature modules
**Problem**: `ErrorWidget.builder` is set to `GlobalErrorScreen`, but there are no per-feature `ErrorBoundary` widgets. A crash in diagnostics, referral, or settings crashes the entire app. With 15 feature modules, the blast radius of any uncaught error is maximized.

#### L5: `Sentry.configureScope` deprecated -- used in 3 locations
**Files**: `auth_provider.dart:219,231`, `root_detection_dialog.dart:42`
**Problem**: `Sentry.configureScope()` was deprecated in sentry_flutter 8.x. Modern API uses `Sentry.getDefaultScope()` or per-event scoping with `Scope`.

#### L6: Hardcoded English strings in app_lock_overlay.dart and quick_actions_service.dart (SUBSUMED by M12)
**Files**: `app_lock_overlay.dart:134-144,203-232`, `quick_actions_service.dart:47-62`
**Problem**: Strings like 'CyberVPN Locked', 'Authenticate to continue', 'Quick Connect', 'Disconnect' bypass the ARB-based localization system. These are visible to users in all locales.
**Note**: This is a subset of the comprehensive i18n issue tracked as M12. Full remediation scope is defined in Phase 4 (Internationalization).

#### L7: 22 type inference warnings from ApiClient generic methods
**Files**: `auth_remote_ds.dart`, `profile_remote_ds.dart`, `server_remote_ds.dart`, `subscription_remote_ds.dart`
**Problem**: Callers of `_apiClient.get()`, `_apiClient.post()`, etc. don't provide explicit type arguments. With strict-inference enabled in `analysis_options.yaml`, this generates 22 `inference_failure_on_function_invocation` warnings.

#### L8: `BuildContext` used across async gaps in 12+ locations
**Files**: `social_accounts_screen.dart:205-290`, `debug_screen.dart:304-423`, `navigation_flow_test.dart:326-542`
**Problem**: `context` is used after `await` calls. While `mounted` checks exist, analyzer flags them as "guarded by an unrelated `mounted` check" -- the check may be from a different State than the context being used.

#### L9: iOS Info.plist missing privacy usage descriptions
**File**: `ios/Runner/Info.plist`
**Problem**: The app uses `local_auth` (biometrics) and WiFi SSID detection (untrusted WiFi handler) but the iOS Info.plist is missing:
- `NSFaceIDUsageDescription` -- required for Face ID biometric prompts
- `NSLocationWhenInUseUsageDescription` -- required for WiFi SSID reading on iOS
Without these, biometric auth fails silently or shows a generic dialog, and WiFi detection crashes or silently returns nil on iOS.
**Impact**: iOS users cannot use biometric login; untrusted WiFi feature non-functional on iOS.

#### L10: Android Gradle -- 8GB JVM heap + ManualPluginRegistrant maintenance burden
**Files**: `android/gradle.properties:1`, `ManualPluginRegistrant.kt`
**Problem**: `org.gradle.jvmargs=-Xmx8G -XX:MaxMetaspaceSize=4G` is excessive for a Flutter project. `ManualPluginRegistrant.kt` replaces auto-generated plugin registration (excluded via `build.gradle.kts:137`), requiring manual updates when adding/removing plugins.

#### L11: Structured error types needed for i18n-ready messages
**Source**: DOC3 3.6
**Problem**: Error messages are raw `e.toString()` strings passed to UI. This exposes implementation details (class names, stack traces) and prevents localization. Without structured error types, i18n of error messages is impossible.
**Impact**: Users see raw English exception text regardless of locale setting.

#### L12: Dart 3 pattern matching used inconsistently
**Source**: DOC3 3.10
**Problem**: The codebase uses sealed classes (good) but inconsistently applies Dart 3 pattern matching. Some places use `is` checks, others use `switch` expressions.
**Examples**:
```dart
// Old style (auth_provider.dart)
if (authState is AuthAuthenticated) {
  return authState.user;
}

// Modern style (vpn_connection_provider.dart)
return switch (this) {
  final VpnConnecting s => s.server,
  final VpnConnected s => s.server,
  _ => null,
};
```

#### L13: Failure uses Equatable instead of sealed classes
**Source**: DOC3 3.11
**Problem**: `Failure` extends `Equatable` which requires maintaining `props` lists. With Dart 3 sealed classes, equality can be derived more naturally (or use freezed for failures).
**Current**:
```dart
abstract class Failure extends Equatable {
  final String message;
  final int? code;
  @override
  List<Object?> get props => [message, code];
}
```

#### L14: Firebase Analytics init race condition
**Source**: DOC3 3.12
**Problem**: Firebase is initialized in `_initializeDeferredServices()` via `addPostFrameCallback`. However, `AnalyticsService` might be called before Firebase initialization completes (e.g., if auth flow completes before first frame callback fires).

#### L15: Missing @immutable annotations on non-Freezed value objects
**Source**: DOC3 3.13
**Problem**: Several manually written classes should be annotated `@immutable` to enforce compile-time immutability checks. Examples:
- `ConnectVpnUseCase` (has `const` constructor but no `@immutable`)
- `VpnDisconnected`, `VpnConnecting`, etc. (manual sealed class hierarchy)
- All `AppException` subclasses

#### L16: CLDR plural violations in ru/pl/uk/cs
**Source**: DOC2
**Problem**: Russian uses `=1{...}` instead of `one{...}` (causes incorrect forms for 21, 31, 101). Polish and Ukrainian have all plural messages as English copies. Czech stub has only 1 plural message as English copy. All need proper `one/few/many/other` CLDR forms.
**Impact**: Incorrect grammar visible to users in 4 languages.

---

## 4. Proposed Solution -- 6-Phase Approach

### Phase 1: Critical Stability (P0) -- 3-5 days

**Objective**: Fix splash screen hang, compile errors, and make the app launchable.
**Dependency**: NOTHING -- this must go first.

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 1.1 | **Switch Flutter SDK to stable channel** | Run `flutter channel stable && flutter upgrade`. Verify all plugins compile. Re-run `flutter analyze`. | System-level | C7 |
| 1.2 | **Fix app_lock_overlay.dart compile error** | Replace `options: AuthenticationOptions(...)` with local_auth 3.0 direct params: `biometricOnly: false, stickyAuth: true`. | `app_lock_overlay.dart:54-59` | C5 |
| 1.3 | **Fix biometric_service.dart deprecated API** | Replace `biometricOnly: true, persistAcrossBackgrounding: true` with correct local_auth 3.0 params. | `biometric_service.dart:57-61` | C6 |
| 1.4 | **Fix duplicate sharedPreferencesProvider** | Remove duplicate declaration in `quick_setup_provider.dart`. Import from `server_list_provider.dart` or create a shared core provider. | `quick_setup_provider.dart:142-147`, `providers.dart` | C8 |
| 1.5 | **Fix SecureStorage race condition** | Option A: `await secureStorage.prewarmCache()` before creating ProviderContainer. Option B: Remove fire-and-forget, let auth check warm cache on first read. Remove deprecated `encryptedSharedPreferences: true`. | `providers.dart:190`, `secure_storage.dart:39`, `main.dart` | C1, H7 |
| 1.6 | **Add splash/loading screen route** | Create `/splash` route with branded loading indicator. Router initial location -> `/splash`. After auth + onboarding check resolves, redirect to appropriate screen. Add `Future.timeout(3s)` to `_checkCachedAuth()`. | `app_router.dart`, new `splash_screen.dart`, `auth_provider.dart:60` | C1 |
| 1.7 | **Extract root widget lifecycle providers** | Move 6 `ref.watch()` calls from `CyberVpnApp.build()` to a separate `_AppLifecycleManager` ConsumerWidget placed under MaterialApp.router. Wrap in try-catch. | `app.dart:48-65` | C2 |
| 1.8 | **Fix VPN engine initialization** | Move `_engine.initialize()` out of `connect()` -- call once in provider setup. Store stream subscription in `VpnEngineDatasource` and cancel in `dispose()`. | `vpn_repository_impl.dart:44-49`, `vpn_engine_datasource.dart:14-30` | C4, H3 |
| 1.9 | **Fix flutter analyze errors** | Fix all 12+ compile errors in test files: update mock AuthRepository to match new signatures (device, rememberMe params), remove `linkOAuth`/`linkTelegram` references, fix clipboard_import_observer_test type error. | `test/features/**` | C7 (analyze) |
| 1.10 | **Add startup profiling** | Add `Stopwatch` + `AppLogger` at each initialization step. Log total startup time. Target: identify operations > 100ms. | `main.dart`, `providers.dart` | -- |

### Phase 2: Security & Core Fixes (P1) -- 3-4 days

**Objective**: Resolve security vulnerabilities and establish foundational patterns for Phase 3.
**Dependency**: Phase 1.

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 2.1 | **Remove FCM token from logs** | Replace `AppLogger.info('FCM token: $_token')` with `AppLogger.debug('FCM token retrieved (${_token?.length ?? 0} chars)')`. Same for refresh log. | `push_notification_service.dart:116,121` | H2 |
| 2.2 | **Conditionally add LogInterceptor** | Only add in `kDebugMode`. Remove `requestBody: true, responseBody: true` from production. Redact Authorization header in debug logs. | `api_client.dart:44-48` | H4 |
| 2.3 | **Fix provider overrides type safety** | Investigate Riverpod 3.x proper override pattern. If `Override` type is still not exported, create `List<Override> buildTypedOverrides()` with proper typing. | `providers.dart:182`, `main.dart:35` | H1 |
| 2.4 | **Research share_plus alternatives** | **RESEARCH ONLY -- NO LIBRARY CHANGES PER USER CONSTRAINT.** Investigate whether upgrading share_plus to a version that doesn't need patching is feasible. Document migration path from `Share.share()` -> `SharePlus.instance.share()` (7 locations). Document findings only; do not remove `scripts/patch_share_plus.py` yet. | `pubspec.yaml`, `scripts/`, 7 files | H6 |
| 2.5 | **Research flutter_v2ray_plus alternatives** | **RESEARCH ONLY -- NO LIBRARY CHANGES PER USER CONSTRAINT.** Research `flutter_v2ray_client` or forking `flutter_v2ray_plus`. Document findings, API diff, migration effort. No code changes. | Research task | H5 |
| 2.6 | **Fix certificate pinning defaults** | Document required certificate fingerprints. Add `CERT_FINGERPRINTS` to each build flavor. Redact fingerprint logging in `CertificatePinner` behind `kDebugMode`. | `environment_config.dart`, `certificate_pinner.dart`, `build.gradle.kts` | H8, H9 |
| 2.7 | **Implement Result<T> type pattern** | Create `sealed class Result<T>` in domain layer. Migrate all 7 repository interfaces + implementations to return `Result<T>` instead of throwing. Update all provider catch blocks to use exhaustive pattern matching. | `lib/core/domain/result.dart` (new), all 7 repository pairs, all providers | H10 |

> **IMPORTANT**: Tasks 2.4 and 2.5 are **RESEARCH ONLY**. Per user constraint, no library version changes or new library additions are permitted at this time. These tasks produce documentation artifacts only.

### Phase 3: Architecture Modernization -- 5-7 days

**Objective**: Modernize DI, establish offline-first patterns, create CI/CD, and prepare infrastructure for i18n.
**Dependency**: Phase 2 (needs Result<T> for clean error handling).

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 3.1 | **Riverpod code generation migration** | Adopt `@riverpod` / `@Riverpod(keepAlive: true)` annotations across all providers. Run `dart run build_runner build` to generate providers. Eliminates `throw UnimplementedError()` stubs, auto-generates dispose/keep-alive logic, type-safe compile-time dependency graph. Reduces `providers.dart` from 270 lines to ~30. (MERGED: DOC1 L1 + DOC3 3.2 + DOC3 3.7) | `core/di/providers.dart`, all feature `presentation/providers/` | L1 |
| 3.2 | **Offline-first data layer with CacheStrategy** | Implement generic `CachePolicy` abstraction with per-repository strategies. | All repository implementations | M8 |

**CacheStrategy enum:**
```dart
enum CacheStrategy {
  cacheFirst,             // Return cache, refresh in background
  networkFirst,           // Try network, fall back to cache
  cacheOnly,              // Never hit network
  networkOnly,            // Never use cache (sensitive data)
  staleWhileRevalidate,   // Return cache immediately, update after
}
```

**Per-repository strategy:**
| Repository | Strategy | TTL |
|-----------|----------|-----|
| ServerRepository | staleWhileRevalidate | 5 min |
| SubscriptionRepository | cacheFirst | 1 hour |
| AuthRepository (user profile) | cacheFirst | 24 hours |
| ReferralRepository | networkFirst | 15 min |
| SettingsRepository | cacheOnly | -- (local) |

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 3.3 | **CI/CD pipeline** | GitHub Actions pipeline (MERGED: DOC3 3.4 + DOC2 Phase 4 CI). Includes: (1) PR Checks: `flutter analyze`, `flutter test`, `dart format --set-exit-if-changed`; (2) Build Matrix: Android (dev, staging, prod flavors) + iOS (Debug, Release); (3) Code Coverage: Enforce minimum 70% with `lcov`; (4) Release: Fastlane for iOS, Gradle for Android, triggered on tag push; (5) Code Signing: GitHub Secrets for keystore (Android) + Match (iOS); **PLUS i18n checks**: (6) Parse `app_en.arb` to get canonical key list, compare each locale ARB; (7) Fail build if any locale has missing keys or >5% untranslated; (8) Grep-based check for `Text('...')` patterns in lib/ (excluding generated/). | `.github/workflows/mobile-ci.yml`, `.github/workflows/mobile-release.yml`, `cybervpn_mobile/fastlane/Fastfile`, `scripts/check_i18n_coverage.py` | M9 |
| 3.4 | **VPN connection code deduplication** | Extract private `_executeConnection(VpnConfigEntity config, ServerEntity server)` method, call from both `connect()` and `connectFromCustomServer()`. Custom server conversion happens before calling the shared method. | `vpn_connection_provider.dart:238-373` | M10 |
| 3.5 | **Structured error types (AppError)** | Create `AppError` sealed class with `localizedMessage(AppLocalizations l10n)` method enabling i18n-ready error messages. This is the bridge between Phase 3 (architecture) and Phase 4 (i18n). | `lib/core/errors/app_error.dart` (new), providers | L11 |

**AppError sealed class example:**
```dart
sealed class AppError {
  String localizedMessage(AppLocalizations l10n);
}
class NetworkError extends AppError {
  @override
  String localizedMessage(l10n) => l10n.errorNoInternet;
}
class AuthError extends AppError {
  final AuthErrorCode code;
  @override
  String localizedMessage(l10n) => switch (code) {
    AuthErrorCode.invalidCredentials => l10n.errorInvalidCredentials,
    AuthErrorCode.emailNotVerified => l10n.errorEmailNotVerified,
    // ...
  };
}
```

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 3.6 | **WebSocket jitter** | Add randomized jitter to `WebSocketClient._calculateBackoff()` to prevent thundering herd on server restart. | `lib/core/network/websocket_client.dart` | M11 |

**WebSocket jitter code:**
```dart
Duration _calculateBackoff() {
  final baseSeconds = _initialBackoff.inSeconds *
      math.pow(_backoffMultiplier, _reconnectAttempt).toInt();
  final capped = math.min(baseSeconds, _maxBackoff.inSeconds);
  final jitter = Random().nextInt(capped ~/ 2 + 1); // 0..50% of delay
  return Duration(seconds: capped + jitter);
}
```

### Phase 4: Internationalization -- 4-6 weeks

**Objective**: Bring the app to production-grade multilingual quality across all 27 locales.
**Dependency**: Phase 3 (structured errors with `localizedMessage()` must exist).

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 4.1 | **Fix plural forms -- ru, pl, uk, cs** | **ru**: Replace `=1{...}` with `one{...}` in all 8 plural messages. Ensure `few` and `many` forms handle 2-4, 5-20, 21+ patterns. **pl**: Translate all 7 plural messages with proper `one/few/many/other` forms. **uk**: Translate all 7 plural messages with proper `one/few/many/other` forms. **cs**: Translate `daysRemaining` with proper `one/few/many/other` forms. | `app_ru.arb`, `app_pl.arb`, `app_uk.arb`, `app_cs.arb` | L16 |

**Russian plural fix example:**
```json
// BEFORE (incorrect):
"daysRemaining": "{count, plural, =1{Ostalsya 1 den'} few{...} many{...} other{...}}"

// AFTER (correct):
"daysRemaining": "{count, plural, one{Ostalsya {count} den'} few{Ostalos' {count} dnya} many{Ostalos' {count} dney} other{Ostalos' {count} dney}}"
```
(The `one{}` CLDR category for Russian matches: 1, 21, 31, 41, 51, 61, 71, 81, 101, 1001... The `=1{}` exact match only matches the number 1.)

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 4.2 | **Add 14 missing keys + 3 rootDetection keys** | Add 14 biometric/Telegram error keys to all 26 non-English ARB files. Add 3 `rootDetectionDialog*` keys to ar, fa, he, ru. Provide English placeholder values initially. | All 26 non-English ARB files | M12 (partial) |

**14 missing keys:**
```
errorTelegramAuthCancelled, errorTelegramAuthFailed, errorTelegramAuthExpired,
errorTelegramNotInstalled, errorTelegramAuthInvalid, errorBiometricUnavailable,
errorBiometricNotEnrolled, errorBiometricFailed, errorBiometricLocked,
errorSessionExpired, errorAccountDisabled, errorRateLimitedWithCountdown (plural),
errorOfflineLoginRequired, errorOfflineSessionExpired
```

**3 rootDetection keys:**
```
rootDetectionDialogTitle, rootDetectionDialogDescription, rootDetectionDialogDismiss
```

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 4.3 | **Complete stub locales cs/da/sv/zh_Hant** | Copy all 275 keys from `app_en.arb` to these 4 files as base. Mark with `@@comment: "TODO: Professional translation required"`. | `app_cs.arb`, `app_da.arb`, `app_sv.arb`, `app_zh_Hant.arb` | M12 (partial) |
| 4.4 | **Add ~250 new ARB keys to app_en.arb** | Add new keys for strings that exist in code but have no ARB entry. | `app_en.arb` | M12 (partial) |

**New key category breakdown:**

| Category | Estimated New Keys |
|----------|-------------------|
| Auth screens (register, login, biometric, app lock) | ~40 |
| Settings screens | ~30 |
| Profile screens | ~30 |
| Config import screens | ~25 |
| Subscription/purchase screens | ~35 |
| Server selection screens | ~15 |
| Notification screens | ~10 |
| Diagnostics/speed test screens | ~10 |
| Shared widgets & error screens | ~15 |
| Provider/service error messages | ~20 |
| Accessibility labels (tooltip, semantics) | ~20 |
| **Total estimated new keys** | **~250** |

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 4.5 | **Wire 574+ strings to context.l10n across 39 files** | Replace all hardcoded strings with `context.l10n.keyName` calls. This is the largest single task. | ~39 files across all features | M12, L6 |

**Feature-by-feature migration order:**
1. `features/auth/` -- register, login, biometric, app lock (5 screens)
2. `features/settings/` -- all settings panels (8+ screens)
3. `features/profile/` -- profile, 2FA, devices (6+ screens)
4. `features/config_import/` -- import, QR scan, preview (4+ screens)
5. `features/subscription/` -- plans, purchase, payment (3+ screens)
6. `features/servers/` -- server list, selection (2 screens)
7. `features/onboarding/` -- onboarding flow (2 screens)
8. `features/notifications/` -- notification center (2 screens)
9. `features/referral/` -- referral dashboard (1 screen)
10. `features/diagnostics/` -- speed test, log viewer (2 screens)
11. `shared/widgets/` -- error_view, global_error_screen (3 widgets)
12. Providers / services -- error messages in Riverpod providers (use `AppError.localizedMessage()` from Phase 3)

**Pattern:**
```dart
// Before:
Text('Connect')

// After:
Text(context.l10n.connect)
```

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 4.6 | **Professional translation for 27 locales** | Replace English placeholder values with real translations. | All 27 ARB files | M12 |

**Tiered priority:**

| Priority | Locales | Rationale | Method |
|----------|---------|-----------|--------|
| P0 | ru, fa, ar, zh | Censored-region users (primary market) | Professional translation service |
| P1 | en, de, es, fr, pt | Major Western markets | Professional translation service |
| P2 | tr, ja, ko, uk | Significant user bases | Professional translation service |
| P3 | it, nl, pl, hi, th, vi, id, ms, he, ro | Extended coverage | Translation service, AI-assisted with human review |
| P4 | cs, da, sv, zh_Hant | Lower priority, stub locales | Translation service, AI-assisted with human review |

### Phase 5: Performance Optimization (P2) -- 3-4 days

**Objective**: Optimize startup time, reduce unnecessary rebuilds, improve network resilience.
**Dependency**: Phase 3 (Riverpod code-gen changes DI structure).

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 5.1 | **Lazy provider initialization** | Replace eager `buildProviderOverrides()` with lazy `Provider` instances (leveraging `@riverpod` from Phase 3). Only pre-create: SharedPreferences, SecureStorage, Dio, ApiClient, AuthInterceptor. All datasources and repositories created on first access. (MERGED: DOC1 M1 + DOC3 4.1) | `providers.dart` | M1 |
| 5.2 | **Split root widget providers** | Extract lifecycle listeners into a dedicated `LifecycleObserverWidget` under the router. Root widget only watches theme/locale/router. Use `RepaintBoundary` for performance isolation. | `app.dart` | M2 |
| 5.3 | **Add `distinct()` to VPN status stream** | Pipe `v2ray.onStatusChanged` through `.distinct()` to prevent duplicate events from triggering rebuilds. | `vpn_engine_datasource.dart:54` | M3 |
| 5.4 | **Add Dio retry interceptor** | Implement retry with exponential backoff for 5xx, timeouts, connection errors. Max 3 retries. Skip retry for 4xx. | `api_client.dart`, new `retry_interceptor.dart` | M4 |
| 5.5 | **Add `unawaited_futures` lint rule** | Add `unawaited_futures` and `discarded_futures` to `analysis_options.yaml`. Fix all violations (explicitly use `unawaited()` from `dart:async` where fire-and-forget is intentional). | `analysis_options.yaml`, various files | M5 |
| 5.6 | **Configure Sentry sampling per environment** | Set `tracesSampleRate` to 1.0 in dev, 0.2 in staging, 0.05 in prod. Use `EnvironmentConfig.environment` to determine. | `main.dart:49` | M6 |
| 5.7 | **Server list pagination** | Implement cursor-based pagination with `FutureProvider.family` and infinite scroll in `ServerListScreen`. | Server feature files | -- |
| 5.8 | **Flag asset optimization** | Use SVG flags via `flutter_svg` (already a dependency) or compress existing PNGs. Reduce APK size contribution from `assets/images/flags/`. | `assets/images/flags/`, server list widgets | -- |

### Phase 6: Quality & Polish (P3) -- 4-5 days

**Objective**: Modernize code patterns, expand test coverage, harden security, improve UX.
**Dependency**: Phase 5.

#### Code Quality (6.1-6.9)

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 6.1 | **Migrate Freezed entities to modern syntax** | Update all 7 entities from `@freezed abstract class X with _$X` to `@freezed sealed class X with _$X`. Re-run `build_runner`. | 7 entity files | L3 |
| 6.2 | **Fix Sentry deprecated APIs** | Replace `Sentry.configureScope()` with modern API in 3 locations. | `auth_provider.dart:219,231`, `root_detection_dialog.dart:42` | L5 |
| 6.3 | **Add explicit type arguments to API calls** | Add `<Map<String, dynamic>>` to all `_apiClient.get()/.post()/.delete()` calls. Resolves 22 inference warnings. | 4 datasource files | L7 |
| 6.4 | **Add ErrorBoundary widgets** | Create `FeatureErrorBoundary` widget. Wrap each feature's root screen. Shows graceful fallback + "Report" button. | New widget + 15 feature screens | L4 |
| 6.5 | **Await VPN config migration** | Convert fire-and-forget `_migrateOldConfigsIfNeeded()` to proper async init with completion flag. Factory pattern: `VpnRepositoryImpl.create()` async factory. | `vpn_repository_impl.dart:38-41` | L2 |
| 6.6 | **Fix BuildContext async gaps** | Ensure all `mounted` checks reference the correct State. Capture context before async operations. | 12+ locations | L8 |
| 6.7 | **Add iOS Info.plist privacy descriptions** | Add `NSFaceIDUsageDescription` for biometric auth and `NSLocationWhenInUseUsageDescription` for WiFi SSID detection. | `ios/Runner/Info.plist` | L9 |
| 6.8 | **Reduce Gradle JVM memory** | Lower from 8G -> 4G heap, 4G -> 2G metaspace. Sufficient for Flutter builds. | `gradle.properties` | L10 |
| 6.9 | **Fix AppLogger ring buffer performance** | Replace `List.removeAt(0)` with `Queue` from `dart:collection` for O(1) eviction. | `app_logger.dart:219` | M7 |

#### Testing & CI (6.10-6.12)

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 6.10 | **Test coverage expansion** | Add provider state tests for `VpnConnectionNotifier` (connect, disconnect, reconnect, force-disconnect, auto-connect edge cases). Add provider tests for `AuthNotifier` (login success/failure, logout, token refresh). Add widget tests for `ConnectionScreen`, `ProfileDashboardScreen`, `PlansScreen`. Set coverage threshold: 70% overall, 80% for domain layer. (Note: task 1.9 fixes broken tests; this task expands coverage.) | `test/features/**` | -- |
| 6.11 | **Dart 3 pattern matching standardization** | Standardize on `switch` expressions for sealed class matching. Add lint rule `unnecessary_type_check` and prefer exhaustive matching. | Various files | L12 |
| 6.12 | **Sealed failures migration** | Convert `Failure` from `Equatable` to sealed class + freezed for automatic equality/hashCode. | `lib/core/errors/failures.dart`, all consumers | L13 |

#### Platform & Init (6.13-6.15)

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 6.13 | **Firebase analytics race condition fix** | Guard analytics calls with `Completer<void>` pattern to prevent calls before Firebase initialization completes. | `lib/core/analytics/` | L14 |
| 6.14 | **Add @immutable annotations** | Add `@immutable` annotation to all value objects and use cases that don't use freezed (`ConnectVpnUseCase`, VPN state classes, `AppException` subclasses). | Various files | L15 |
| 6.15 | **Startup integration test** | Write integration test verifying: cold start -> interactive screen in < 5s. Add `flutter test integration_test/` to CI. | `integration_test/` | -- |

#### i18n QA (6.16-6.17)

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 6.16 | **i18n CI checks + lint rules** | Add ARB metadata (`@key` description entries). Add CI script to detect missing keys, untranslated values. Add grep-based check for `Text('...')` patterns. Add `@description` metadata to all keys in `app_en.arb`. | `app_en.arb`, `scripts/check_i18n_coverage.py`, `analysis_options.yaml` | M12 |
| 6.17 | **Visual QA per locale** | Test each supported locale on representative screens. Verify: text renders correctly (no truncation, no overflow), RTL layout correct for ar/he/fa, CJK characters display properly for ja/ko/zh/zh_Hant, long German/Russian text doesn't break layouts. | Manual QA task | M12 |

#### Security Hardening (6.18-6.20)

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 6.18 | **Token rotation on biometric change** | When `BiometricService.hasEnrollmentChanged()` detects changes, invalidate the stored session and require password re-authentication before enabling biometric login again. | `biometric_service.dart`, auth flow | -- |
| 6.19 | **Root/jailbreak enforcement policy** | Define clear policy: Logging mode (current) -- log to Sentry, show warning banner. Enforcement mode (future) -- prevent VPN connection on rooted devices (configurable via remote config). | `DeviceIntegrityChecker`, remote config | -- |
| 6.20 | **Memory-safe token handling** | Use `SecureStorageWrapper` for all token access, avoid caching tokens as class fields, call `_storage.delete()` immediately after use in auth interceptor. | Auth interceptor, token handling | -- |

#### UX Improvements (6.21-6.24)

| # | Task | Description | Files | Issues |
|---|------|-------------|-------|--------|
| 6.21 | **Haptic feedback** | Add `HapticFeedback.mediumImpact()` on VPN connect/disconnect button press. | Connection screen | -- |
| 6.22 | **Server ping indicators** | Add color-coded ping indicators: Green < 100ms, Yellow 100-200ms, Red > 200ms, Grey unavailable. | Server list widgets | -- |
| 6.23 | **Progressive onboarding** | Add skip button on each page. Add coachmarks for first-time feature discovery (server selection, kill switch). Add contextual tooltips instead of upfront tutorial. | Onboarding feature | -- |
| 6.24 | **Subscription expiry countdown widget** | Home screen widget showing days remaining with color gradient (green -> yellow -> red). | Home/subscription widgets | -- |

---

## 5. Success Criteria

| Metric | Current | Target | Source |
|--------|---------|--------|--------|
| App launch to interactive screen | **Infinite (hangs)** | < 2s cold start | DOC1 |
| `flutter analyze` errors | **12+** (lib + test) | **0** | DOC1 |
| `flutter analyze` warnings | **27** | < 5 | DOC1 |
| Crash-free session rate | Unknown | > 99.5% | DOC1 + DOC3 |
| Test suite | **Cannot execute** | All tests pass | DOC1 |
| Test coverage (overall) | ~0% (tests broken) / ~45% (if tests worked) | >= 70% | DOC1 + DOC3 |
| Test coverage (domain layer) | ~65% (estimated) | >= 80% | DOC3 |
| Provider type safety | `List<Object?>` cast | Typed overrides | DOC1 |
| Security: tokens in logs | **Exposed** | Redacted | DOC1 |
| Production LogInterceptor | **Enabled** | Disabled | DOC1 |
| `AppLocalizations` usage | 4/305 files (1.3%) | 100% of user-visible strings | DOC2 |
| ARB key coverage per locale | 50-261/275 | 525/525 (100%) | DOC2 |
| Hardcoded English strings in UI | **574+** | **0** | DOC2 |
| CLDR plural compliance | 4 locales broken | 100% | DOC2 |
| Locales with real translations | 3-4 / 27 | 27/27 | DOC2 |
| CI pipeline status | **None** | Green (all checks passing) | DOC2 + DOC3 |
| Repository error handling | Exceptions | Result<T> | DOC3 |
| Cold start time (Android) | Unmeasured | < 1.5s | DOC3 |
| APK size | Unmeasured | < 25MB | DOC3 |
| Provider boilerplate (`providers.dart`) | 270 lines | < 50 lines | DOC3 |
| CI build time | N/A | < 10 min | DOC3 |

---

## 6. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation | Source |
|------|--------|------------|------------|--------|
| Flutter stable channel breaks plugins | Build fails | Low | Test all plugins after switch; maintain compatibility matrix | DOC1 |
| flutter_v2ray_plus incompatible with stable Flutter | VPN core broken | Medium | Fork plugin; evaluate `flutter_v2ray_client` (task 2.5 research) | DOC1 |
| Riverpod 3.x `Override` type not exported | Cannot fix type safety | Low | Use extension methods or submit upstream PR | DOC1 |
| SecureStorage deadlock is device-specific | Cannot reproduce | Medium | Timeout + fallback; remove deprecated param; test on 5+ Android OEMs | DOC1 |
| share_plus upgrade breaks share functionality | Share feature broken | Medium | Pin version + add integration test; research first (task 2.4) | DOC1 |
| Quick setup provider fix affects authenticated users | Users re-see setup | Low | Check SharedPreferences value persisted correctly | DOC1 |
| Beta->Stable SDK switch changes rendering | UI regressions | Medium | Visual regression testing; golden tests for key screens | DOC1 |
| Translation quality (AI-generated or machine translation) | Poor UX for non-English users | High | Use professional translators for P0/P1 languages; AI + human review for P3/P4 | DOC2 |
| New hardcoded strings introduced after cleanup | i18n regression | Medium | CI check to block PRs with `Text('...')` patterns (task 3.3, 6.16) | DOC2 |
| Layout breakage with long translations (de, ru) | Truncated text | Medium | Add maxLines/overflow handling; visual QA per locale (task 6.17) | DOC2 |
| RTL layout bugs (ar, he, fa) | Broken UI for RTL users | Medium | Dedicated RTL testing pass; use `Directionality`-aware widgets | DOC2 |
| DI boilerplate explosion during Riverpod migration | Temporary breakage | Medium | Incremental migration, feature-by-feature; maintain backward compat | DOC3 |
| Offline-first cache staleness | Users see outdated data | Low | Clear TTL policies per repository (see CacheStrategy table) | DOC3 |
| Result<T> migration scope creep | Delays other phases | Medium | Migrate one repository at a time; start with AuthRepository | DOC3 |
| Professional translation budget not approved | Locales remain English | Medium | Use AI-assisted translation as interim; prioritize P0 languages | DOC2 |
| Key conflicts when merging new ARB keys | Build failures | Low | Use feature-prefixed naming convention consistently | DOC2 |

---

## 7. Dependencies & Constraints

| Dependency / Constraint | Details | Source |
|------------------------|---------|--------|
| **No library version downgrades** | All dependency changes must be forward-only. Strictly enforced throughout all phases. | DOC1 + Project CLAUDE.md |
| **No library changes (tasks 2.4, 2.5)** | share_plus and flutter_v2ray_plus tasks are RESEARCH ONLY. No version changes, no new libraries. | User constraint |
| **Flutter SDK switch allowed** | Task 1.1 (beta->stable) is permitted. This is a channel switch, not a downgrade. | User constraint |
| **riverpod_generator already installed** | Using it more (task 3.1) is not a new dependency -- it's in `dev_dependencies` already. | DOC3 |
| Flutter SDK | Must switch to stable; stay at ^3.10.8 or upgrade forward | DOC1 |
| Android minSdk | 24 (Android 7.0) -- required by flutter_v2ray_plus | DOC1 |
| Backend API | Auth endpoints must remain compatible; no backend changes | DOC1 |
| App Store | Changes must not break Play Store / App Store listings | DOC1 |
| local_auth | Must support both biometric + PIN/passcode fallback | DOC1 |
| Flutter `gen-l10n` toolchain | Available (already configured) | DOC2 |
| `context.l10n` extension | Available (already exists in `context_extensions.dart`) | DOC2 |
| `intl` package | Available (already in pubspec) | DOC2 |
| Professional translation service / budget | Needs approval for Phase 4 | DOC2 |
| CI pipeline access (GitHub Actions) | Needs configuration | DOC2 + DOC3 |

---

## 8. Out of Scope

| Item | Source |
|------|--------|
| iOS-specific VPN NetworkExtension implementation | DOC1 |
| Backend API changes | DOC1 + DOC3 |
| Landing page / marketing site | DOC1 |
| New feature development (feature freeze during stabilization) | DOC1 |
| Admin dashboard changes | DOC1 |
| Riverpod 4.x migration (defer until stable release) | DOC1 |
| Backend API localization (API returns error codes, not translated strings) | DOC2 |
| App Store metadata localization (store listing, screenshots) | DOC2 |
| Push notification localization (FCM topics, server-side content) | DOC2 |
| Adding new locales beyond 27 | DOC2 |
| Dynamic language switching without restart (already works via Riverpod state) | DOC2 |
| iOS WidgetKit enhancements (separate PRD) | DOC3 |
| macOS/Linux/Windows platform support (placeholder only) | DOC3 |
| Redesign of UI theme system (Material You + Cyberpunk is well-implemented) | DOC3 |
| Migration away from flutter_v2ray_plus (works, but vendor-locked -- research only in task 2.5) | DOC3 |

---

## 9. Deduplication Manifest

This section documents how overlapping items across the three source documents were resolved.

| Overlap | DOC1 Reference | DOC3 / DOC2 Reference | Resolution |
|---------|---------------|----------------------|------------|
| Lazy init / eager DI | M1 (Eager DI init) | DOC3 4.1 (Lazy Provider Init) | **MERGED** into single issue M1 (section 3.3) + single task 5.1 (Phase 5). Both sources cited in the issue description. |
| Riverpod code gen | L1 (Mixed providers) | DOC3 3.2 (DI code gen) + DOC3 3.7 (Annotations upgrade) | **MERGED** into single issue L1 (section 3.4) + single task 3.1 (Phase 3). All three references combined. |
| CI/CD pipeline | -- | DOC3 3.4 (CI/CD) + DOC2 Phase 4 (i18n CI) | **MERGED** into single issue M9 (section 3.3) + single task 3.3 (Phase 3). Pipeline includes both standard CI checks and i18n coverage checks. |
| Hardcoded strings | L6 (2 files) | DOC2 (entire scope: 574+ strings, 39 files) | **DOC2 subsumes DOC1 L6**. L6 retained as reference-only pointing to M12 and Phase 4. |
| Test fixes vs coverage | Task 1.9 (fix broken tests) | DOC3 3.9 (expand test coverage) | **Sequential**: Task 1.9 in Phase 1 fixes compile errors so tests can run. Task 6.10 in Phase 6 expands coverage to new areas. |
| Structured errors + i18n | -- | DOC3 3.6 (AppError) + DOC2 (l10n wiring) | **Sequential**: Phase 3 (task 3.5) creates AppError sealed class with `localizedMessage(l10n)`. Phase 4 (task 4.5) uses it when wiring provider error messages to l10n. |

---

## 10. Constraint Compliance Matrix

| Constraint | How Handled |
|-----------|-------------|
| **No version downgrades** | Enforced throughout all phases. No task downgrades any package version in `pubspec.yaml`. All dependency changes are forward-only upgrades or parameter removal (e.g., removing deprecated `encryptedSharedPreferences`). |
| **No library changes** | Tasks 2.4 (share_plus) and 2.5 (flutter_v2ray_plus) are explicitly marked **RESEARCH ONLY** with prominent notes. No code changes, no version bumps, no new dependencies added. |
| **Flutter SDK switch** | Allowed. Task 1.1 switches from beta channel to stable channel. This is a channel change (potentially a version downgrade in number but an upgrade in stability). Explicitly approved by user constraint. |
| **riverpod_generator already installed** | Task 3.1 adopts `@riverpod` annotations. The `riverpod_generator` package is already in `dev_dependencies` (confirmed in DOC3 3.2). Using it more broadly is not adding a new dependency. |
| **No new feature development** | All tasks are stabilization, security, architecture, i18n, performance, or quality. No new user-facing features are added (UX improvements in 6.21-6.24 are polish, not new features). |

---

## 11. Appendix A: File Inventory (Key Files)

| File | Role | Issues |
|------|------|--------|
| `lib/main.dart` | App entry point, deferred services | C1, M1, M6 |
| `lib/app/app.dart` | Root ConsumerWidget | C2, M2 |
| `lib/app/router/app_router.dart` | GoRouter + redirect guards | C1, C8 |
| `lib/core/di/providers.dart` | Eager DI setup, 16 overrides | H1, M1, C1 |
| `lib/core/storage/secure_storage.dart` | SecureStorage with cache | C1, H7 |
| `lib/core/network/api_client.dart` | Dio HTTP client | H4, M4 |
| `lib/core/network/auth_interceptor.dart` | JWT refresh with queue | -- (well-implemented) |
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
| `android/app/build.gradle.kts` | Android build | -- |
| `ios/Runner/Info.plist` | iOS config | L9 |
| `android/gradle.properties` | Gradle JVM config | L10 |

---

## 12. Appendix B: Dependency Audit

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

**Transitive upgradable**: `objective_c` 9.2.5 -> 9.3.0

---

## 13. Appendix C: flutter analyze Error Details

### Production Code Errors (lib/)
```
error - The named parameter 'options' isn't defined
       lib/features/auth/presentation/widgets/app_lock_overlay.dart:56:9
error - The name 'AuthenticationOptions' isn't a class
       lib/features/auth/presentation/widgets/app_lock_overlay.dart:56:24
```

### Test Code Errors (test/)
```
error - 'MockAuthRepository.login' signature mismatch (missing device, rememberMe)
       test/features/auth/presentation/providers/auth_provider_test.dart:51
error - 'MockAuthRepository.register' signature mismatch (missing device)
       test/features/auth/presentation/providers/auth_provider_test.dart:63
error - 'MockAuthRepository.logout' signature mismatch (missing refreshToken, deviceId)
       test/features/auth/presentation/providers/auth_provider_test.dart:77
error - 'MockAuthRepository.refreshToken' signature mismatch (missing deviceId)
       test/features/auth/presentation/providers/auth_provider_test.dart:83
error - Too many positional arguments (3 lines)
       test/features/auth/presentation/providers/auth_provider_test.dart:371,393,407
error - argument_type_not_assignable (clipboard_import_observer_test)
       test/features/config_import/presentation/widgets/clipboard_import_observer_test.dart:19
error - argument_type_not_assignable (providers_test)
       test/core/di/providers_test.dart:35
error - undefined_method 'linkOAuth'
       test/features/profile/data/datasources/profile_remote_ds_test.dart:220
```

---

## 14. Appendix D: Project Statistics

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

## 15. Appendix E: Strengths to Preserve

### From DOC1 (Stability Analysis)

1. **Well-structured DI pattern**: Provider overrides allow clean testing (despite the type safety issue)
2. **Proper security storage classification**: Consistent `SecureStorageWrapper` for tokens, `LocalStorageWrapper` for preferences
3. **Token refresh queue**: `AuthInterceptor` properly queues concurrent 401 requests -- prevents multiple simultaneous refresh calls
4. **Deferred Firebase init**: Post-frame callback pattern correctly avoids blocking cold start
5. **VPN sealed class hierarchy**: Exhaustive pattern matching for all connection states
6. **Proper error reporting**: Both `FlutterError.onError` and `PlatformDispatcher.onError` configured with Sentry
7. **SecureStorage cache layer**: In-memory cache with proper invalidation reduces I/O from ~200ms to near-zero
8. **Certificate pinning infrastructure**: `CertificatePinner` class exists with configurable fingerprints (but currently disabled by default -- see H8)
9. **Platform-aware update service**: Proper `Platform.isAndroid` guards in `AndroidUpdateService`
10. **App lock service**: Well-designed with biometric + PIN fallback, failed attempt tracking, and enrollment change detection

### From DOC3 (Architecture Review)

11. **Clean Architecture with Feature-Sliced Design**: Proper layer separation across all 15 features
12. **Strict type safety**: strict-casts, strict-raw-types, strict-inference analyzer rules, freezed entities, sealed classes for state
13. **Security infrastructure**: Certificate pinning, SecureStorage for credentials, jailbreak detection, biometric enrollment change detection, screen protection
14. **Layered error handling**: Exceptions -> failures mapping, NetworkErrorHandler mixin with retry + backoff, rate-limit parsing
15. **Observability**: Sentry integration, structured logging (AppLogger), Firebase Analytics abstraction, performance profiling
16. **Testing infrastructure**: 95+ test files covering unit, widget, integration, and E2E layers
17. **VPN connection state machine**: Sealed state hierarchy with auto-reconnect, kill switch, DNS resolution, force disconnect via WebSocket

### From DOC2 (i18n Analysis)

18. **i18n infrastructure in place**: `gen-l10n` configured, `l10n.yaml` correct, `nullable-getter: false`, all 4 MaterialApp delegates wired, `context.l10n` extension exists
19. **RTL handling**: `Directionality` widget in `app.dart` based on `LocaleConfig.isRtl()`
20. **Locale persistence**: `SettingsProvider` -> `SharedPreferences` for user locale preference

---

## 16. Appendix F: i18n Reference Data

### F.1 Complete List of 14 Missing Error Keys

```json
"errorTelegramAuthCancelled": "Telegram login was cancelled.",
"errorTelegramAuthFailed": "Telegram authentication failed. Please try again.",
"errorTelegramAuthExpired": "Telegram login expired. Please try again.",
"errorTelegramNotInstalled": "Telegram is not installed on this device.",
"errorTelegramAuthInvalid": "Invalid Telegram authentication data.",
"errorBiometricUnavailable": "Biometric authentication is not available on this device.",
"errorBiometricNotEnrolled": "No biometric data enrolled. Please set up fingerprint or face recognition in device settings.",
"errorBiometricFailed": "Biometric authentication failed. Please try again.",
"errorBiometricLocked": "Biometric authentication is locked. Try again later or use your password.",
"errorSessionExpired": "Your session has expired. Please log in again.",
"errorAccountDisabled": "Your account has been disabled. Please contact support.",
"errorRateLimitedWithCountdown": "Too many attempts. Please try again in {seconds, plural, =1{1 second} other{{seconds} seconds}}.",
"errorOfflineLoginRequired": "You need to be online to log in. Please check your connection.",
"errorOfflineSessionExpired": "Your cached session has expired. Please connect to the internet to log in."
```

### F.2 CLDR Plural Category Reference

| Language | Categories Required | Example (count=21) |
|----------|-------------------|--------------------|
| English | one, other | "21 days remaining" |
| Russian | one, few, many, other | "21 den'" (one), "22 dnya" (few), "25 dney" (many) |
| Arabic | zero, one, two, few, many, other | 6 forms needed |
| Japanese | other | Single form always |
| Polish | one, few, many, other | "21 dni" (many), "1 dzien'" (one), "2 dni" (few) |
| Czech | one, few, many, other | "21 dni" (other), "1 den" (one), "2 dny" (few) |
| German, Spanish, French, Italian, Dutch, Portuguese, Swedish, Danish, Hindi, Romanian | one, other | Standard two-form |
| Hebrew | one, two, other | Three forms |
| Korean, Chinese, Vietnamese, Thai, Indonesian, Malay, Turkish, Farsi | other | Single form always |

### F.3 Russian Plural Fix Example

```json
// BEFORE (incorrect):
"daysRemaining": "{count, plural, =1{Ostalsya 1 den'} few{...} many{...} other{...}}"

// AFTER (correct):
"daysRemaining": "{count, plural, one{Ostalsya {count} den'} few{Ostalos' {count} dnya} many{Ostalos' {count} dney} other{Ostalos' {count} dney}}"
```

The `one{}` CLDR category for Russian matches: 1, 21, 31, 41, 51, 61, 71, 81, 101, 1001...
The `=1{}` exact match only matches the number 1.

### F.4 Key Naming Convention

| Prefix | Usage | Example |
|--------|-------|---------|
| (none) | Core UI actions | `connect`, `disconnect`, `cancel` |
| `onboarding*` | Onboarding flow | `onboardingWelcomeTitle` |
| `settings*` | Settings screens | `settingsKillSwitchLabel` |
| `profile*` | Profile screens | `profileEditProfile` |
| `config*` | Config import | `configImportTitle` |
| `notification*` | Notifications | `notificationConnected` |
| `referral*` | Referral program | `referralDashboardTitle` |
| `diagnostics*` / `speedTest*` / `logViewer*` | Diagnostics | `speedTestStart` |
| `error*` | Error messages | `errorConnectionFailed` |
| `a11y*` | Accessibility labels | `a11yConnectButton` |
| `widget*` / `quickAction*` | Home widgets & quick actions | `widgetConnectLabel` |
| `subscription*` / `purchase*` | Subscription screens | `subscriptionChoosePlan` |
| `auth*` / `biometric*` | Auth screens | `authRegisterTitle` |
| `import*` | Import list actions | `importClearAll` |

---

## 17. Appendix G: Architecture Code Examples

### G.1 Result<T> Type Pattern

```dart
// Domain layer - sealed result type
sealed class Result<T> {
  const Result();
}
class Success<T> extends Result<T> {
  final T value;
  const Success(this.value);
}
class Err<T> extends Result<T> {
  final Failure failure;
  const Err(this.failure);
}

// Repository returns Result, never throws
Future<Result<(UserEntity, String)>> login({...});

// Provider uses exhaustive pattern matching
final result = await _repo.login(...);
switch (result) {
  case Success(:final value): state = AsyncData(AuthAuthenticated(value.$1));
  case Err(:final failure): state = AsyncData(AuthError(failure.message));
}
```

### G.2 CacheStrategy Enum

```dart
enum CacheStrategy {
  cacheFirst,             // Return cache, refresh in background
  networkFirst,           // Try network, fall back to cache
  cacheOnly,              // Never hit network
  networkOnly,            // Never use cache (sensitive data)
  staleWhileRevalidate,   // Return cache immediately, update after
}
```

**Per-repository application:**
| Repository | Strategy | TTL |
|-----------|----------|-----|
| ServerRepository | staleWhileRevalidate | 5 min |
| SubscriptionRepository | cacheFirst | 1 hour |
| AuthRepository (user profile) | cacheFirst | 24 hours |
| ReferralRepository | networkFirst | 15 min |
| SettingsRepository | cacheOnly | -- (local) |

### G.3 AppError Sealed Class with localizedMessage

```dart
sealed class AppError {
  String localizedMessage(AppLocalizations l10n);
}
class NetworkError extends AppError {
  @override
  String localizedMessage(l10n) => l10n.errorNoInternet;
}
class AuthError extends AppError {
  final AuthErrorCode code;
  @override
  String localizedMessage(l10n) => switch (code) {
    AuthErrorCode.invalidCredentials => l10n.errorInvalidCredentials,
    AuthErrorCode.emailNotVerified => l10n.errorEmailNotVerified,
    AuthErrorCode.sessionExpired => l10n.errorSessionExpired,
    AuthErrorCode.accountDisabled => l10n.errorAccountDisabled,
    AuthErrorCode.rateLimited => l10n.errorRateLimited,
    // ...
  };
}
class VpnError extends AppError {
  final VpnErrorCode code;
  @override
  String localizedMessage(l10n) => switch (code) {
    VpnErrorCode.engineFailed => l10n.errorVpnEngineFailed,
    VpnErrorCode.configInvalid => l10n.errorVpnConfigInvalid,
    // ...
  };
}
```

### G.4 WebSocket Jitter Calculation

```dart
Duration _calculateBackoff() {
  final baseSeconds = _initialBackoff.inSeconds *
      math.pow(_backoffMultiplier, _reconnectAttempt).toInt();
  final capped = math.min(baseSeconds, _maxBackoff.inSeconds);
  final jitter = Random().nextInt(capped ~/ 2 + 1); // 0..50% of delay
  return Duration(seconds: capped + jitter);
}
```

**Behavior comparison:**
| Attempt | Without Jitter | With Jitter (range) |
|---------|---------------|-------------------|
| 0 | 1s | 1s - 1.5s |
| 1 | 2s | 2s - 3s |
| 2 | 4s | 4s - 6s |
| 3 | 8s | 8s - 12s |
| 4 | 16s | 16s - 24s |
| 5+ | 30s (cap) | 30s - 45s |

### G.5 Firebase Analytics Completer Pattern

```dart
class FirebaseAnalyticsImpl implements AnalyticsService {
  final Completer<FirebaseAnalytics> _ready = Completer();

  void markReady(FirebaseAnalytics analytics) => _ready.complete(analytics);

  @override
  Future<void> logEvent(String name, {Map<String, Object>? parameters}) async {
    final analytics = await _ready.future;
    await analytics.logEvent(name: name, parameters: parameters);
  }

  @override
  Future<void> setUserId(String? id) async {
    final analytics = await _ready.future;
    await analytics.setUserId(id: id);
  }
}
```

---

**Document Version**: 1.0
**Created**: 2026-02-06
**Quality Score**: N/A (merge document, not discovery-driven)
**Phase Dependencies**: Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6
**Total Estimated Timeline**: 10-14 weeks (Phases 1-3: 2-3 weeks, Phase 4: 4-6 weeks, Phases 5-6: 2-3 weeks)
