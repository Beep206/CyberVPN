
# PRD: CyberVPN Mobile App Improvements

**Version**: 1.0
**Date**: 2026-02-06
**Author**: CTO / Mobile Architecture Review
**Status**: Draft

---

## 1. Executive Summary

CyberVPN Mobile is a production-grade Flutter VPN client with Clean Architecture, Riverpod state management, 27 locales, and 16 features. The codebase demonstrates strong engineering fundamentals: sealed classes, freezed entities, certificate pinning, biometric auth, and comprehensive error handling.

This PRD identifies **architectural debt, Dart/Flutter anti-patterns, and strategic gaps** discovered during a deep analysis using dart-expert and flutter-development assessment frameworks. Recommendations are prioritized by impact and risk.

---

## 2. Current State Assessment

### 2.1 Strengths (Keep)

| Area | Details |
|------|---------|
| **Architecture** | Clean Architecture with Feature-Sliced Design, proper layer separation |
| **Type Safety** | Strict analyzer rules (strict-casts, strict-raw-types, strict-inference), freezed entities, sealed classes for state |
| **Security** | Certificate pinning, SecureStorage for credentials, jailbreak detection, biometric enrollment change detection, screen protection |
| **Error Handling** | Layered exceptions -> failures mapping, NetworkErrorHandler mixin with retry + backoff, rate-limit parsing |
| **VPN Connection** | Sealed state machine (VpnConnectionState), auto-reconnect, kill switch, DNS resolution, force disconnect via WebSocket |
| **Observability** | Sentry integration, structured logging (AppLogger), Firebase Analytics abstraction, performance profiling |
| **Testing** | 95+ test files covering unit, widget, integration, and E2E layers |
| **Deferred Init** | Firebase and FCM initialization deferred to post-first-frame for fast cold start |

### 2.2 Risk Matrix

| Risk | Severity | Probability | Impact |
|------|----------|-------------|--------|
| DI Boilerplate Explosion | Medium | High | Maintenance burden grows with every new feature |
| Missing Either/Result in Repositories | High | High | Exceptions leak across layer boundaries |
| No Offline-First Data Layer | High | Medium | VPN app must work reliably with poor connectivity |
| Test Coverage Gaps in Presentation Layer | Medium | High | UI regressions undetected |
| No CI/CD Pipeline for Mobile | Critical | High | Manual builds, no automated quality gates |

---

## 3. Recommendations

### 3.1 CRITICAL: Adopt Result Type Pattern Across Repositories

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

**Recommended pattern**:
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

**Scope**: All 7 repository interfaces + implementations.
**Priority**: P0 (Critical)
**Effort**: ~3 days

---

### 3.2 HIGH: Migrate DI from Manual Overrides to Riverpod Code Generation

**Problem**: `providers.dart` manually creates 30+ provider overrides in `buildProviderOverrides()`, duplicating instantiation logic. Every new repository or data source requires editing this file, the provider declarations, and the override list.

**Current state**: 270 lines of manual wiring in `core/di/providers.dart`, providers scattered across feature files with `throw UnimplementedError()` stubs.

**Recommendation**: Adopt `@riverpod` code generation (already installed as `riverpod_generator` in dev_dependencies but unused).

```dart
@riverpod
AuthRepository authRepository(Ref ref) {
  return AuthRepositoryImpl(
    remoteDataSource: ref.watch(authRemoteDataSourceProvider),
    localDataSource: ref.watch(authLocalDataSourceProvider),
    networkInfo: ref.watch(networkInfoProvider),
  );
}
```

**Benefits**:
- Eliminates `throw UnimplementedError()` stubs
- Auto-generates dispose/keep-alive logic
- Type-safe, compile-time checked dependency graph
- Reduces `providers.dart` from 270 lines to ~30

**Scope**: All providers in `core/di/` and feature `presentation/providers/`.
**Priority**: P1 (High)
**Effort**: ~4 days

---

### 3.3 HIGH: Implement Offline-First Data Layer with Repository Caching Strategy

**Problem**: Most repositories check `_networkInfo.isConnected` and throw immediately on no network. A VPN app's users frequently have degraded connectivity. Server list, user profile, subscription status, and settings should all be available offline.

**Current gap**: `ServerRepositoryImpl` and `SubscriptionRepositoryImpl` have a `localDataSource` but no stale-while-revalidate pattern. `AuthRepositoryImpl.getCurrentUser()` returns `null` on no network with no attempt to refresh from cache.

**Recommendation**: Implement a generic `CachePolicy` abstraction:

```dart
enum CacheStrategy {
  cacheFirst,       // Return cache, refresh in background
  networkFirst,     // Try network, fall back to cache
  cacheOnly,        // Never hit network
  networkOnly,      // Never use cache (sensitive data)
  staleWhileRevalidate, // Return cache immediately, update after
}
```

Apply per-repository:
| Repository | Strategy | TTL |
|-----------|----------|-----|
| ServerRepository | staleWhileRevalidate | 5 min |
| SubscriptionRepository | cacheFirst | 1 hour |
| AuthRepository (user profile) | cacheFirst | 24 hours |
| ReferralRepository | networkFirst | 15 min |
| SettingsRepository | cacheOnly | -- (local) |

**Priority**: P1 (High)
**Effort**: ~5 days

---

### 3.4 HIGH: Establish CI/CD Pipeline for Mobile

**Problem**: No automated build, test, or release pipeline exists. Manual builds are error-prone and slow.

**Recommendation**: GitHub Actions pipeline with:

1. **PR Checks**: `flutter analyze`, `flutter test`, `dart format --set-exit-if-changed`
2. **Build Matrix**: Android (dev, staging, prod flavors) + iOS (Debug, Release)
3. **Code Coverage**: Enforce minimum 70% coverage with `lcov`
4. **Release**: Fastlane for iOS, Gradle for Android, triggered on tag push
5. **Code Signing**: GitHub Secrets for keystore (Android) + Match (iOS)

**Files to create**:
- `.github/workflows/mobile-ci.yml`
- `.github/workflows/mobile-release.yml`
- `cybervpn_mobile/fastlane/Fastfile` (iOS already has skeleton)

**Priority**: P1 (High)
**Effort**: ~3 days

---

### 3.5 MEDIUM: Eliminate Code Duplication in VpnConnectionNotifier

**Problem**: `connect()` and `connectFromCustomServer()` share ~80% identical logic (settings resolution, kill switch, persist, auto-reconnect, device registration, review prompt). Violates DRY.

**Lines affected**: `vpn_connection_provider.dart:238-373` -- two 65-line methods with nearly identical structure.

**Recommendation**: Extract a private `_executeConnection(VpnConfigEntity config, ServerEntity server)` method, call from both public methods. Custom server conversion happens before calling the shared method.

**Priority**: P2 (Medium)
**Effort**: ~2 hours

---

### 3.6 MEDIUM: Add Structured Error Types for User-Facing Messages

**Problem**: Error messages are raw `e.toString()` strings passed to UI. This exposes implementation details (class names, stack traces) and prevents localization.

**Current**:
```dart
catch (e) {
  state = AsyncValue.data(AuthError(e.toString()));
}
```

**Recommendation**: Create an `AppError` enum/sealed class with i18n-ready error codes:

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

**Priority**: P2 (Medium)
**Effort**: ~2 days

---

### 3.7 MEDIUM: Upgrade to Riverpod Annotations Pattern

**Problem**: Mix of legacy `Provider((...) => ...)` and modern `@riverpod` patterns. `BiometricService`, analytics, and utility providers use the legacy syntax. Inconsistency increases onboarding time.

**Current mix**:
- `final authProvider = AsyncNotifierProvider<AuthNotifier, AuthState>()` (manual)
- No `@riverpod` annotations used anywhere despite `riverpod_generator` being installed

**Recommendation**: Adopt `@riverpod` / `@Riverpod(keepAlive: true)` annotations consistently. Run `dart run build_runner build` to generate providers. Benefits: auto-dispose by default, cleaner syntax, no manual NotifierProvider declarations.

**Priority**: P2 (Medium)
**Effort**: ~3 days (incremental migration)

---

### 3.8 MEDIUM: Improve WebSocket Reconnection with Jitter

**Problem**: `WebSocketClient._calculateBackoff()` uses pure exponential backoff without jitter. When the server restarts, all clients reconnect at the same exact intervals, causing a thundering herd.

**Current**: `1s, 2s, 4s, 8s, 16s, 30s` (capped)

**Recommendation**: Add randomized jitter:
```dart
Duration _calculateBackoff() {
  final baseSeconds = _initialBackoff.inSeconds *
      math.pow(_backoffMultiplier, _reconnectAttempt).toInt();
  final capped = math.min(baseSeconds, _maxBackoff.inSeconds);
  final jitter = Random().nextInt(capped ~/ 2 + 1); // 0..50% of delay
  return Duration(seconds: capped + jitter);
}
```

**Priority**: P2 (Medium)
**Effort**: ~30 minutes

---

### 3.9 MEDIUM: Strengthen Test Coverage for Presentation Layer

**Problem**: 95+ tests exist but concentrate on domain/data layers and config parsers. Presentation layer (providers, screens) has limited coverage:
- `VpnConnectionNotifier` -- no dedicated unit tests for the complex state machine
- `AuthNotifier` -- no tests for token refresh scheduling, attestation, FCM registration
- Widget tests cover only 5 screens (`LoginScreen`, `ServerListScreen`, `SettingsScreen`, etc.)

**Recommendation**:
1. Add provider state tests for `VpnConnectionNotifier` (connect, disconnect, reconnect, force-disconnect, auto-connect edge cases)
2. Add provider tests for `AuthNotifier` (login success/failure, logout, token refresh)
3. Add widget tests for `ConnectionScreen`, `ProfileDashboardScreen`, `PlansScreen`
4. Set coverage threshold: 70% overall, 80% for domain layer

**Priority**: P2 (Medium)
**Effort**: ~5 days

---

### 3.10 LOW: Adopt Dart 3 Pattern Matching More Broadly

**Problem**: The codebase uses sealed classes (good) but inconsistently applies Dart 3 pattern matching. Some places use `is` checks, others use `switch` expressions.

**Examples of inconsistent style**:
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

**Recommendation**: Standardize on `switch` expressions for sealed class matching. Add lint rule `unnecessary_type_check` and prefer exhaustive matching. Low effort, improves readability.

**Priority**: P3 (Low)
**Effort**: ~1 day

---

### 3.11 LOW: Remove Equatable from Failure, Use Sealed Classes Instead

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

**Recommendation**: Convert to sealed class + freezed, or at minimum use `@freezed` for automatic equality/hashCode:
```dart
@freezed
sealed class Failure with _$Failure {
  const factory Failure.server({required String message, int? code}) = ServerFailure;
  const factory Failure.network({required String message, int? code}) = NetworkFailure;
  // ...
}
```

**Priority**: P3 (Low)
**Effort**: ~1 day

---

### 3.12 LOW: Address Firebase Analytics Initialization Race Condition

**Problem**: Firebase is initialized in `_initializeDeferredServices()` via `addPostFrameCallback`. However, `AnalyticsService` might be called before Firebase initialization completes (e.g., if auth flow completes before first frame callback fires).

**Recommendation**: Guard analytics calls with an `isInitialized` flag or use a `Completer<void>` pattern:
```dart
class FirebaseAnalyticsImpl implements AnalyticsService {
  final Completer<FirebaseAnalytics> _ready = Completer();

  void markReady(FirebaseAnalytics analytics) => _ready.complete(analytics);

  @override
  Future<void> logEvent(String name, {...}) async {
    final analytics = await _ready.future;
    await analytics.logEvent(name: name, parameters: parameters);
  }
}
```

**Priority**: P3 (Low)
**Effort**: ~2 hours

---

### 3.13 LOW: Add `@immutable` Annotation to Non-Freezed Value Objects

**Problem**: Several manually written classes should be annotated `@immutable` to enforce compile-time immutability checks. Examples:
- `ConnectVpnUseCase` (has `const` constructor but no `@immutable`)
- `VpnDisconnected`, `VpnConnecting`, etc. (manual sealed class hierarchy)
- All `AppException` subclasses

**Recommendation**: Add `@immutable` annotation to all value objects and use cases that don't use freezed.

**Priority**: P4 (Backlog)
**Effort**: ~1 hour

---

## 4. Performance Improvements

### 4.1 Lazy Provider Initialization

**Current**: `buildProviderOverrides()` eagerly creates all repositories and data sources at app startup, even if the user won't visit certain features (diagnostics, referral, config import).

**Recommendation**: Use Riverpod's lazy initialization (default behavior with `@riverpod`). Only `authRepository`, `vpnRepository`, and `secureStorage` need eager initialization.

### 4.2 Server List Pagination

**Current**: Server list is fetched in full. As server count grows, this will impact memory and render time.

**Recommendation**: Implement cursor-based pagination with `FutureProvider.family` and infinite scroll in `ServerListScreen`.

### 4.3 Image/Asset Optimization

**Current**: Country flags in `assets/images/flags/` are likely PNG. With 200+ countries, this adds significant APK size.

**Recommendation**: Use SVG flags via `flutter_svg` (already a dependency) or a flag emoji approach. Compress existing PNGs with `flutter_launcher_icons`-style optimization.

---

## 5. Security Improvements

### 5.1 Token Rotation on Biometric Enrollment Change

**Current**: `BiometricService.hasEnrollmentChanged()` detects changes but the app doesn't enforce credential re-validation.

**Recommendation**: When enrollment changes, invalidate the stored session and require password re-authentication before enabling biometric login again.

### 5.2 Root/Jailbreak Enforcement Policy

**Current**: `DeviceIntegrityChecker` exists but its enforcement policy is unclear from the codebase.

**Recommendation**: Define a clear policy:
- **Logging mode** (current): Log to Sentry, show warning banner
- **Enforcement mode** (future): Prevent VPN connection on rooted devices (configurable via remote config)

### 5.3 Memory-Safe Token Handling

**Current**: JWT tokens exist as Dart `String` objects which remain in memory until GC.

**Recommendation**: Use `SecureStorageWrapper` for all token access, avoid caching tokens as class fields, and call `_storage.delete()` immediately after use in auth interceptor.

---

## 6. UX Improvements

### 6.1 Connection Screen Haptic Feedback

Add haptic feedback (`HapticFeedback.mediumImpact()`) on VPN connect/disconnect button press.

### 6.2 Server Ping Visual Indicators

Current ping values are numeric. Add color-coded indicators:
- Green: < 100ms
- Yellow: 100-200ms
- Red: > 200ms
- Grey: Unavailable

### 6.3 Progressive Onboarding

Current onboarding is a linear flow. Consider:
- Skip button on each page
- Coachmarks for first-time feature discovery (server selection, kill switch)
- Contextual tooltips instead of upfront tutorial

### 6.4 Subscription Expiry Countdown Widget

Home screen widget showing days remaining with color gradient (green -> yellow -> red).

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] 3.1 Result type pattern (P0)
- [ ] 3.4 CI/CD pipeline (P1)
- [ ] 3.8 WebSocket jitter (P2, quick win)

### Phase 2: Architecture (Weeks 3-4)
- [ ] 3.2 Riverpod code generation migration (P1)
- [ ] 3.3 Offline-first data layer (P1)
- [ ] 3.5 VPN connection code dedup (P2, quick win)

### Phase 3: Quality (Weeks 5-6)
- [ ] 3.6 Structured error types (P2)
- [ ] 3.9 Presentation layer test coverage (P2)
- [ ] 3.10 Dart 3 pattern matching standardization (P3)

### Phase 4: Polish (Weeks 7-8)
- [ ] 3.11 Sealed failures (P3)
- [ ] 3.12 Firebase init race condition (P3)
- [ ] 4.1-4.3 Performance optimizations
- [ ] 5.1-5.3 Security hardening
- [ ] 6.1-6.4 UX improvements

---

## 8. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage (overall) | ~45% | 70% |
| Test Coverage (domain) | ~65% | 80% |
| Cold Start Time (Android) | Unmeasured | < 1.5s |
| APK Size | Unmeasured | < 25MB |
| Crash-Free Rate | Unmeasured | > 99.5% |
| Provider Boilerplate (providers.dart) | 270 lines | < 50 lines |
| Repository Error Handling | Exceptions | Result<T> |
| CI Build Time | N/A | < 10 min |

---

## 9. Out of Scope

- Backend API changes (this PRD focuses on mobile client only)
- iOS WidgetKit enhancements (separate PRD)
- macOS/Linux/Windows platform support (placeholder only)
- Redesign of UI theme system (current Material You + Cyberpunk is well-implemented)
- Migration away from flutter_v2ray_plus (works, but vendor-locked)

---

## 10. Appendix: Files Analyzed

### Core
- `lib/main.dart` -- App entry, deferred init, error handlers
- `lib/core/di/providers.dart` -- DI container, 270 lines of overrides
- `lib/core/network/api_client.dart` -- Dio wrapper, cert pinning
- `lib/core/network/websocket_client.dart` -- WS with reconnection
- `lib/core/errors/failures.dart` -- Domain failure hierarchy (Equatable)
- `lib/core/errors/exceptions.dart` -- Infrastructure exception hierarchy
- `lib/core/errors/network_error_handler.dart` -- Retry + backoff mixin
- `lib/core/analytics/analytics_service.dart` -- Analytics abstraction

### Auth Feature
- `lib/features/auth/domain/entities/user_entity.dart` -- freezed entity
- `lib/features/auth/presentation/providers/auth_provider.dart` -- AuthNotifier
- `lib/features/auth/presentation/providers/auth_state.dart` -- Sealed auth states
- `lib/features/auth/data/repositories/auth_repository_impl.dart`
- `lib/features/auth/domain/usecases/biometric_service.dart`

### VPN Feature
- `lib/features/vpn/domain/entities/connection_state_entity.dart` -- freezed
- `lib/features/vpn/presentation/providers/vpn_connection_provider.dart` -- 850 lines
- `lib/features/vpn/data/repositories/vpn_repository_impl.dart` -- Secure config storage
- `lib/features/vpn/domain/usecases/connect_vpn.dart`

### Navigation
- `lib/app/router/app_router.dart` -- GoRouter with guards + deep links
- `lib/app/theme/material_you_theme.dart` -- Theme builder

### Config Import
- `lib/features/config_import/domain/parsers/vpn_uri_parser.dart` -- Sealed parse result

### Configuration
- `pubspec.yaml` -- 50+ dependencies
- `analysis_options.yaml` -- Strict linting, 49 custom rules
