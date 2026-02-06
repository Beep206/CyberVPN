# PRD: CyberVPN Mobile App Quality Remediation

**Version:** 1.0
**Date:** 2026-02-06
**Author:** Senior Mobile Engineering Team (3-skill audit)
**Status:** Draft
**App:** CyberVPN Flutter Mobile Client
**Codebase:** `cybervpn_mobile/`

---

## 1. Executive Summary

A comprehensive audit of the CyberVPN Flutter mobile application was conducted using three independent analysis perspectives: **Flutter Expert** (best practices, performance, null safety), **Senior Flutter Architect** (clean architecture, DI, testing, code organization), and **Flutter Developer** (UX, security, network layer, VPN engine, app lifecycle).

The audit identified **83 unique issues** (after deduplication across the three reports):

| Severity | Count | Description |
|----------|-------|-------------|
| **Critical** | 11 | Pre-release blockers: security vulnerabilities, architectural violations, compile failures |
| **High** | 18 | Major bugs, performance issues, missing core functionality |
| **Medium** | 28 | Code quality, consistency, moderate UX gaps |
| **Low** | 16 | Polish, minor inconsistencies, documentation |
| **Positive** | 10 | Well-implemented patterns to preserve |

This PRD organizes all findings into **6 remediation phases** with clear acceptance criteria, affected files, and estimated effort.

---

## 2. Goals and Non-Goals

### Goals
- Fix all Critical and High severity issues before production release
- Establish architectural consistency (Clean Architecture compliance)
- Achieve security posture appropriate for a VPN application
- Ensure full i18n coverage across all user-facing strings
- Improve test coverage for critical code paths

### Non-Goals
- Full Riverpod code-gen migration (tracked as separate initiative)
- Tablet/foldable responsive redesign (separate UX initiative)
- UI visual redesign or new feature development
- Backend API changes

---

## 3. Phase 1: Security Critical (Pre-Release Blockers)

**Priority:** P0
**Estimated Effort:** 3-5 days
**Blocking:** Production release

### 3.1 Configure Certificate Pinning for Production

**Severity:** Critical
**Sources:** Flutter Expert 8.2, Senior Architect 5.5, Flutter Dev 9.1

**Problem:** `EnvironmentConfig.certificateFingerprints` is empty. Certificate pinning code exists but is not activated. A VPN app without certificate pinning is vulnerable to MITM attacks -- all API traffic (JWT tokens, credentials, VPN configurations) can be intercepted.

**Files:**
- `lib/core/network/api_client.dart` (lines 39-44)
- `lib/core/config/environment_config.dart`

**Acceptance Criteria:**
- [ ] At least 2 SHA-256 certificate fingerprints configured (primary + backup)
- [ ] Fingerprints injected via `--dart-define` in CI/CD, not hardcoded
- [ ] Pinning active in staging and production builds
- [ ] Pinning disabled in dev builds for proxy debugging
- [ ] Certificate rotation plan documented

---

### 3.2 Remove .env from Flutter Assets

**Severity:** Critical
**Sources:** Flutter Expert 8.5, Senior Architect 5.6, Flutter Dev 9.5

**Problem:** `.env` file is listed under `flutter: assets:` in `pubspec.yaml` (line 112), bundling it into the APK/IPA. Anyone decompiling the app can extract all environment variables.

**Files:**
- `pubspec.yaml` (line 112)
- `lib/core/config/environment_config.dart`

**Acceptance Criteria:**
- [ ] `.env` removed from `pubspec.yaml` assets list
- [ ] `EnvironmentConfig.init()` skips `.env` loading in release builds (`kReleaseMode` guard)
- [ ] All production configuration injected via `--dart-define`
- [ ] Comment in `pubspec.yaml` explaining why `.env` must never be an asset

---

### 3.3 Replace HTTPS assert() with Runtime Enforcement

**Severity:** Critical
**Sources:** Flutter Expert 8.3, Senior Architect 5.4, Flutter Dev 5.4

**Problem:** HTTPS enforcement uses `assert()` which is stripped in release builds. A misconfigured `baseUrl` would silently allow cleartext HTTP traffic in production.

**Files:**
- `lib/core/network/api_client.dart` (lines 22-28)

**Acceptance Criteria:**
- [ ] `assert()` replaced with `throw StateError(...)` that fires in all build modes
- [ ] Unit test verifying that HTTP URL in production mode throws

---

### 3.4 Fix Auth Interceptor Infinite Refresh Loop

**Severity:** Critical
**Sources:** Flutter Dev 5.3

**Problem:** Token refresh request goes through the same Dio instance with the same `AuthInterceptor`. If the refresh endpoint returns 401 (expired refresh token), the interceptor tries to refresh again, creating an infinite loop.

**Files:**
- `lib/core/network/auth_interceptor.dart` (lines 98-102)

**Acceptance Criteria:**
- [ ] Refresh request flagged with `options.extra['isRefreshRequest'] = true`
- [ ] `onError` handler skips 401 processing when flag is present
- [ ] On refresh failure, tokens cleared and user logged out (single attempt)
- [ ] Unit test for recursive 401 scenario

---

### 3.5 Remove PII from Sentry User Context

**Severity:** Critical
**Sources:** Flutter Dev 9.3

**Problem:** `_setSentryUser` sends email and username to Sentry despite `sendDefaultPii = false`. This creates GDPR compliance risk.

**Files:**
- `lib/features/auth/presentation/providers/auth_provider.dart` (lines 262-270)

**Acceptance Criteria:**
- [ ] `SentryUser` only contains `id` (UUID, not PII)
- [ ] `email` and `username` fields removed from Sentry context
- [ ] Privacy documentation comment added

---

### 3.6 Replace Plaintext Biometric Credential Storage

**Severity:** Critical
**Sources:** Flutter Dev 9.2

**Problem:** `setBiometricCredentials()` stores the user's raw email and password as JSON in secure storage. If keystore is compromised (rooted device), plaintext password is recoverable.

**Files:**
- `lib/core/storage/secure_storage.dart` (lines 212-241)

**Acceptance Criteria:**
- [ ] Backend issues device-bound auth token during biometric enrollment
- [ ] Raw password never persisted to any storage
- [ ] Biometric auth uses device token exchange instead of stored credentials
- [ ] Migration clears old credential format on update

---

### 3.7 Fix Deprecated biometricOnly Parameter

**Severity:** Critical
**Sources:** Flutter Expert 1.1

**Problem:** `local_auth ^3.0.0` no longer accepts `biometricOnly` as a direct parameter on `authenticate()`. Must use `AuthenticationOptions`.

**Files:**
- `lib/features/auth/presentation/widgets/app_lock_overlay.dart` (line 58)
- `lib/features/auth/domain/usecases/biometric_service.dart` (line 59)

**Acceptance Criteria:**
- [ ] `biometricOnly` and `stickyAuth` passed via `AuthenticationOptions`
- [ ] Compiles without deprecation warnings against local_auth 3.x
- [ ] Biometric authentication flow tested on Android and iOS

---

### 3.8 Configure Sentry DSN for Staging/Production

**Severity:** Critical
**Sources:** Flutter Expert 8.4

**Problem:** All build flavors set `SENTRY_DSN = ""`. Crash reporting is disabled for all environments. Production crashes go undetected.

**Files:**
- `android/app/build.gradle.kts` (lines 88, 98, 107)

**Acceptance Criteria:**
- [ ] Real Sentry DSN configured for staging and production flavors
- [ ] Dev flavor may remain empty (local debugging)
- [ ] Verify crash reports appear in Sentry dashboard

---

## 4. Phase 2: Architecture Critical (Clean Architecture Compliance)

**Priority:** P1
**Estimated Effort:** 5-7 days
**Impact:** Testability, maintainability, separation of concerns

### 4.1 Fix Presentation Layer Importing Concrete Data Implementations

**Severity:** Critical
**Sources:** Senior Architect 1.1, 1.2

**Problem:** Every feature's presentation provider imports the concrete `*RepositoryImpl` and data sources from the data layer, violating the Dependency Inversion Principle.

**Files (14 affected):**
| Presentation File | Violating Import |
|---|---|
| `auth/presentation/providers/auth_provider.dart:17` | `auth_repository_impl.dart` |
| `servers/presentation/providers/server_list_provider.dart:10-14` | `server_repository_impl.dart`, `ping_service.dart`, `favorites_local_datasource.dart` |
| `subscription/presentation/providers/subscription_provider.dart:11-14` | `subscription_repository_impl.dart`, `revenuecat_datasource.dart` |
| `vpn/presentation/providers/vpn_connection_provider.dart:21-28` | `vpn_repository_impl.dart`, `kill_switch_service.dart` |
| `profile/presentation/providers/profile_provider.dart:11-12` | `profile_repository_impl.dart`, `profile_remote_ds.dart` |
| `notifications/presentation/providers/notification_provider.dart:9-11` | `notification_repository_impl.dart`, `fcm_datasource.dart`, `notification_local_datasource.dart` |
| `config_import/presentation/providers/config_import_provider.dart:8` | `config_import_repository_impl.dart` |

**Acceptance Criteria:**
- [ ] All `*RepositoryProvider` and `*DataSourceProvider` definitions moved to `core/di/providers.dart`
- [ ] Presentation files import ONLY domain abstract classes
- [ ] No `import '...data/...'` in any `presentation/` file
- [ ] `flutter analyze` passes
- [ ] All existing tests pass (update mock injection as needed)

---

### 4.2 Wire Use Cases into Notifiers (Restore Input Validation)

**Severity:** High (functional bug)
**Sources:** Senior Architect 1.3, 4.1

**Problem:** `AuthNotifier.login()` and `.register()` bypass `LoginUseCase` / `RegisterUseCase`, which contain input validation (`InputValidators.validateEmail()`, `.validatePassword()`). Users get cryptic server errors instead of client-side validation.

**Files:**
- `lib/features/auth/presentation/providers/auth_provider.dart` (lines 127, 162)
- `lib/features/auth/domain/usecases/login.dart`
- `lib/features/auth/domain/usecases/register.dart`

**Acceptance Criteria:**
- [ ] `AuthNotifier.login()` calls `LoginUseCase.call()` instead of `_repo.login()`
- [ ] `AuthNotifier.register()` calls `RegisterUseCase.call()` instead of `_repo.register()`
- [ ] Input validation fires before network request
- [ ] Invalid email/password returns user-friendly error messages
- [ ] Unit test verifying validation is called

---

### 4.3 Move Infrastructure Providers to Core DI

**Severity:** High
**Sources:** Senior Architect 2.2, 2.3

**Problem:** `secureStorageProvider` and `networkInfoProvider` are defined inside `vpn_connection_provider.dart` (a feature-specific presentation file) but consumed by auth, biometric, profile, and DI modules.

**Files:**
- `lib/features/vpn/presentation/providers/vpn_connection_provider.dart` (lines 118-129)
- `lib/core/di/providers.dart`

**Acceptance Criteria:**
- [ ] `secureStorageProvider` moved to `core/providers/` or `core/di/providers.dart`
- [ ] `networkInfoProvider` moved to `core/providers/` or `core/di/providers.dart`
- [ ] All imports updated across the codebase
- [ ] No duplicate provider definitions remain

---

### 4.4 Split vpn_connection_provider.dart (867 lines)

**Severity:** High
**Sources:** Senior Architect 8.1

**Problem:** Single file contains sealed state class, 7 provider definitions, storage constants, a 670-line notifier, and 3 derived providers.

**Files:**
- `lib/features/vpn/presentation/providers/vpn_connection_provider.dart` (867 lines)

**Acceptance Criteria:**
- [ ] `vpn_connection_state.dart` -- sealed state hierarchy
- [ ] `vpn_dependency_providers.dart` -- infrastructure providers (or moved to core/di/)
- [ ] `vpn_connection_notifier.dart` -- the notifier class
- [ ] `vpn_connection_providers.dart` -- notifier provider + derived providers
- [ ] No file exceeds 300 lines

---

### 4.5 Fix Manual JSON Serialization in VpnConnectionNotifier

**Severity:** Critical
**Sources:** Senior Architect 5.1

**Problem:** `_persistLastConnection` and `_loadLastServer` manually serialize `ServerEntity` fields instead of using Freezed-generated `toJson()`/`fromJson()`. Any field added to `ServerEntity` must be updated in two places.

**Files:**
- `lib/features/vpn/presentation/providers/vpn_connection_provider.dart` (lines 649-691)

**Acceptance Criteria:**
- [ ] Uses `ServerEntity.toJson()` / `ServerEntity.fromJson()` for persistence
- [ ] All `ServerEntity` fields correctly round-trip through serialization
- [ ] Unit test verifying persistence/restoration of server entity

---

## 5. Phase 3: High Priority Fixes

**Priority:** P2
**Estimated Effort:** 5-7 days

### 5.1 Fix GoRouter Recreation on Auth State Change

**Severity:** High
**Sources:** Flutter Expert 6.1, 2.5

**Problem:** `appRouterProvider` creates a new `GoRouter` instance whenever auth state changes, resetting all navigation state (scroll position, sub-routes).

**Files:**
- `lib/app/router/app_router.dart` (line 152)

**Acceptance Criteria:**
- [ ] GoRouter created once with `refreshListenable`
- [ ] Auth state changes trigger redirect re-evaluation, not router recreation
- [ ] Navigation stack preserved during auth transitions
- [ ] Unit test for redirect logic

---

### 5.2 Add App Lifecycle Observer for VPN State Reconciliation

**Severity:** High
**Sources:** Flutter Dev 10.1

**Problem:** When app resumes from background, VPN connection state is not verified. If tunnel dropped while backgrounded (common on iOS), UI shows "Connected" when user is unprotected.

**Files:**
- `lib/features/vpn/presentation/providers/vpn_connection_provider.dart`

**Acceptance Criteria:**
- [ ] `WidgetsBindingObserver` registered in `VpnConnectionNotifier`
- [ ] On `AppLifecycleState.resumed`, actual VPN engine state checked
- [ ] State reconciled: auto-reconnect or transition to disconnected
- [ ] User sees accurate connection status after app resume

---

### 5.3 Add VPN Engine Reconnection Logic

**Severity:** Critical (Flutter Dev) / High (impact)
**Sources:** Flutter Dev 7.1, 7.2

**Problem:** `VpnEngineDatasource` provides no reconnection mechanism. Status uses magic string `'CONNECTED'` comparison.

**Files:**
- `lib/features/vpn/data/datasources/vpn_engine_datasource.dart` (lines 1-85)

**Acceptance Criteria:**
- [ ] Enum mapping for V2Ray status strings (CONNECTING, CONNECTED, DISCONNECTED, ERROR, etc.)
- [ ] Fallback/logging for unknown state strings
- [ ] `reconnect()` method that reuses last config
- [ ] Distinct state emission for RECONNECTING vs CONNECTING

---

### 5.4 Implement Foreground Push Notification Display

**Severity:** High
**Sources:** Flutter Dev 8.1, 8.2

**Problem:** `_handleForegroundMessage` only logs -- users see no notification while app is open. `_handleMessageOpenedApp` doesn't navigate to relevant screen.

**Files:**
- `lib/core/services/push_notification_service.dart` (lines 156-173)

**Acceptance Criteria:**
- [ ] Foreground messages displayed via `flutter_local_notifications` or in-app banner
- [ ] Notification tap navigates to relevant screen via GoRouter deep link
- [ ] `message.data['route']` parsed and used for navigation

---

### 5.5 Cache HapticService Enabled State

**Severity:** High
**Sources:** Flutter Expert 3.1, 2.4

**Problem:** Every haptic call (`selection()`, `impact()`, `heavy()`, etc.) performs a full async `SharedPreferences` read. On busy screens with multiple haptic interactions, this introduces latency.

**Files:**
- `lib/core/haptics/haptic_service.dart` (lines 49-66)

**Acceptance Criteria:**
- [ ] Haptics-enabled state cached at construction time
- [ ] Re-checked only when settings change (reactive watch)
- [ ] No async I/O during haptic invocation

---

### 5.6 Fix Force-Unwrap on response.data! in AuthInterceptor

**Severity:** High
**Sources:** Flutter Expert 4.1

**Problem:** `response.data!` force-unwrap during token refresh. Malformed server response crashes and logs user out.

**Files:**
- `lib/core/network/auth_interceptor.dart` (line 104)

**Acceptance Criteria:**
- [ ] Null check before unwrap with proper `DioException` on null
- [ ] Graceful degradation instead of forced logout on transient errors

---

### 5.7 Add CancelToken Support to API Client

**Severity:** High
**Sources:** Flutter Dev 5.1

**Problem:** No request cancellation on widget disposal. Orphaned requests waste bandwidth and can cause errors on unmounted widgets.

**Files:**
- `lib/core/network/api_client.dart` (lines 91-121)

**Acceptance Criteria:**
- [ ] `CancelToken? cancelToken` parameter on `get`, `post`, `patch`, `delete`
- [ ] Passed through to Dio calls
- [ ] Key providers create `CancelToken` and cancel in `ref.onDispose()`

---

### 5.8 Fix Broken Navigation Routes in Profile

**Severity:** Medium (functional bug)
**Sources:** Flutter Dev 1.6, 1.7

**Problem:** `context.push('/plans')` should be `/subscribe`. `context.push('/profile/security')` should be `/profile/2fa`. Server list uses `Navigator.pushNamed` instead of GoRouter.

**Files:**
- `lib/features/profile/presentation/screens/profile_dashboard_screen.dart` (lines 413, 434)
- `lib/features/servers/presentation/screens/server_list_screen.dart` (line 103)

**Acceptance Criteria:**
- [ ] Profile "Upgrade Plan" navigates to `/subscribe`
- [ ] Profile "Security Settings" navigates to `/profile/2fa`
- [ ] Server list uses `context.push('/servers/${server.id}')` via GoRouter

---

### 5.9 Localize Remaining Hardcoded Auth Strings

**Severity:** High
**Sources:** Flutter Dev 1.1, 1.2, Flutter Expert 1.4

**Problem:** Login screen and app lock overlay have ~20 hardcoded English strings not wired to AppLocalizations.

**Files:**
- `lib/features/auth/presentation/screens/login_screen.dart` (lines 216-374)
- `lib/features/auth/presentation/widgets/app_lock_overlay.dart` (lines 57-148)

**Acceptance Criteria:**
- [ ] All user-facing strings use `AppLocalizations.of(context)`
- [ ] ARB keys added to `app_en.arb`
- [ ] `flutter gen-l10n` succeeds with 0 untranslated messages
- [ ] Translations propagated to all 26 non-English locales

---

### 5.10 Replace Hardcoded Colors in Connection Screen with Theme Tokens

**Severity:** High
**Sources:** Flutter Dev 3.1

**Problem:** Connection screen uses ~15 hardcoded colors (`Color(0xFF0A0E1A)`, etc.) that don't respond to theme changes or light/dark mode.

**Files:**
- `lib/features/vpn/presentation/screens/connection_screen.dart` (lines 69-420)

**Acceptance Criteria:**
- [ ] All colors use `theme.colorScheme.*` or `CyberColors` tokens
- [ ] Screen adapts to light/dark mode
- [ ] Cyberpunk theme variant preserved via ThemeExtension

---

## 6. Phase 4: State Management & Model Consistency

**Priority:** P2
**Estimated Effort:** 5-7 days

### 6.1 Migrate Key State Classes to Freezed

**Severity:** High
**Sources:** Senior Architect 5.2, 5.3, Flutter Expert 2.3

**Problem:** `ServerListState`, `VpnSettings`, `AuthState` variants, and `QuickSetupState` are manually-written without Freezed. Missing equality operators cause unnecessary Riverpod rebuilds.

**Files:**
- `lib/features/servers/presentation/providers/server_list_provider.dart` (lines 28-118)
- `lib/features/settings/presentation/providers/settings_provider.dart` (VpnSettings, line 494)
- `lib/features/auth/presentation/providers/auth_state.dart`

**Acceptance Criteria:**
- [ ] All state classes annotated with `@freezed`
- [ ] Generated `copyWith`, `==`, `hashCode`, `toString`
- [ ] Manual implementations removed
- [ ] `build_runner` runs clean

---

### 6.2 Standardize Repository Error Handling

**Severity:** Medium
**Sources:** Senior Architect 3.4, Flutter Expert 7.1, 7.2

**Problem:** Inconsistent error handling: some repos catch `AppException` only, some catch generic `Exception`, some silently swallow errors.

**Files:**
- `lib/features/profile/data/repositories/profile_repository_impl.dart`
- `lib/features/vpn/data/repositories/vpn_repository_impl.dart`
- `lib/core/storage/secure_storage.dart` (lines 238, 286)
- `lib/features/auth/data/repositories/auth_repository_impl.dart` (line 108)

**Acceptance Criteria:**
- [ ] All repositories: `on AppException` catch → mapped failure, then `catch (e)` → `UnknownFailure`
- [ ] Silent `catch (_)` blocks replaced with `catch (e) { AppLogger.warning(...); }`
- [ ] Consistent pattern across all 7 repository implementations

---

### 6.3 Fix ConnectVpnUseCase Throwing Failures as Exceptions

**Severity:** Medium
**Sources:** Senior Architect 4.2

**Problem:** `ConnectVpnUseCase` converts `Result<void>` back into thrown exceptions, defeating the Result pattern.

**Files:**
- `lib/features/vpn/domain/usecases/connect_vpn.dart` (lines 13-21)
- `lib/features/vpn/domain/usecases/disconnect_vpn.dart`

**Acceptance Criteria:**
- [ ] Use cases return `Result<void>` instead of throwing
- [ ] Callers use pattern matching instead of try/catch

---

### 6.4 Memoize ServerListState.filteredServers

**Severity:** Medium
**Sources:** Flutter Expert 3.2

**Problem:** `filteredServers` is a computed getter that recomputes the full filter/sort on every access. Multiple widgets reading it in the same frame trigger redundant computation.

**Files:**
- `lib/features/servers/presentation/providers/server_list_provider.dart` (lines 48-97)

**Acceptance Criteria:**
- [ ] `filteredServers` computed once and cached as a field
- [ ] Recomputed in `copyWith` when filter/sort/search criteria change
- [ ] Or: separate derived Riverpod provider with memoization

---

## 7. Phase 5: Testing & Quality

**Priority:** P3
**Estimated Effort:** 5-7 days

### 7.1 Add Unit Tests for VpnConnectionNotifier

**Severity:** High
**Sources:** Senior Architect 6.1

**Problem:** The most complex code path (867 lines) has no direct unit tests.

**Acceptance Criteria:**
- [ ] Test: auto-connect on launch
- [ ] Test: `connect()` with kill switch enabled
- [ ] Test: `handleNetworkChange()` reconnection
- [ ] Test: `connectFromCustomServer()` flow
- [ ] Test: state persistence and restoration
- [ ] >= 80% line coverage for the notifier

---

### 7.2 Add Repository Tests for VPN, Subscription, Referral

**Severity:** High
**Sources:** Senior Architect 6.2

**Problem:** `VpnRepositoryImpl`, `SubscriptionRepositoryImpl`, `ReferralRepositoryImpl` have no tests.

**Acceptance Criteria:**
- [ ] `VpnRepositoryImpl`: config persistence, migration, connect/disconnect
- [ ] `SubscriptionRepositoryImpl`: in-memory cache, purchase flow, restore
- [ ] `ReferralRepositoryImpl`: availability caching, code retrieval
- [ ] Mock all data sources

---

### 7.3 Add Integration Tests for Purchase Flow

**Severity:** Medium
**Sources:** Senior Architect 6.3

**Acceptance Criteria:**
- [ ] Test: `SubscriptionNotifier.purchase()` happy path
- [ ] Test: `SubscriptionNotifier.restorePurchases()` success and failure
- [ ] Mock RevenueCat data source

---

### 7.4 Consolidate Test Directory Structure

**Severity:** Medium
**Sources:** Senior Architect 6.4

**Problem:** Tests split between `test/unit/auth/`, `test/features/auth/`, `test/widget/` with overlapping coverage.

**Acceptance Criteria:**
- [ ] Single consistent structure: `test/features/<name>/unit/`, `test/features/<name>/widget/`
- [ ] Or: `test/unit/`, `test/widget/`, `test/integration/` top-level
- [ ] No duplicate test locations

---

## 8. Phase 6: Polish & Debt

**Priority:** P4
**Estimated Effort:** 3-5 days

### 8.1 Non-Atomic Token Writes

**Sources:** Flutter Expert 1.2, Flutter Dev 6.2

**Files:** `lib/core/storage/secure_storage.dart` (lines 143-149)

**Fix:** Use `Future.wait()` for concurrent writes or single JSON key.

---

### 8.2 Add Persistent Cache to SubscriptionRepository

**Sources:** Senior Architect 3.2

**Problem:** In-memory only cache; lost on provider disposal. No offline plan access.

**Fix:** Add `SharedPreferences` or local DB cache with TTL.

---

### 8.3 Cache Referral Availability with TTL

**Sources:** Senior Architect 3.3

**Problem:** Every `getReferralCode()`, `getStats()` call first hits `isAvailable()` network endpoint.

**Fix:** Cache availability result for 5 minutes.

---

### 8.4 Extract Auth Side Effects from AuthNotifier

**Sources:** Senior Architect 1.5

**Problem:** `AuthNotifier` handles Sentry, FCM registration, attestation in addition to auth state.

**Fix:** Extract into dedicated side-effect providers listening to auth state changes.

---

### 8.5 Add Missing Empty State for Filtered Server List

**Sources:** Flutter Dev 1.5

**Fix:** "No servers match your search" message when filter returns 0 results.

---

### 8.6 Use Case Directory Naming Consistency

**Sources:** Senior Architect 1.4

**Problem:** Profile uses `use_cases/` (snake_case) while all others use `usecases/`.

**Fix:** Consolidate to `usecases/` everywhere.

---

### 8.7 Theme-Aware SnackBar Colors

**Sources:** Flutter Dev 3.2

**Fix:** Replace hardcoded `Colors.blue.shade800` etc. with `theme.colorScheme.*`.

---

### 8.8 Cap Staggered Animation Count

**Sources:** Flutter Dev 2.1

**Problem:** 50+ servers with individual `AnimationController` causes jank.

**Fix:** First 10 items animate, rest appear instantly.

---

### 8.9 Add RepaintBoundary to Route Transitions

**Sources:** Flutter Dev 2.2

**Fix:** Wrap transition child in `RepaintBoundary` to isolate animation layer.

---

### 8.10 Secure Storage Cache Clear on Memory Pressure

**Sources:** Flutter Dev 6.1

**Fix:** `WidgetsBindingObserver` calling `invalidateCache()` on `didHaveMemoryPressure()`.

---

### 8.11 FCM Token Registration on Auth Completion

**Sources:** Flutter Dev 8.3

**Problem:** Token only registered with backend after login. Pre-auth campaigns can't reach device.

**Fix:** Store locally, register on auth completion, re-register on token refresh.

---

### 8.12 Tablet / Landscape Responsive Layouts

**Sources:** Flutter Dev 4.1

**Problem:** No screen adapts to tablet or landscape. Bottom nav wastes space on tablets.

**Fix:** `LayoutBuilder` with `NavigationRail` for tablets; master-detail for server list.

---

### 8.13 Decide on Riverpod Code Generation Strategy

**Sources:** Flutter Expert 2.1, Senior Architect 2.1

**Problem:** `riverpod_annotation` and `riverpod_generator` declared but only 3 usages. 100+ manual providers.

**Decision needed:**
- **Option A:** Incremental migration to `@riverpod` (recommended, ~2 weeks)
- **Option B:** Remove codegen packages and formalize manual provider pattern

---

## 9. Positive Findings (Preserve These)

The audit identified well-implemented patterns that should be preserved and used as models:

| Pattern | Location | Quality |
|---------|----------|---------|
| Sealed `Result<T>` type | `core/types/result.dart` | Excellent -- `map`, `flatMap`, `when` extensions |
| SecureStorage wrapper | `core/storage/secure_storage.dart` | Pre-warmed cache, platform-specific keychain/keystore |
| CachedRepository mixin | `core/data/cache_strategy.dart` | 5 strategies, stale-while-revalidate |
| VPN config split storage | `vpn/data/repositories/vpn_repository_impl.dart` | Metadata in SharedPrefs, secrets in SecureStorage |
| Debug log redaction | `core/network/api_client.dart` | Auth headers and response bodies redacted |
| Feature error boundaries | `shared/widgets/feature_error_boundary.dart` | Per-route graceful degradation |
| Biometric enrollment detection | `auth/domain/usecases/biometric_service.dart` | Hash-based change detection with forced re-auth |
| Analytics consent (GDPR) | `core/analytics/analytics_providers.dart` | Opt-out default, proper Firebase toggle |
| Config import parsers | `config_import/` | Excellent test coverage for VLESS/VMess/Trojan/SS |
| Deferred initialization | `main.dart` | Non-critical services post-first-frame with profiling |

---

## 10. Issue Cross-Reference Matrix

| ID | Issue | Phase | Severity | Expert | Architect | Dev |
|---|---|---|---|---|---|---|
| 3.1 | Certificate pinning | 1 | Critical | 8.2 | 5.5 | 9.1 |
| 3.2 | .env in assets | 1 | Critical | 8.5 | 5.6 | 9.5 |
| 3.3 | HTTPS assert | 1 | Critical | 8.3 | 5.4 | 5.4 |
| 3.4 | Auth refresh loop | 1 | Critical | -- | -- | 5.3 |
| 3.5 | Sentry PII | 1 | Critical | -- | -- | 9.3 |
| 3.6 | Biometric creds | 1 | Critical | -- | -- | 9.2 |
| 3.7 | biometricOnly API | 1 | Critical | 1.1 | -- | -- |
| 3.8 | Sentry DSN empty | 1 | Critical | 8.4 | -- | -- |
| 4.1 | Layer violations | 2 | Critical | -- | 1.1, 1.2 | -- |
| 4.2 | Use cases bypassed | 2 | High | -- | 1.3, 4.1 | -- |
| 4.3 | Provider location | 2 | High | -- | 2.2, 2.3 | -- |
| 4.4 | File splitting | 2 | High | -- | 8.1 | -- |
| 4.5 | Manual JSON | 2 | Critical | -- | 5.1 | -- |
| 5.1 | GoRouter recreation | 3 | High | 6.1 | -- | -- |
| 5.2 | Lifecycle observer | 3 | High | -- | -- | 10.1 |
| 5.3 | VPN reconnection | 3 | Critical/High | -- | -- | 7.1, 7.2 |
| 5.4 | Push notifications | 3 | High | -- | -- | 8.1, 8.2 |
| 5.5 | Haptic caching | 3 | High | 3.1, 2.4 | -- | -- |
| 5.6 | response.data! | 3 | High | 4.1 | -- | -- |
| 5.7 | CancelToken | 3 | High | -- | -- | 5.1 |
| 5.8 | Broken routes | 3 | Medium | -- | -- | 1.6, 1.7 |
| 5.9 | Auth i18n | 3 | High | 1.4 | -- | 1.1, 1.2 |
| 5.10 | Theme hardcoded | 3 | High | 3.4 | -- | 3.1 |
| 6.1 | Freezed migration | 4 | High | 2.3 | 5.2, 5.3 | -- |
| 6.2 | Error handling | 4 | Medium | 7.1, 7.2 | 3.4 | -- |
| 7.1 | VPN notifier tests | 5 | High | -- | 6.1 | -- |
| 7.2 | Repo tests | 5 | High | -- | 6.2 | -- |

---

## 11. Estimated Timeline

| Phase | Description | Effort | Priority |
|-------|-------------|--------|----------|
| **Phase 1** | Security Critical | 3-5 days | P0 (pre-release blocker) |
| **Phase 2** | Architecture Critical | 5-7 days | P1 (first sprint) |
| **Phase 3** | High Priority Fixes | 5-7 days | P2 (first sprint) |
| **Phase 4** | State & Model Consistency | 5-7 days | P2 (second sprint) |
| **Phase 5** | Testing & Quality | 5-7 days | P3 (second sprint) |
| **Phase 6** | Polish & Debt | 3-5 days | P4 (ongoing) |
| **Total** | | **26-38 days** | |

Phases 2 and 3 can partially overlap. Phase 5 can run in parallel with Phase 4.

---

## 12. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Critical issues | 11 | 0 |
| High issues | 18 | 0 |
| `flutter analyze` errors | 0 | 0 |
| Presentation layer data imports | 14 | 0 |
| Use cases actually called | 2/12 | 12/12 |
| Hardcoded English strings | ~30 | 0 |
| VPN notifier test coverage | 0% | 80%+ |
| Certificate pinning | Disabled | Active (staging + prod) |
| Sentry crash reporting | Disabled | Active (staging + prod) |

---

*PRD generated from 3-perspective Flutter audit: Flutter Expert (42 issues), Senior Flutter Architect (42 issues), Flutter Developer (35 issues). Deduplicated to 83 unique issues.*
