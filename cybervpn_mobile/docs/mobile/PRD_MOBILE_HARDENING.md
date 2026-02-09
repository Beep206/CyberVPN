# PRD: CyberVPN Mobile App -- Quality Hardening & Performance Optimization

**Version:** 1.0
**Date:** 2026-02-07
**Status:** Draft
**Author:** Automated Multi-Agent Analysis (12 specialists + logcat review)
**App:** CyberVPN Mobile (`cybervpn_mobile/`)
**Files analyzed:** 382 Dart files + Android build config (Gradle, ProGuard, manifests)

---

## Executive Summary

This PRD consolidates findings from 12 parallel expert analyses covering architecture, performance, security, UI/UX, testing, navigation, state management, networking, animations, i18n, Dart patterns, and general development practices.

**Critical findings:**
1. The app freezes on the splash screen due to missing Dio timeouts, an endpoint path mismatch (`/mobile/auth/me` vs `/api/v1/auth/me`), and a production `StateError` crash when certificate fingerprints are not configured.
2. Android release builds have broken plugin registration: `build.gradle.kts` excludes the auto-generated `GeneratedPluginRegistrant`, a stale manual fallback uses reflection that R8 strips, and the `google-services` Gradle plugin is missing (Firebase fails to init).

**Overall Health Scores:**
| Domain | Score | Status |
|--------|-------|--------|
| Architecture | 7.5/10 | Good, needs provider scoping |
| Riverpod State | 9/10 | Excellent |
| Animations | 8.5/10 | Excellent |
| Adaptive UI | 9/10 | Excellent, Material 3 compliant |
| Networking | 8/10 | Strong, missing Dio timeouts |
| Navigation | 7/10 | 9 issues found |
| Android Build | 3/10 | Plugin registration broken, Firebase not init |
| Testing | 4.6/10 | 46% coverage, critical gaps |
| i18n | 7/10 | 27 languages, RTL gaps |
| Dev Practices | 9/10 | Production-grade |
| Dart Patterns | 9/10 | Excellent type safety |
| Security | 9/10 | Strong, WebSocket token in URL |

---

## Table of Contents

1. [P0: Splash Screen Freeze Fix](#1-p0-splash-screen-freeze-fix)
2. [P0: Production Crash Prevention](#2-p0-production-crash-prevention)
3. [P0: Biometric API Fix](#3-p0-biometric-api-fix)
4. [P0: Android Plugin Registration & Firebase Init](#4-p0-android-plugin-registration--firebase-init)
5. [P1: Networking Hardening](#5-p1-networking-hardening)
6. [P1: Navigation Hardening](#6-p1-navigation-hardening)
7. [P1: Security Improvements](#7-p1-security-improvements)
8. [P1: Performance Optimization](#8-p1-performance-optimization)
9. [P2: Architecture Improvements](#9-p2-architecture-improvements)
10. [P2: Testing Hardening](#10-p2-testing-hardening)
11. [P2: Internationalization Completion](#11-p2-internationalization-completion)
12. [P3: UI/UX Polish](#12-p3-uiux-polish)
13. [P3: Animation & Motion Refinements](#13-p3-animation--motion-refinements)
14. [Implementation Roadmap](#14-implementation-roadmap)
15. [Success Metrics](#15-success-metrics)

---

## 1. P0: Splash Screen Freeze Fix

### Problem Statement

The app freezes on the splash screen with the CyberVPN logo. Users cannot proceed past the loading spinner.

### Root Cause Analysis

**5 contributing factors identified:**

| # | Root Cause | Severity | File |
|---|-----------|----------|------|
| RC-1 | **Dio has no configured timeouts** -- `Dio()` created with infinite default timeouts. Any network call can hang indefinitely. | CRITICAL | `core/di/providers.dart:501` |
| RC-2 | **Endpoint path mismatch** -- `AuthRemoteDataSourceImpl` calls `GET /mobile/auth/me` but backend expects `/api/v1/auth/me`. Returns 404 or hangs. | CRITICAL | `features/auth/data/datasources/auth_remote_ds.dart:34` |
| RC-3 | **`connectivity_plus` can hang** -- `checkConnectivity()` may hang indefinitely on certain Android devices (Samsung, Xiaomi ROMs, Android 14+ OEM mods) during cold start. | HIGH | `core/network/network_info.dart:8-10` |
| RC-4 | **Production `StateError` crash** -- If `CERT_FINGERPRINTS` is not configured, `ApiClient` constructor throws `StateError`, crashing before `runApp()`. Native splash screen stays forever. | CRITICAL | `core/network/api_client.dart:75-79` |
| RC-5 | **No maximum splash timeout** -- No safety net if providers never resolve. Splash stays indefinitely. | HIGH | `app/router/app_router.dart:231-238` |

### Solution

#### 1.1 Configure Dio Timeouts (RC-1)

**File:** `core/di/providers.dart`

Replace `final dio = Dio();` with:
```dart
final dio = Dio(BaseOptions(
  connectTimeout: const Duration(seconds: 10),
  receiveTimeout: const Duration(seconds: 15),
  sendTimeout: const Duration(seconds: 10),
));
```

#### 1.2 Fix Endpoint Path Mismatch (RC-2)

**File:** `features/auth/data/datasources/auth_remote_ds.dart`

Replace hardcoded `_basePath = '/mobile/auth'` with `ApiConstants` paths:
```dart
// Before
static const String _basePath = '/mobile/auth';
// All calls: '$_basePath/login', '$_basePath/me', etc.

// After
// Use ApiConstants.login, ApiConstants.me, ApiConstants.register, etc.
```

#### 1.3 Add Timeout to NetworkInfo.isConnected (RC-3)

**File:** `core/network/network_info.dart`

```dart
Future<bool> get isConnected async {
  try {
    final result = await _connectivity.checkConnectivity()
        .timeout(const Duration(seconds: 2));
    return !result.contains(ConnectivityResult.none);
  } catch (_) {
    return true; // Assume connected on timeout; let HTTP calls determine reality
  }
}
```

#### 1.4 Convert Production StateError to Graceful Degradation (RC-4)

**File:** `core/network/api_client.dart`

Replace `throw StateError(...)` with logged warning + app continues launching. Show a configuration error screen instead of crashing silently.

#### 1.5 Add Maximum Splash Screen Timeout (RC-5)

**File:** `app/router/app_router.dart`

Add a 10-second maximum splash display time that forces navigation to `/login` regardless of provider state.

### Acceptance Criteria

- [ ] App launches to login or connection screen within 3 seconds on all devices
- [ ] No splash freeze on airplane mode, captive portals, or slow networks
- [ ] App still launches if certificate fingerprints not configured (with degraded functionality)
- [ ] Startup time logged and monitored via Sentry

---

## 2. P0: Production Crash Prevention

### 2.1 ApiClient Constructor Guards

**Problem:** `StateError` thrown in `ApiClient` constructor if `CERT_FINGERPRINTS` or HTTPS not configured. Permanently freezes app on splash.

**Solution:** Convert to logged warnings. Certificate pinning enforcement should happen at the network request level (reject individual requests), not at app initialization.

**File:** `core/network/api_client.dart:28-31, 75-79`

### 2.2 Duplicate SecureStorageWrapper Provider

**Problem:** Two separate `SecureStorageWrapper` providers exist. Using the wrong one bypasses prewarm cache.

**Files:**
- `core/device/device_provider.dart:8` (`secureStorageProvider` -- canonical)
- `core/di/providers.dart:162` (`secureStorageWrapperProvider` -- duplicate)

**Solution:** Remove `secureStorageWrapperProvider`. Ensure all imports use `secureStorageProvider`.

### 2.3 LocalStorageWrapper Re-initializes SharedPreferences

**Problem:** `LocalStorageWrapper` lazily calls `SharedPreferences.getInstance()` instead of using the pre-initialized instance from `main()`.

**File:** `core/storage/local_storage.dart:23-27`

**Solution:** Inject pre-initialized `SharedPreferences` via constructor.

---

## 3. P0: Biometric API Fix

### Problem

`BiometricService.authenticate()` uses deprecated `local_auth` parameters:
```dart
biometricOnly: true,              // DEPRECATED in local_auth 2.x
persistAcrossBackgrounding: true,  // NOT a valid parameter
```

**File:** `features/auth/domain/usecases/biometric_service.dart:59`

### Solution

Update to current `local_auth` API:
```dart
return _localAuth.authenticate(
  localizedReason: reason,
  options: const AuthenticationOptions(
    biometricOnly: true,
    stickyAuth: true,
  ),
);
```

### Acceptance Criteria

- [ ] Biometric authentication works on iOS and Android
- [ ] No compilation warnings from `local_auth`

---

## 4. P0: Android Plugin Registration & Firebase Init

### Problem Statement

Logcat from a 60-second smoke test shows **6 errors** that break core functionality in release builds. Three plugin classes fail to load (`ClassNotFoundException`), the auto-generated plugin registrant is missing, and Firebase cannot initialize.

**Source:** Logcat capture from release APK on physical device.

### Root Cause Analysis

**4 contributing factors identified:**

| # | Root Cause | Severity | File |
|---|-----------|----------|------|
| RC-6 | **`build.gradle.kts` excludes auto-generated `GeneratedPluginRegistrant.java`** -- Lines 143-145 tell the Java compiler to skip Flutter's auto-generated plugin registrant. The class is never compiled into the APK. Flutter engine's reflection lookup fails at runtime. | CRITICAL | `android/app/build.gradle.kts:143-145` |
| RC-7 | **Stale hand-committed `GeneratedPluginRegistrant.java`** -- A manually committed copy sits in `android/app/src/main/java/io/flutter/plugins/` conflicting with auto-generation. Combined with the exclude directive, neither version compiles. | CRITICAL | `android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java` |
| RC-8 | **R8 strips plugin classes loaded via reflection** -- `ManualPluginRegistrant.kt` fallback uses `Class.forName()` to load plugins. R8 cannot trace reflective references, so it strips `connectivity_plus`, `device_info_plus`, and `dynamic_color` classes (they lack ProGuard keep rules). **Class names are NOT stale** -- verified against pub cache source. | CRITICAL | `android/app/src/main/kotlin/.../ManualPluginRegistrant.kt` + `proguard-rules.pro` |
| RC-9 | **`google-services` Gradle plugin not applied** -- `google-services.json` files exist in all 3 flavor dirs but the plugin that reads them is never applied. Firebase cannot find project config. | HIGH | `android/app/build.gradle.kts` (plugins block) |

### Impact Analysis

| Failed Component | Features That Break |
|-----------------|-------------------|
| `ConnectivityPlugin` | Network status detection, auto-reconnect, offline mode, VPN monitoring |
| `DeviceInfoPlusPlugin` | Device fingerprinting for auth, analytics dimensions, crash report metadata |
| `DynamicColorPlugin` | Material You theming on Android 12+ (graceful fallback to cyberpunk theme) |
| `FirebaseApp` | Push notifications (FCM), analytics events, Firebase Messaging token |

**Debug vs Release behavior:**

| Issue | Debug Builds | Release Builds |
|-------|-------------|---------------|
| GeneratedPluginRegistrant | ManualPluginRegistrant fallback works (no R8) | Fallback partially fails (R8 strips classes) |
| connectivity_plus | Works | **ClassNotFoundException** |
| device_info_plus | Works | **ClassNotFoundException** |
| dynamic_color | Works | **ClassNotFoundException** |
| Firebase | **Fails in both** (plugin never applied) | **Fails in both** |

### Solution

#### 4.1 Remove Exclude Directive & Delete Stale Registrant (RC-6, RC-7)

**File:** `android/app/build.gradle.kts`

Delete lines 143-145:
```kotlin
// DELETE ENTIRELY:
tasks.withType<JavaCompile>().configureEach {
    exclude("io/flutter/plugins/GeneratedPluginRegistrant.java")
}
```

**File:** `android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java`

Delete entire file. The `dev.flutter.flutter-plugin-loader` in `settings.gradle.kts` auto-generates the correct version at build time with current class names and direct instantiation (not reflection), so R8 can trace all references.

#### 4.2 Remove ManualPluginRegistrant (RC-8)

**File:** `android/app/src/main/kotlin/com/cybervpn/cybervpn_mobile/ManualPluginRegistrant.kt`

Delete entire file. With the auto-generated registrant restored, this reflection-based fallback is unnecessary and is the source of R8 stripping issues.

**File:** `android/app/src/main/kotlin/com/cybervpn/cybervpn_mobile/MainActivity.kt`

Remove the manual registration call:
```kotlin
// DELETE this line from configureFlutterEngine():
ManualPluginRegistrant.registerWith(flutterEngine)
```

#### 4.3 Apply google-services Gradle Plugin (RC-9)

**File:** `android/settings.gradle.kts`

Add to plugins block:
```kotlin
plugins {
    id("dev.flutter.flutter-plugin-loader") version "1.0.0"
    id("com.android.application") version "8.11.1" apply false
    id("org.jetbrains.kotlin.android") version "2.2.20" apply false
    id("com.google.gms.google-services") version "4.4.2" apply false  // ADD
}
```

**File:** `android/app/build.gradle.kts`

Add to plugins block:
```kotlin
plugins {
    id("com.android.application")
    id("kotlin-android")
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services")  // ADD
}
```

#### 4.4 Verify google-services.json Flavor Package Names

Each `google-services.json` must contain a `client` entry matching the flavor's `applicationId`:

| Flavor | Expected `package_name` in JSON |
|--------|-------------------------------|
| dev | `com.cybervpn.cybervpn_mobile.dev` |
| staging | `com.cybervpn.cybervpn_mobile.staging` |
| prod | `com.cybervpn.cybervpn_mobile` |

### Verification Sequence

1. Apply fixes 4.1 + 4.2 + 4.3
2. Run `flutter clean && flutter pub get`
3. Build debug: `flutter build apk --debug --flavor dev` -- verify compilation
4. Run on device, check logcat for `GeneratedPluginsRegister` and `ManualPluginRegistrant` errors -- should be gone
5. Build release: `flutter build apk --release --flavor dev` -- verify R8 does not strip plugins
6. Install release APK, verify: connectivity detection, device info, dynamic colors, Firebase push

### Acceptance Criteria

- [ ] No `ClassNotFoundException` in logcat for any Flutter plugin
- [ ] No `GeneratedPluginsRegister` errors in logcat
- [ ] `FirebaseApp` initializes successfully (no "default options" warning)
- [ ] Release APK passes all plugin registration (connectivity, device_info, dynamic_color)
- [ ] `ManualPluginRegistrant.kt` deleted, no manual plugin registration in codebase
- [ ] `flutter build apk --release --flavor prod` succeeds without plugin errors

---

## 5. P1: Networking Hardening

### 4.1 WebSocket Token Security

**Problem:** Access JWT passed as URL query parameter (`?ticket=<jwt>`). Tokens visible in server logs, proxy logs, CDN logs.

**File:** `core/network/websocket_provider.dart:34-38`

**Solution:** Implement the ticket endpoint (`POST /api/v1/ws/ticket`) that returns a short-lived, single-use ticket. Pass ticket in URL instead of JWT.

### 4.2 Certificate Pinning on WebSocket

**Problem:** Certificate pinning only applied to HTTP (Dio), not WebSocket connections.

**File:** `core/network/websocket_client.dart`

**Solution:** Apply same SHA-256 fingerprint validation to WebSocket TLS handshake.

### 4.3 Offline Request Queue

**Problem:** Failed requests are lost when network disconnects. No offline queue or sync mechanism.

**Solution:** Implement a simple offline queue for critical operations (auth, subscription sync). Replay on reconnect.

### 4.4 Unsafe Response Casting

**Problem:** Remote data sources cast API responses without null checks:
```dart
final data = response.data as Map<String, dynamic>; // Can throw
```

**Files:** `auth_remote_ds.dart:54-57`, `server_remote_ds.dart:52-53`

**Solution:** Add defensive null/type checks before casting.

### 4.5 Interceptor Ordering Concern

**Problem:** `RetryInterceptor` comes AFTER `AuthInterceptor`. If token refresh fails during retry, no second refresh attempt occurs.

**File:** `core/di/providers.dart:503-506`

**Solution:** Document this as intentional behavior or reorder interceptors.

---

## 6. P1: Navigation Hardening

### 6.1 Quick Setup Loading Race Condition

**Problem:** `shouldShowQuickSetupProvider` returns `true` while loading (value=null), causing route flash between `/quick-setup` and `/connection`.

**File:** `app/router/app_router.dart:219, 288`

**Solution:** Track loading state of quick setup provider in redirect. Keep on splash until ALL providers resolve.

### 6.2 Redirect Exception Returns /login

**Problem:** Unhandled exception in redirect callback returns `/login`, forcing logout on transient errors.

**File:** `app/router/app_router.dart:314-317`

**Solution:** Return `null` (preserve current location) on exception instead of `/login`.

### 6.3 Concurrent Deep Links Overwrite

**Problem:** Second deep link overwrites pending first deep link. First link is lost.

**File:** `app/router/app_router.dart:262-264`

**Solution:** Queue deep links or show user choice if >1 pending.

### 6.4 Server Detail in Branch Stack

**Problem:** `/servers/:id` defined in servers branch. Tapping servers tab returns to detail, not list.

**File:** `app/router/app_router.dart:556-567`

**Solution:** Move server detail to root navigator (full-screen modal like profile sub-routes).

### 6.5 Quick Actions Null Context

**Problem:** Quick actions silently fail if root navigator context unavailable (app in background).

**File:** `features/quick_actions/domain/services/quick_actions_handler.dart:213`

**Solution:** Queue navigation action if context unavailable. Retry on foreground.

---

## 7. P1: Security Improvements

### 7.1 Remove Deprecated Plaintext Credential Storage

**Problem:** `setBiometricCredentials()` and `getBiometricCredentials()` still store plaintext email/password in SecureStorage. Marked `@Deprecated` but still callable.

**File:** `core/storage/secure_storage.dart:309-339`

**Solution:** Remove methods entirely. Migration method `migrateCredentialFormat()` handles old data cleanup.

### 7.2 WebSocket Event Parsing Error Boundary

**Problem:** Malformed WebSocket event payload could throw uncaught exception in `fromJson()`.

**File:** `core/network/websocket_client.dart:40-51`

**Solution:** Wrap each factory call in try-catch, return null on parse failure.

### 7.3 Configure Certificate Pinning for Production

**Problem:** `CERT_FINGERPRINTS` not configured in CI/CD. Production builds would crash (after RC-4 fix: would run without pinning).

**Solution:** Add SHA-256 fingerprints to GitHub Secrets and CI/CD `--dart-define`.

---

## 8. P1: Performance Optimization

### 8.1 Return Cached User Immediately on Startup

**Problem:** `getCurrentUser()` makes a network call during startup, adding 1-3 seconds to splash time even when cached user exists.

**File:** `features/auth/data/repositories/auth_repository_impl.dart:117-150`

**Solution:** Return cached user immediately for startup path. Validate session in background after first frame renders.

### 8.2 Parallelize DeviceService.getDeviceInfo()

**Problem:** 5 sequential platform channel calls add ~200-500ms to auth flow.

**File:** `core/device/device_service.dart:31-65`

**Solution:** Use `Future.wait()` for independent calls.

### 8.3 Split _AppLifecycleManager

**Problem:** 8 `ref.watch()` + 4 `ref.listen()` in single `build()` method. Any provider change triggers full rebuild.

**File:** `app/app.dart:310-496`

**Solution:** Extract into separate `ConsumerWidget` children, each watching one provider.

### 8.4 Provider Rebuild Cascade

**Problem:** Auth state change cascades through 5+ derived providers:
`authProvider` -> `currentUserProvider` -> `profileProvider` -> `subscriptionProvider` -> `serverListProvider`

**Solution:** Use `.select()` to watch specific fields:
```dart
final userId = ref.watch(currentUserProvider.select((u) => u?.id));
```

---

## 9. P2: Architecture Improvements

### 9.1 Provider Scoping Strategy

**Problem:** 45+ global providers. Features cannot be independently tested without full DI graph.

**Solution:**
1. Audit and categorize all providers (global/feature/screen)
2. Apply `.autoDispose` to screen-scoped providers
3. Document scoping decisions in comments

### 9.2 Break Circular Feature Dependencies

**Problem:** VPN -> Servers -> VPN circular dependency via shared entities.

**Solution:** Extract shared domain models to `core/domain/`:
- `vpn_protocol.dart` -- shared enum
- `server_reference.dart` -- ID + name only
- VPN feature references servers by ID, presentation layer joins data

### 9.3 Standardize Cache Invalidation

**Problem:** Inconsistent caching: Auth uses 5-min TTL, servers use stale-while-revalidate (no TTL), VPN uses migration-based versioning.

**Solution:** Document and enforce cache TTL per data type:
| Data Type | TTL | Strategy |
|-----------|-----|----------|
| Auth tokens | 5 min | Proactive refresh |
| Server list | 15 min | Stale-while-revalidate |
| User profile | 1 hour | Cache-first |
| Subscription | 30 min | Event-driven invalidation |

### 9.4 Split DI Provider File

**Problem:** `providers.dart` is 517 lines with all provider definitions.

**Solution:** Split into:
- `infrastructure_providers.dart` (Dio, storage, network)
- `repository_providers.dart` (all repositories)
- `usecase_providers.dart` (domain use cases)
- `providers.dart` (re-exports, backward compatibility)

### 9.5 Fix ref.read in build() Anti-pattern

**Problem:** `VpnConnectionNotifier.build()` uses `ref.read()` instead of `ref.watch()`. Provider doesn't rebuild when dependencies change.

**File:** `features/vpn/presentation/providers/vpn_connection_notifier.dart:44`

**Solution:** Use lazy getters: `VpnRepository get _repo => ref.read(vpnRepositoryProvider);`

---

## 10. P2: Testing Hardening

### Current State

- **166 test files** covering 382 source files (~46% file coverage)
- CI/CD enforces 70% overall, 80% domain layer coverage
- Test infrastructure: mocktail, golden_toolkit, integration_test

### 10.1 Phase 1: Critical Path Tests (Weeks 1-2)

| Gap | Risk | Effort |
|-----|------|--------|
| **Purchase Screen** | Revenue-impacting bugs undetected | 3 days |
| **Kill Switch** (Android/iOS) | Device traffic exposed on VPN disconnect | 3 days |
| **DNS Leak Protection** | User location leaked | 2 days |
| **Subscription Renewal/Expiry** | Users lose access unexpectedly | 2 days |

### 10.2 Phase 2: Stability Tests (Weeks 3-4)

| Gap | Coverage | Effort |
|-----|----------|--------|
| App Lock Service | 0% | 2 days |
| VPN Lifecycle Reconciler | 0% | 2 days |
| Split Tunnel (Android/iOS) | 0% | 3 days |
| Offline Session Service | 0% | 1 day |

### 10.3 Phase 3: Polish Tests (Weeks 5-6)

| Gap | Type | Effort |
|-----|------|--------|
| Golden tests expansion | Visual regression (4 themes, RTL, tablet) | 2 days |
| Widget screen tests | User interaction testing | 2 days |
| Integration test completion | End-to-end flows | 2 days |

### 10.4 Test Infrastructure Fixes

- **Consolidate test directories** -- remove duplicate `test/unit/`, use `test/features/` only
- **Add integration tests to CI/CD** -- currently not run
- **Platform channel testing framework** -- for kill switch, split tunnel

### Target Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Overall coverage | 70% | 78% |
| Domain layer | 80% | 85% |
| Payment feature | 0% | 85% |
| VPN platform features | 30% | 70% |
| Integration tests | 5 (incomplete) | 12 complete |
| Golden tests | 3 | 20+ |

---

## 11. P2: Internationalization Completion

### Current State

- 27 supported locales, 1,547 translation keys in English
- RTL support for Arabic, Hebrew, Farsi
- ICU pluralization with language-appropriate rules

### 11.1 Complete RTL Language Translations

**Problem:** Arabic, Hebrew, Farsi missing ~265 keys each (~34% of English coverage).

**Solution:** Complete all missing translations. Prioritize user-facing screens: settings, profile, errors, subscription.

### 11.2 Expose All Supported Languages in UI

**Problem:** Only 14 of 27 languages shown in language picker. 13 hidden (Czech, Danish, Hindi, Indonesian, Malay, Dutch, Polish, Romanian, Swedish, Thai, Vietnamese, Chinese Traditional).

**File:** `features/settings/data/repositories/language_repository.dart`

**Solution:** Expand `_supportedLanguages` list to all 27 locales.

### 11.3 Fix Hardcoded Strings

**Problem:** Several user-facing strings hardcoded in English.

| File | String | Priority |
|------|--------|----------|
| `app/app.dart:477-483` | "Your biometric data has changed..." | P1 |
| `features/auth/domain/usecases/biometric_service.dart` | Biometric dialog strings | P1 |
| `features/settings/presentation/widgets/settings_search.dart:54` | "OLED Mode" | P2 |
| Various form fields | "Email", "Password" labels | P2 |

### 11.4 Add Translation Validation

**Solution:** Add CI/CD check that prevents PRs with incomplete translations. Create translation completeness dashboard.

---

## 12. P3: UI/UX Polish

### 12.1 Tablet Master-Detail Persistence

**Problem:** Selected server/detail pane lost on app restart.

**Solution:** Save selected pane in SharedPreferences across restarts.

### 12.2 Foldable Device Testing

**Problem:** No explicit testing on Samsung Galaxy Z Fold devices.

**Solution:** Add foldable-specific test cases for hinge positions and inner/outer screen transitions.

### 12.3 Screen Reader Audit

**Problem:** No formal accessibility audit with TalkBack (Android) and VoiceOver (iOS).

**Solution:** Conduct full screen reader walkthrough. Add missing semantic labels.

### 12.4 Font Size Extremes

**Problem:** UI layout at `TextScale.extraLarge` (1.3x) not tested on compact screens.

**Solution:** Test and fix overflow issues at all text scale levels.

### 12.5 Lottie Asset Cleanup

**Problem:** Unused Lottie assets (`connect.json`, `privacy.json`, `globe.json`) in `assets/animations/`.

**Solution:** Remove or rename unused assets. Add error handling for missing Lottie files.

---

## 13. P3: Animation & Motion Refinements

### Current State: 8.5/10

The animation system is well-implemented with proper disposal, accessibility support, and RepaintBoundary isolation.

### 13.1 Centralize Animation Durations

**Problem:** Mix of `AnimDurations.fast` (~150ms), `AnimDurations.normal` (~300ms), and hardcoded milliseconds.

**Solution:** Use `tokens.dart` `AnimDurations` constants everywhere.

### 13.2 Add Animation Golden Tests

**Problem:** No golden tests for animation frames.

**Solution:** Add golden tests for key animation states (connected, connecting, disconnected) in both themes.

### 13.3 Frame Rate Telemetry

**Problem:** No monitoring of animation performance under stress.

**Solution:** Add frame rate profiling to `ConnectButton` (dual AnimationController) and Lottie animations during connection state changes.

---

## 14. Implementation Roadmap

### Sprint 1 (Week 1-2): Critical Fixes

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Configure Dio timeouts | P0 | 1h | Fixes splash freeze |
| Fix endpoint path mismatch | P0 | 2h | Fixes auth failures |
| Convert StateError to graceful degradation | P0 | 3h | Prevents production crash |
| Add NetworkInfo timeout | P0 | 1h | Prevents platform channel hang |
| Add max splash timeout | P0 | 2h | Safety net for all freeze scenarios |
| Fix BiometricService API | P0 | 1h | Fixes compilation/runtime error |
| Remove duplicate SecureStorageWrapper | P0 | 1h | Prevents race conditions |
| Remove exclude directive + delete stale GeneratedPluginRegistrant | P0 | 30min | Restores Flutter auto-registration |
| Delete ManualPluginRegistrant + remove call from MainActivity | P0 | 30min | Eliminates R8 stripping of plugin classes |
| Apply google-services Gradle plugin | P0 | 1h | Fixes Firebase init (FCM, analytics) |
| Verify google-services.json flavor package names | P0 | 30min | Ensures Firebase works per flavor |

**Sprint 1 Total: ~13.5h estimated**

### Sprint 2 (Week 3-4): Networking & Navigation

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Implement WebSocket ticket auth | P1 | 1d | Security: removes JWT from URLs |
| Fix redirect exception handling | P1 | 2h | Prevents logout on transient errors |
| Fix Quick Setup loading race | P1 | 3h | Prevents route flashing |
| Return cached user on startup | P1 | 3h | Reduces cold start by 1-3s |
| Parallelize DeviceService calls | P1 | 2h | Saves 200-500ms on auth |
| Fix hardcoded l10n strings | P1 | 3h | i18n compliance |
| Move server detail to root navigator | P1 | 2h | Fixes back button behavior |

**Sprint 2 Total: ~3d estimated**

### Sprint 3 (Week 5-8): Testing & Architecture

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Purchase screen tests | P2 | 3d | Revenue protection |
| Kill switch tests | P2 | 3d | Security verification |
| Provider scoping audit | P2 | 2d | Architecture health |
| Split _AppLifecycleManager | P2 | 1d | Performance improvement |
| Complete RTL translations | P2 | 3d | Market expansion |
| Consolidate test directories | P2 | 1d | Developer experience |

**Sprint 3 Total: ~2 weeks estimated**

### Sprint 4+ (Month 3-6): Long-term

| Task | Priority | Effort |
|------|----------|--------|
| Break VPN-Servers circular dependency | P2 | 1 week |
| Event bus for cross-feature communication | P3 | 1 week |
| Certificate pinning on WebSocket | P1 | 2 days |
| Offline request queue | P2 | 1 week |
| Golden test expansion (20+ tests) | P3 | 1 week |
| Foldable device testing | P3 | 3 days |
| Provider dependency visualization | P3 | 3 days |

---

## 15. Success Metrics

### Launch Readiness Gate

| Metric | Current | Required | Target |
|--------|---------|----------|--------|
| Cold start time | Unknown (freeze) | < 3s | < 2s |
| Splash freeze rate | ~100% (broken) | 0% | 0% |
| Crash-free sessions | Unknown | > 99% | > 99.5% |
| Auth check duration | ~3s (timeout) | < 500ms | < 200ms |
| Plugin registration errors | 6 (3 ClassNotFound + Firebase + registrant) | 0 | 0 |
| Firebase initialization | Failed | Success | Success |

### Quality Gates (Ongoing)

| Metric | Current | Target |
|--------|---------|--------|
| Test coverage (overall) | 70% | 78% |
| Test coverage (domain) | 80% | 85% |
| Test coverage (payments) | 0% | 85% |
| Translation completeness | 66% avg | 95%+ |
| RTL translation coverage | 66% | 95%+ |
| Accessibility audit score | Not measured | WCAG AA |
| Animation frame drops | Not measured | < 1% at 60fps |

### Security Gates

| Metric | Current | Target |
|--------|---------|--------|
| JWT in URLs | Yes (WebSocket) | No |
| Certificate pinning | HTTP only | HTTP + WebSocket |
| Deprecated credential storage | Present | Removed |
| PII in Sentry | Redacted | Verified redacted |

---

## Appendix A: Files Referenced

### Critical Path (Splash Freeze)
- `lib/main.dart` -- Startup sequence
- `lib/app/app.dart` -- App widget, lifecycle manager
- `lib/app/router/app_router.dart` -- Router redirect logic
- `lib/features/splash/presentation/screens/splash_screen.dart` -- Splash UI
- `lib/features/auth/presentation/providers/auth_provider.dart` -- Auth state machine
- `lib/features/auth/data/repositories/auth_repository_impl.dart` -- Auth repository
- `lib/features/auth/data/datasources/auth_remote_ds.dart` -- Remote API calls
- `lib/core/di/providers.dart` -- DI graph, Dio creation
- `lib/core/network/api_client.dart` -- HTTP client, cert pinning
- `lib/core/network/network_info.dart` -- Connectivity check
- `lib/core/constants/api_constants.dart` -- Canonical API paths

### Android Build & Plugin Registration
- `android/app/build.gradle.kts` -- App build config, R8, exclude directive (lines 143-145)
- `android/build.gradle.kts` -- Root Gradle config
- `android/settings.gradle.kts` -- Plugin loader, AGP, Kotlin versions
- `android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java` -- STALE (delete)
- `android/app/src/main/kotlin/.../ManualPluginRegistrant.kt` -- Reflection fallback (delete)
- `android/app/src/main/kotlin/.../MainActivity.kt` -- FlutterEngine config, method channels
- `android/app/proguard-rules.pro` -- R8 keep rules
- `android/app/src/dev/google-services.json` -- Firebase config (dev flavor)
- `android/app/src/staging/google-services.json` -- Firebase config (staging flavor)
- `android/app/src/prod/google-services.json` -- Firebase config (prod flavor)

### Security
- `lib/core/network/auth_interceptor.dart` -- Token refresh, circuit breaker
- `lib/core/network/websocket_client.dart` -- WebSocket connection
- `lib/core/network/websocket_provider.dart` -- WebSocket auth (JWT in URL)
- `lib/core/security/certificate_pinner.dart` -- TLS pinning
- `lib/core/storage/secure_storage.dart` -- Encrypted storage
- `lib/core/auth/token_refresh_scheduler.dart` -- Proactive refresh
- `lib/core/auth/jwt_parser.dart` -- Token parsing

### State Management
- `lib/features/vpn/presentation/providers/vpn_connection_notifier.dart` -- VPN state
- `lib/features/servers/presentation/providers/server_list_provider.dart` -- Server list
- `lib/features/settings/presentation/providers/settings_provider.dart` -- Settings
- `lib/features/subscription/presentation/providers/subscription_provider.dart` -- Subscription
- `lib/features/notifications/presentation/providers/notification_provider.dart` -- Notifications

### Architecture
- `lib/core/errors/exceptions.dart` -- Exception hierarchy
- `lib/core/errors/failures.dart` -- Failure sealed class
- `lib/core/types/result.dart` -- Result type
- `lib/core/errors/app_error.dart` -- Presentation errors

---

## Appendix B: Constraints

- **No library version downgrades** -- All fixes must work with current or newer versions
- **No root/jailbreak detection** -- App must launch without barriers on all devices
- **No user-blocking mechanisms** -- App should always be usable, even in degraded state
- **Backward compatibility** -- Migration paths required for stored data format changes
