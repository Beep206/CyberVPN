# PRD: CyberVPN Mobile — Quality & Security Hardening

**Version:** 1.0
**Date:** 2026-02-07
**Status:** Draft
**Authors:** 5-skill parallel audit (Senior Flutter, Flutter Expert, Flutter Dev, Dart Expert, Mobile Security)

---

## 1. Executive Summary

This PRD consolidates findings from five independent, parallel audits of the CyberVPN mobile Flutter application. Each audit evaluated the codebase from a distinct specialty lens — architecture, patterns/best-practices, development quality, Dart code quality, and mobile security. The goal is to produce a prioritized, actionable remediation plan.

### Audit Scores

| Audit | Grade | Score | Auditor Focus |
|-------|-------|-------|---------------|
| Senior Flutter Architecture | B+ | 85/100 | FSD structure, Riverpod, navigation, error handling, DI |
| Flutter Expert Patterns | B+ | 85/100 | Widget arch, async, performance, data layer, testing |
| Flutter Dev General | A | 90/100 | Build/deps, UI/UX, i18n, CI/CD, feature completeness |
| Dart Expert Code Quality | B+ | 85/100 | Type safety, idioms, error handling, collections, memory |
| Mobile Security | HIGH risk | — | Auth/tokens, network, data protection, VPN, platform |

**Composite Assessment:** The codebase is architecturally sound with excellent i18n (27 locales), clean FSD structure, and strong Riverpod patterns. The primary risks are **4 CRITICAL security vulnerabilities**, a **God class** (798 lines), **silent error swallowing** (31 instances), and **missing certificate pinning enforcement** for production.

### Finding Distribution

| Severity | Count | Source Audits |
|----------|-------|---------------|
| CRITICAL | 4 | Security |
| HIGH | 12 | Security (8), Architecture (2), Patterns (2) |
| MEDIUM | 28 | All audits |
| LOW | 11 | All audits |
| **Total** | **55** | |

---

## 2. Background & Context

CyberVPN Mobile is a Flutter-based VPN client targeting Android and iOS. Key facts:

- **Flutter SDK:** ^3.10.8, **Riverpod:** 3.2.1, **GoRouter:** 17.0.0
- **Architecture:** Feature-Sliced Design + Clean Architecture (data → domain → presentation)
- **Features:** 11 feature modules, 140 Riverpod providers, 22+ repositories
- **Tests:** 158 test files, 2506+ test cases, 70% coverage target
- **i18n:** 27 locales including RTL (Arabic, Farsi, Hebrew)
- **VPN:** Xray-core via `flutter_v2ray_plus` (VLESS, VMess, Trojan, Shadowsocks)

The app completed a 136-task quality remediation (Phases 1-6) immediately prior to this audit. This PRD addresses remaining findings not covered by that remediation.

---

## 3. Goals

1. **Eliminate all CRITICAL security vulnerabilities** before production release
2. **Reduce HIGH findings to zero** within 1 month
3. **Improve composite audit score to A (90+)** across all dimensions
4. **Establish automated security gates** in CI/CD pipeline
5. **Reduce technical debt** (God class, God file, silent error swallowing)

### Non-Goals

- Full rewrite of any feature module
- Riverpod 3.x codegen migration (deferred per `riverpod-strategy.md`)
- iOS-specific native code audit (separate scope)
- Backend API implementation (separate PRD)

---

## 4. Findings & Remediation Tasks

### Phase 1: CRITICAL Security (P0 — Before Production)

These 4 findings represent immediate security risks that block production release.

#### 1.1 Plaintext Password Storage in Biometric Credentials

**Severity:** CRITICAL
**Source:** Mobile Security Audit (C-1.1)
**Files:**
- `lib/core/storage/secure_storage.dart:265-296` — stores `{email, password}` as JSON
- `lib/features/auth/presentation/providers/biometric_login_provider.dart:196-199` — replays password

**Problem:** Biometric login stores user password in plaintext JSON within SecureStorage. If device is compromised (rooted, backup extraction, malware), the password is exposed directly.

**Remediation:**
1. Implement device-bound token authentication flow:
   - On biometric enrollment: call `POST /mobile/auth/biometric/enroll` → receive device token
   - Store device token (not password) in SecureStorage
   - On biometric login: send device token to `POST /mobile/auth/biometric/login`
2. Add migration function `migrateCredentialFormat()` that:
   - Reads existing plaintext credentials
   - Enrolls device token with backend
   - Replaces plaintext credentials with device token
   - Deletes old `biometricCredentialsKey`
3. Call migration on app startup (idempotent)
4. Remove deprecated `setBiometricCredentials()` / `getBiometricCredentials()` methods
5. Make `_setBiometricCredentialsDeprecated` private immediately

**Acceptance Criteria:**
- [ ] No plaintext passwords stored anywhere in SecureStorage
- [ ] Biometric login uses device-bound token
- [ ] Migration function converts existing users
- [ ] Old methods throw `UnsupportedError` or are removed

---

#### 1.2 Certificate Pinning Disabled by Default in Production

**Severity:** CRITICAL
**Source:** Mobile Security Audit (C-2.1, C-2.2)
**Files:**
- `lib/core/network/api_client.dart:40-64` — pinning only active if `CERT_FINGERPRINTS` non-empty
- `lib/core/config/environment_config.dart:65-72` — default is empty string
- `lib/core/security/certificate_pinner.dart:59-70` — bypassed in debug mode
- `.env.example:29` — `CERT_FINGERPRINTS=` (empty)

**Problem:** Production builds ship without certificate pinning if `CERT_FINGERPRINTS` is not set via `--dart-define`. A VPN app without cert pinning is vulnerable to MITM attacks — total compromise of credentials and traffic metadata.

**Remediation:**
1. Add build-time assertion in `api_client.dart`:
   ```dart
   if (EnvironmentConfig.isProd && fingerprints.isEmpty) {
     throw StateError('Certificate pinning REQUIRED for production builds');
   }
   ```
2. Add CI check in `mobile-release.yml` that verifies `CERT_FINGERPRINTS` is non-empty for release builds
3. Extract production certificate fingerprints and store as GitHub secret
4. Add `--dart-define=ENABLE_CERT_PINNING=true` flag for testing pinning in debug mode
5. Document fingerprint rotation procedure in `docs/security/CERTIFICATE_PINNING_ROTATION.md` (already exists, verify completeness)
6. Include current + backup certificate fingerprints

**Acceptance Criteria:**
- [ ] Production builds fail if `CERT_FINGERPRINTS` is empty
- [ ] CI validates pinning configuration on release
- [ ] At least 2 fingerprints configured (primary + backup)
- [ ] Debug mode has opt-in pinning via flag

---

#### 1.3 JWT Tokens Leaked via Logging to Sentry

**Severity:** CRITICAL
**Source:** Mobile Security Audit (C-1.2), Dart Audit (silent error swallowing)
**Files:**
- `lib/core/network/api_client.dart:187-228` — `_RedactedLogInterceptor` incomplete
- `lib/core/utils/app_logger.dart:112, 236-251` — breadcrumbs include `data` field
- `lib/main.dart:72-86` — Sentry init without `beforeBreadcrumb`

**Problem:** The `_RedactedLogInterceptor` redacts auth headers but response bodies for non-sensitive endpoints are passed as `null` (not actively redacted). AppLogger sends `data` field to Sentry breadcrumbs, which may contain tokens, emails, or device IDs.

**Remediation:**
1. Update `_RedactedLogInterceptor.onResponse` to never log response bodies:
   ```dart
   data: {'status': response.statusCode},  // Never include body
   ```
2. Add `beforeBreadcrumb` callback in Sentry init:
   ```dart
   options.beforeBreadcrumb = (breadcrumb, {hint}) {
     var message = breadcrumb?.message;
     if (message != null) {
       message = message.replaceAll(RegExp(r'[\w\.-]+@[\w\.-]+\.\w+'), '***@***.***');
       message = message.replaceAll(RegExp(r'[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}'), '***');
       message = message.replaceAll(RegExp(r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'), '***JWT***');
     }
     return breadcrumb?.copyWith(message: message);
   };
   ```
3. Remove `data` parameter from all auth-related AppLogger calls
4. Add unit test that verifies no JWT patterns in Sentry breadcrumbs

**Acceptance Criteria:**
- [ ] No response bodies logged for any endpoint
- [ ] Sentry breadcrumbs sanitize emails, UUIDs, and JWTs
- [ ] Unit test validates sanitization patterns

---

#### 1.4 SecureStorage Cache Not Cleared on Logout

**Severity:** CRITICAL
**Source:** Mobile Security Audit (H-3.2)
**Files:**
- `lib/core/storage/secure_storage.dart:27-98, 361-378` — `clearAll()` doesn't call `invalidateCache()`
- `lib/features/auth/presentation/providers/logout_provider.dart:127-133` — logout clears keys individually

**Problem:** The in-memory `_cache` map in SecureStorageWrapper retains tokens after `clearAll()`. A memory dump post-logout would reveal the previous user's tokens.

**Remediation:**
1. Add `invalidateCache()` call at the start of `clearAll()`:
   ```dart
   Future<void> clearAll() async {
     invalidateCache();  // Clear memory first
     final deviceId = await read(key: deviceIdKey);
     // ... existing deletion logic
   }
   ```
2. Also clear AppLogger ring buffer on logout:
   ```dart
   AppLogger.clearLogs();  // Prevent log-based PII leakage
   ```
3. Verify `_clearAuthTokens()` in `LogoutNotifier` also invalidates cache

**Acceptance Criteria:**
- [ ] `clearAll()` calls `invalidateCache()` before storage operations
- [ ] AppLogger buffer cleared on logout
- [ ] Unit test verifies cache is empty after `clearAll()`

---

### Phase 2: HIGH Priority Architecture & Security (P1 — Week 1-2)

#### 2.1 God Class: VpnConnectionNotifier (798 lines, 9 responsibilities)

**Severity:** HIGH
**Source:** Architecture Audit, Dart Audit
**File:** `lib/features/vpn/presentation/providers/vpn_connection_notifier.dart`

**Problem:** Single class handles VPN state, network monitoring, WebSocket events, auto-reconnect, kill switch, device registration, review prompts, lifecycle observation, and persistence. Violates SRP, hard to test and maintain.

**Remediation:** Extract into 5 focused services:

| New Service | Responsibility | Lines to Extract |
|---|---|---|
| `VpnConnectionNotifier` (keep) | State transitions: connect/disconnect | Core ~200 lines |
| `VpnNetworkMonitor` | Network change handling | Lines 302-320 |
| `VpnWebSocketListener` | WebSocket event handling | Lines 579-617 |
| `VpnPersistenceService` | Last-connected server, config storage | Lines 543-575 |
| `VpnLifecycleReconciler` | App resume/background handling | Lines 710-766 |

Each extracted service should be a separate Riverpod provider. `VpnConnectionNotifier` orchestrates via `ref.watch`/`ref.listen`.

**Acceptance Criteria:**
- [ ] No file exceeds 300 lines
- [ ] Each service has dedicated unit tests
- [ ] VPN connect/disconnect flow unchanged
- [ ] All existing tests pass

---

#### 2.2 God File: providers.dart (512 lines, 62 providers)

**Severity:** HIGH
**Source:** Architecture Audit
**File:** `lib/core/di/providers.dart`

**Problem:** All 62 DI providers in a single file. Causes merge conflicts, hard navigation, and SRP violation.

**Remediation:** Split by domain:

```
core/di/
├── providers.dart                    # Re-exports all (barrel file)
├── infrastructure_providers.dart     # Dio, ApiClient, Storage, Network (~15 providers)
├── auth_providers.dart               # Auth repo, use cases, providers (~12 providers)
├── vpn_providers.dart                # VPN repo, use cases, services (~10 providers)
├── server_providers.dart             # Server repo, ping, favorites (~8 providers)
├── subscription_providers.dart       # Subscription, RevenueCat (~6 providers)
├── profile_providers.dart            # Profile, devices, 2FA (~6 providers)
└── misc_providers.dart               # Remaining (notifications, diagnostics, etc.)
```

**Acceptance Criteria:**
- [ ] Each file ≤ 120 lines
- [ ] `providers.dart` only contains `export` statements
- [ ] No import changes needed in consuming code (barrel file handles it)
- [ ] All existing tests pass

---

#### 2.3 Silent Error Swallowing (31 instances of `catch (_)`)

**Severity:** HIGH
**Source:** Dart Audit, Architecture Audit
**Key Files:**
- `lib/core/routing/deep_link_parser.dart:228, 295, 391, 521`
- `lib/core/security/app_attestation.dart:139, 312`
- `lib/features/servers/data/datasources/ping_service.dart:61`
- `lib/features/auth/data/repositories/auth_repository_impl.dart:108-109, 127-129`

**Problem:** 31 `catch (_)` blocks silently swallow exceptions with no logging. In security-critical code (attestation, auth), this hides real failures.

**Remediation:**
1. Replace all `catch (_)` with typed catches + logging:
   ```dart
   } catch (e, st) {
     AppLogger.warning('URI parse failed', error: e, stackTrace: st);
     return null;
   }
   ```
2. In `auth_repository_impl.dart`, distinguish between network errors and bugs:
   ```dart
   } on AppException catch (e) {
     AppLogger.info('Logout API failed (offline OK)', error: e);
   } catch (e, st) {
     AppLogger.error('Unexpected logout error', error: e, stackTrace: st);
   }
   ```
3. Add lint rule to prevent future `catch (_)`:
   ```yaml
   # analysis_options.yaml
   linter:
     rules:
       - avoid_catches_without_on_clauses: true  # Or custom lint
   ```

**Acceptance Criteria:**
- [ ] Zero instances of `catch (_)` in codebase
- [ ] All catch blocks include `AppLogger` call
- [ ] Lint rule prevents reintroduction

---

#### 2.4 Sentry PII Leakage

**Severity:** HIGH
**Source:** Mobile Security Audit (H-3.1)
**File:** `lib/main.dart:72-86`

**Problem:** `sendDefaultPii = false` is insufficient. AppLogger breadcrumbs, HTTP data, and error messages may contain emails, device IDs, and tokens.

**Remediation:** (Partially addressed in 1.3) Additionally:
1. Add `beforeSend` callback to strip PII from event exceptions:
   ```dart
   options.beforeSend = (event, {hint}) {
     return event.copyWith(
       exceptions: event.exceptions?.map((e) => e.copyWith(
         value: _sanitizePii(e.value),
       )).toList(),
     );
   };
   ```
2. Add Sentry test event in CI to verify no PII leaks

**Acceptance Criteria:**
- [ ] `beforeSend` and `beforeBreadcrumb` callbacks implemented
- [ ] Integration test sends mock event and verifies sanitization

---

#### 2.5 Token Refresh Race Condition on Cold Start

**Severity:** HIGH
**Source:** Mobile Security Audit (H-1.4), Flutter Expert Audit
**Files:**
- `lib/core/auth/token_refresh_scheduler.dart:35-58` — `unawaited(_triggerRefresh())`
- `lib/core/network/auth_interceptor.dart:88-96` — no mutex on `_isRefreshing`

**Problem:** On cold start, `scheduleRefresh()` triggers refresh with `unawaited()`, meaning the auth provider may issue API calls with an expired token before refresh completes. Additionally, `_isRefreshing` flag lacks mutex protection — concurrent 401s can trigger multiple refresh attempts.

**Remediation:**
1. Make expired-token refresh blocking in `scheduleRefresh()`:
   ```dart
   if (payload.isExpired) {
     await _triggerRefresh();  // Block until refreshed
     return;
   }
   ```
2. Add `Completer`-based mutex to `AuthInterceptor`:
   ```dart
   Completer<void>? _refreshCompleter;

   Future<void> _handleRefresh() async {
     if (_refreshCompleter != null) {
       await _refreshCompleter!.future;
       return;
     }
     _refreshCompleter = Completer<void>();
     try {
       await _performRefresh();
       _refreshCompleter!.complete();
     } catch (e) {
       _refreshCompleter!.completeError(e);
     } finally {
       _refreshCompleter = null;
     }
   }
   ```
3. Add circuit breaker after 3 consecutive failures

**Acceptance Criteria:**
- [ ] No API calls made with expired token on cold start
- [ ] Concurrent 401s result in single refresh call
- [ ] Circuit breaker stops retries after 3 failures

---

#### 2.6 HTTP Allowed in Non-Production Environments

**Severity:** HIGH
**Source:** Mobile Security Audit (H-2.3)
**Files:**
- `lib/core/network/api_client.dart:19-30`
- `android/app/build.gradle.kts`

**Problem:** HTTPS enforcement only checks `isProd`. Staging environment credentials could be sent over cleartext.

**Remediation:**
1. Only allow HTTP for `localhost` and emulator IPs:
   ```dart
   if (!resolvedBaseUrl.startsWith('https://')) {
     final uri = Uri.parse(resolvedBaseUrl);
     final isLocal = uri.host == 'localhost' || uri.host == '10.0.2.2' || uri.host == '127.0.0.1';
     if (!isLocal) {
       throw StateError('Non-local HTTP endpoints are forbidden: $resolvedBaseUrl');
     }
   }
   ```
2. Add Android `network_security_config.xml`:
   ```xml
   <network-security-config>
     <base-config cleartextTrafficPermitted="false" />
     <domain-config cleartextTrafficPermitted="true">
       <domain includeSubdomains="true">localhost</domain>
       <domain includeSubdomains="true">10.0.2.2</domain>
     </domain-config>
   </network-security-config>
   ```
3. Reference in `AndroidManifest.xml`

**Acceptance Criteria:**
- [ ] Only localhost/emulator allowed over HTTP
- [ ] Android network security config enforces HTTPS
- [ ] Staging uses HTTPS only

---

#### 2.7 WebSocket Deprecated Token Auth & Race Condition

**Severity:** HIGH
**Source:** Mobile Security Audit (H-1.3, H-2.4)
**File:** `lib/core/network/websocket_client.dart:226-229, 261-272`

**Problem:** Deprecated `tokenProvider` parameter still accepted (puts JWT in URL). `connect()` has race condition allowing duplicate connections.

**Remediation:**
1. Remove `tokenProvider` parameter entirely (breaking change OK)
2. Add `_isConnecting` guard with `Completer`
3. Add assertion: `assert(ticketProvider != null)`

**Acceptance Criteria:**
- [ ] `tokenProvider` parameter removed
- [ ] Concurrent `connect()` calls deduplicated
- [ ] No JWT tokens appear in WebSocket URLs

---

#### 2.8 VPN Config Credentials Stored Without Additional Encryption

**Severity:** HIGH
**Source:** Mobile Security Audit (H-4.1)
**File:** `lib/features/vpn/data/datasources/xray_config_generator.dart:1-69`

**Problem:** VPN UUIDs (effectively passwords for VPN access) stored in app sandbox. On rooted devices, these can be extracted.

**Remediation:**
1. Encrypt VPN config UUIDs with a key derived from user's auth token hash
2. Add HMAC signature to imported configs for integrity verification
3. Implement server-side config management (fetch on-demand with short-lived tokens)
4. Show warning when importing unsigned configs from QR codes

**Acceptance Criteria:**
- [ ] VPN UUIDs encrypted at rest with user-derived key
- [ ] Config integrity verified via HMAC before use
- [ ] Warning shown for unsigned QR imports

---

### Phase 3: MEDIUM Priority — Architecture & Quality (P2 — Week 2-4)

#### 3.1 Large build() Methods & Missing Widget Decomposition

**Source:** Flutter Expert Audit
**Files:**
- `lib/features/servers/presentation/screens/server_list_screen.dart:252-527` — 275-line `_buildBody()`
- `lib/app/router/app_router.dart` — 722 lines

**Tasks:**
- [ ] Extract `_SearchBar`, `_FastestServerChip`, `_FavoritesSection`, `_ServerGroupList` widgets from `server_list_screen.dart`
- [ ] Split `app_router.dart` into `auth_routes.dart`, `shell_routes.dart`, `deep_link_routes.dart`, `transition_builders.dart`
- [ ] Add `ValueKey(server.id)` to `ServerCard` in all dynamic lists

---

#### 3.2 Expensive Operations in build()

**Source:** Flutter Expert Audit, Dart Audit
**File:** `lib/features/servers/presentation/screens/server_list_screen.dart:216-246`

**Tasks:**
- [ ] Memoize `_getMergedGroupedServers()` — currently called every rebuild
- [ ] Move filtering logic to provider (computed provider with `select()`)
- [ ] Add missing server list pagination for 500+ server scalability

---

#### 3.3 Generic Exception Handlers (39 instances)

**Source:** Dart Audit
**Files:** Multiple repositories and providers

**Tasks:**
- [ ] Replace `catch (e, st)` with typed catches in top 15 critical methods:
  ```dart
  } on DioException catch (e) {
    // Network error — maybe retry
  } on AppException catch (e) {
    // Known app error — map to failure
  } catch (e, st) {
    // Unexpected — report to Sentry
  }
  ```
- [ ] Add missing fallback `catch (e)` in `referral_repository_impl.dart` (`isAvailable`, `getRecentReferrals`)

---

#### 3.4 Force Unwraps (50 instances)

**Source:** Dart Audit
**Files:**
- `lib/features/vpn/presentation/providers/vpn_connection_notifier.dart:218`
- `lib/core/utils/performance_profiler.dart:67`

**Tasks:**
- [ ] Replace `response.data!` with null check + early return pattern
- [ ] Replace `_endTime!` with state validation before computation
- [ ] Audit and fix remaining 48 force unwraps

---

#### 3.5 Missing Test Coverage Gaps

**Source:** Flutter Expert Audit, Flutter Dev Audit
**Current:** ~70% coverage target, but missing:

**Tasks:**
- [ ] Add widget tests for `ConnectionScreen`, `LoginScreen`, `ServerListScreen`
- [ ] Add golden tests (golden_toolkit dependency exists but unused)
- [ ] Add integration tests for auth flow and VPN connection flow
- [ ] Target 80% coverage in domain layer, 70% overall

---

#### 3.6 Router Error Handling

**Source:** Architecture Audit
**File:** `lib/app/router/app_router.dart:189-293`

**Tasks:**
- [ ] Wrap redirect logic in try-catch with fallback route:
  ```dart
  redirect: (context, state) {
    try {
      // ... existing logic
    } catch (e, st) {
      AppLogger.error('Router redirect failed', error: e, stackTrace: st);
      return '/error';
    }
  }
  ```
- [ ] Add `/error` route with retry button

---

#### 3.7 Provider Scoping Opportunities

**Source:** Architecture Audit
**File:** `lib/core/di/providers.dart`

**Tasks:**
- [ ] Convert server detail provider to `.family` (parameterized by server ID)
- [ ] Scope subscription providers to subscription feature
- [ ] Document scoping decisions in provider file headers

---

#### 3.8 Automated Dependency Scanning

**Source:** Mobile Security Audit (M-7.1)
**File:** `.github/workflows/mobile-ci.yml`

**Tasks:**
- [ ] Add `flutter pub audit` step to CI pipeline
- [ ] Create `.github/dependabot.yml` for pub ecosystem:
  ```yaml
  version: 2
  updates:
    - package-ecosystem: "pub"
      directory: "/cybervpn_mobile"
      schedule:
        interval: "weekly"
  ```
- [ ] Pin exact versions for production builds

---

#### 3.9 iOS CI/CD Parity

**Source:** Flutter Dev Audit
**File:** `.github/workflows/mobile-release.yml`

**Tasks:**
- [ ] Add `build-ios-release` job to release workflow
- [ ] Add iOS simulator testing to CI workflow
- [ ] Set up TestFlight deployment automation
- [ ] Add Podfile to version control (if not dynamically generated)

---

#### 3.10 Unbounded In-Memory Caches

**Source:** Dart Audit
**Files:**
- `lib/features/servers/data/datasources/ping_service.dart:27` — `Map<String, int> _cache`
- `lib/core/storage/secure_storage.dart:32-35` — `Map<String, String?> _cache`

**Tasks:**
- [ ] Implement LRU eviction with max size (1000 entries)
- [ ] Add TTL for cached SecureStorage values (5 min for tokens)
- [ ] Clear ping cache when server list refreshes

---

### Phase 4: MEDIUM Priority — Security Hardening (P2 — Week 2-4)

#### 4.1 Refresh Token Rotation

**Source:** Mobile Security Audit (M-1.5)
**File:** `lib/core/network/auth_interceptor.dart:119-125`

**Tasks:**
- [ ] Enforce mandatory refresh token rotation (fail if backend returns null)
- [ ] Document backend requirement for rotation
- [ ] Add detection for concurrent refresh token usage (sign of theft)

---

#### 4.2 AppLogger Ring Buffer PII

**Source:** Mobile Security Audit (M-3.3)
**File:** `lib/core/utils/app_logger.dart:83-98`

**Tasks:**
- [ ] Clear ring buffer on logout
- [ ] Reduce buffer size from 1000 to 500
- [ ] Add PII sanitization before buffer insertion
- [ ] Encrypt exported logs

---

#### 4.3 DNS Leak Protection Verification

**Source:** Mobile Security Audit (M-4.3)
**File:** `lib/features/vpn/data/datasources/xray_config_generator.dart:16-17`

**Tasks:**
- [ ] Implement DNS leak test on VPN connection
- [ ] Add periodic leak checks while connected
- [ ] Alert user if DNS leak detected
- [ ] Add DoH/DoT option in VPN settings

---

#### 4.4 Kill Switch Verification

**Source:** Mobile Security Audit (H-4.2)
**File:** `lib/features/vpn/data/datasources/kill_switch_android.dart:1-36`

**Tasks:**
- [ ] Add kill switch verification method (attempt HTTP request, expect failure)
- [ ] Periodically verify kill switch is active while connected
- [ ] Alert user if kill switch fails to enable
- [ ] Audit native Android/iOS kill switch implementations (separate scope)

---

#### 4.5 QR Config Signature Verification

**Source:** Mobile Security Audit (M-4.4)
**File:** `lib/features/config_import/presentation/screens/qr_scanner_screen.dart:100-113`

**Tasks:**
- [ ] Implement HMAC-signed config format for official CyberVPN configs
- [ ] Verify signature before importing
- [ ] Show "Unverified Config" warning for unsigned imports
- [ ] Add trusted CA for config signing

---

#### 4.6 ProGuard Rules Tightening

**Source:** Mobile Security Audit (M-5.1)
**File:** `android/app/proguard-rules.pro`

**Tasks:**
- [ ] Replace `{ *; }` with specific keeps:
  ```proguard
  -keep class com.wisecodex.flutter_v2ray.** { public *; native <methods>; }
  ```
- [ ] Use `-printusage` to identify unused kept code
- [ ] Test thoroughly after narrowing rules

---

#### 4.7 BuildConfig URL Obfuscation

**Source:** Mobile Security Audit (M-5.4)
**File:** `android/app/build.gradle.kts:82-115`

**Tasks:**
- [ ] Move Sentry DSN to remote config (fetch on first launch)
- [ ] Obfuscate API URLs with runtime string decryption
- [ ] Add ProGuard rule to strip BuildConfig:
  ```proguard
  -assumenosideeffects class **.BuildConfig { *; }
  ```

---

#### 4.8 Email Validation Hardening

**Source:** Mobile Security Audit (M-6.1)
**File:** `lib/core/utils/input_validators.dart:19-21`

**Tasks:**
- [ ] Add punycode/IDN homograph detection
- [ ] Add password max length (72 bytes for bcrypt)
- [ ] Whitelist common TLDs for non-enterprise users

---

#### 4.9 Debug Build Detection & Warning

**Source:** Mobile Security Audit (M-5.3)
**File:** `lib/main.dart:92`

**Tasks:**
- [ ] Add `Banner(message: 'DEBUG')` widget in debug mode
- [ ] Show one-time dialog on first debug launch
- [ ] Add watermark to screenshots in debug mode

---

### Phase 5: LOW Priority — Polish & Consistency (P3 — Month 2)

#### 5.1 Overuse of `late final` (264 instances)

**Source:** Dart Audit
**Task:** Refactor extracted services (from 2.1) to use constructor injection instead of `late final` initialized in `build()`.

---

#### 5.2 Missing `const` Constructors (~15% of widgets)

**Source:** Dart Audit
**Task:** Add `const` to simple widget constructors for rebuild performance.

---

#### 5.3 Provider Documentation (54 of 62 lack doc comments)

**Source:** Architecture Audit
**Task:** Add dartdoc comments to all public providers in `core/di/`.

---

#### 5.4 Inconsistent Directory Naming

**Source:** Architecture Audit
**Task:** Standardize on plural directory names (`datasources/`, `repositories/`, `usecases/`).

---

#### 5.5 Missing Failure Serialization

**Source:** Architecture Audit
**File:** `lib/core/errors/failures.dart`
**Task:** Add `toJson()` to Failure subtypes for structured error telemetry.

---

#### 5.6 Test Structure Migration

**Source:** Architecture Audit
**Task:** Complete migration of 28 remaining test files from `test/unit/` and `test/widget/` to `test/features/` structure.

---

#### 5.7 Responsive Tablet Layouts

**Source:** Flutter Dev Audit
**Tasks:**
- [ ] Landscape mode for connection screen
- [ ] Responsive grid for subscription plans (2-3 columns on tablets)
- [ ] Verify existing NavigationRail + master-detail works across devices

---

#### 5.8 Missing StreamController Cleanup

**Source:** Dart Audit
**File:** `lib/features/vpn/data/datasources/vpn_notification_service.dart:198-199`
**Task:** Replace `.close()` with `.cancel()` for StreamSubscriptions.

---

#### 5.9 Isolate Usage for Heavy Computation

**Source:** Dart Audit
**Task:** Consider `compute()` for large JSON parsing and JWT validation.

---

#### 5.10 No Certificate Transparency Validation

**Source:** Mobile Security Audit (M-2.6)
**Task:** Document reliance on platform CT enforcement. Monitor CT logs for `api.cybervpn.com`.

---

## 5. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| CRITICAL findings | 4 | 0 | Security re-audit |
| HIGH findings | 12 | 0 | Security re-audit |
| MEDIUM findings | 28 | ≤ 10 | Code review |
| `catch (_)` instances | 31 | 0 | `grep -r "catch (_)" lib/` |
| Largest file (lines) | 798 | ≤ 300 | `wc -l` |
| Test coverage (overall) | ~70% | ≥ 75% | `flutter test --coverage` |
| Test coverage (domain) | ~80% | ≥ 85% | Coverage report |
| Provider doc coverage | 13% | ≥ 80% | Automated check |
| CI security scan | None | Pass | `flutter pub audit` |

---

## 6. Timeline

| Phase | Scope | Duration | Blocker? |
|-------|-------|----------|----------|
| **Phase 1** | CRITICAL security (4 tasks) | 3-5 days | **Yes — blocks production** |
| **Phase 2** | HIGH architecture + security (8 tasks) | 1-2 weeks | Soft blocker |
| **Phase 3** | MEDIUM architecture + quality (10 tasks) | 2-3 weeks | No |
| **Phase 4** | MEDIUM security hardening (9 tasks) | 2-3 weeks | No |
| **Phase 5** | LOW polish + consistency (10 tasks) | 2-4 weeks | No |

**Total estimated scope:** 41 tasks across 5 phases.

---

## 7. Dependencies & Risks

### Backend Dependencies

| Task | Backend Requirement |
|------|-------------------|
| 1.1 Biometric device token | `POST /mobile/auth/biometric/enroll` and `/login` endpoints |
| 1.2 Certificate pinning | Production SSL certificate fingerprints |
| 4.1 Refresh token rotation | Backend must always return new refresh token |
| 2.8 Server-side config mgmt | Config fetch API with short-lived tokens |

### Risks

| Risk | Mitigation |
|------|-----------|
| Backend endpoints not ready for Phase 1 | Implement client-side with feature flag, enable when backend ready |
| Certificate rotation breaks pinning | Include backup fingerprint, implement graceful fallback |
| VpnConnectionNotifier refactor breaks VPN | Comprehensive test coverage before refactoring |
| ProGuard tightening breaks native plugins | Incremental changes with CI validation |

---

## 8. Appendix: Files Referenced

### Critical Files (Must Read)

| File | Lines | Relevance |
|------|-------|-----------|
| `lib/core/storage/secure_storage.dart` | 378 | Token storage, cache, biometric credentials |
| `lib/core/network/api_client.dart` | 228 | HTTP client, cert pinning, logging |
| `lib/core/network/auth_interceptor.dart` | 210 | Token refresh, 401 handling, race conditions |
| `lib/core/security/certificate_pinner.dart` | 160 | TLS pinning, debug bypass |
| `lib/features/vpn/presentation/providers/vpn_connection_notifier.dart` | 798 | God class — VPN state management |
| `lib/core/di/providers.dart` | 512 | God file — all DI providers |
| `lib/core/utils/app_logger.dart` | 251 | Logging, ring buffer, Sentry breadcrumbs |
| `lib/main.dart` | ~180 | App init, Sentry config, deferred services |
| `lib/app/router/app_router.dart` | 722 | Navigation, deep links, redirect guards |
| `lib/core/config/environment_config.dart` | 224 | Build config, cert fingerprints, env vars |

### Audit Reports (Full Details)

| Audit | Output Location |
|-------|----------------|
| Senior Flutter Architecture | Agent a42f2a0 |
| Flutter Expert Patterns | Agent a9b8d7a |
| Flutter Dev General | Agent ab1d045 |
| Dart Expert Code Quality | Agent aa93637 |
| Mobile Security | Agent aad6029 |
