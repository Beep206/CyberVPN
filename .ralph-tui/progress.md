# Progress Log

## Codebase Patterns

### Riverpod State Management
- Use `AsyncNotifier<T>` with `AsyncNotifierProvider` for async state
- Sealed classes (Dart 3) for type-safe state hierarchies instead of freezed
- Create derived providers with `Provider<T>` for computed values like `currentUserProvider` and `isAuthenticatedProvider`
- Override providers in tests using `ProviderContainer` with `overrides`

### Test Patterns
- Use `implements` instead of `extends` for mock classes to avoid super constructor issues
- Create a `waitForState()` helper to await async provider initialization
- Use `container.listen()` before `container.read()` to ensure provider is initialized
- Clean up containers in `tearDown()`

### Auth Provider Structure
- Repository providers that throw `UnimplementedError` must be overridden in `ProviderScope`
- FCM token registration and app attestation run as fire-and-forget async operations after login
- Sentry user context is set on login/register and cleared on logout

### Secure Storage Patterns
- Use `FakeSecureStorage` for testing (in-memory map storage)
- Generate UUID v4 using `Random.secure()` with RFC 4122 variant/version bits
- Return Dart records `({String email, String password})?` for structured nullable returns
- `clearAll()` should preserve device ID for analytics tracking across sessions

---

## 2026-02-04 - VPNBussiness-258.2
- **What was implemented:**
  - Enhanced `SecureStorageWrapper` with high-level convenience methods:
    - Token management: `setTokens()`, `getAccessToken()`, `getRefreshToken()`, `clearTokens()`
    - Device ID: `getOrCreateDeviceId()` generates UUID v4 on first call, persists thereafter
    - Biometric credentials: `setBiometricCredentials()`, `getBiometricCredentials()`, `clearBiometricCredentials()`
    - App lock state: `setAppLockEnabled()`, `isAppLockEnabled()`
    - Cached user: `setCachedUser()`, `getCachedUser()`, `clearCachedUser()`
    - `clearAll()` clears auth data but preserves device ID
  - Updated `FakeSecureStorage` with `seed()` method for test data population
  - Created 31 comprehensive unit tests covering all storage operations

- **Files changed:**
  - `lib/core/storage/secure_storage.dart` - Added convenience methods for token, device ID, biometric, app lock, and cached user management
  - `test/helpers/fakes/fake_secure_storage.dart` - Added `seed()` method for test data
  - `test/core/storage/secure_storage_test.dart` - New file with 31 unit tests
  - `.env` - Created empty file (required for flutter test asset bundle)

- **Learnings:**
  - UUID v4 can be generated without a package using `Random.secure()` with proper RFC 4122 variant/version bits
  - Dart 3 records `({String email, String password})?` are excellent for returning structured nullable data
  - FakeSecureStorage's high-level methods work correctly because they delegate to overridden base methods

---

## 2026-02-04 - VPNBussiness-258.17
- **What was implemented:**
  - Added specific intent-filter for `cybervpn://telegram-auth` deep link in AndroidManifest.xml
  - The generic `cybervpn://` handler (lines 37-43) already catches all custom scheme URLs
  - Added explicit handler (lines 45-53) specifically for `telegram-auth` host pattern
  - Flutter deep linking is already enabled via `flutter_deeplinking_enabled` meta-data

- **Files changed:**
  - `android/app/src/main/AndroidManifest.xml` - Added specific intent-filter for telegram-auth

- **Learnings:**
  - Android intent filters with just `android:scheme="cybervpn"` catch ALL URLs with that scheme
  - Adding `android:host="telegram-auth"` creates a more specific filter for that particular path
  - For custom scheme URIs like `cybervpn://telegram-auth`, the "host" portion becomes the route path in DeepLinkParser
  - Flutter's `flutter_deeplinking_enabled` meta-data must be true for deep links to work
  - The existing DeepLinkParser handles OAuth callbacks via `oauth/callback` route, not `telegram-auth`

- **Note on testing:**
  - Android SDK not available in this environment - manual testing on emulator/device required
  - Deep link testing commands: `adb shell am start -a android.intent.action.VIEW -d "cybervpn://telegram-auth?code=test123"`

---

## 2026-02-04 - VPNBussiness-258.6
- **What was implemented:**
  - Fixed lint warnings in `auth_provider.dart` (unused stack trace variables)
  - Created comprehensive unit tests for `AuthNotifier` and `AuthState` (23 tests total)
  - Tests cover: build() auto-login flow, login(), register(), logout(), checkAuthStatus()
  - Tests cover derived providers: currentUserProvider, isAuthenticatedProvider
  - Created `.env` file (empty) required for Flutter test asset bundle

- **Files changed:**
  - `lib/features/auth/presentation/providers/auth_provider.dart` - Fixed 3 unused_catch_stack warnings
  - `test/features/auth/presentation/providers/auth_provider_test.dart` - New file with 23 unit tests
  - `.env` - New empty file for asset bundle

- **Learnings:**
  - Freezed generated files must exist before analyze can pass (run `dart run build_runner build`)
  - When mocking classes with constructor dependencies that throw, use `implements` instead of `extends`
  - The `.env` file is listed as an asset in pubspec.yaml and must exist for tests to run
  - Sealed classes in Dart 3 provide type-safe state hierarchies without needing freezed

---
