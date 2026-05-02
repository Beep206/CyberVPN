# Mobile SDK Integration

## Goal

Подключить официальные Telegram native SDK на iOS и Android и дать Flutter-приложению единый интерфейс для login flow.

## Recommended Flutter Abstraction

```dart
abstract interface class TelegramNativeAuthClient {
  Future<TelegramNativeAuthResult> login({
    required bool requestPhone,
  });
}

class TelegramNativeAuthResult {
  final String idToken;
  final String? username;
  final String? displayName;
  final String? phoneNumber;

  const TelegramNativeAuthResult({
    required this.idToken,
    this.username,
    this.displayName,
    this.phoneNumber,
  });
}
```

## Flutter Failure Model

```dart
sealed class TelegramNativeAuthFailure {
  const TelegramNativeAuthFailure();
}

final class TelegramNativeAuthCancelled extends TelegramNativeAuthFailure {
  const TelegramNativeAuthCancelled();
}

final class TelegramNativeAuthNotConfigured extends TelegramNativeAuthFailure {
  const TelegramNativeAuthNotConfigured();
}

final class TelegramNativeAuthSdkError extends TelegramNativeAuthFailure {
  final String message;

  const TelegramNativeAuthSdkError(this.message);
}
```

## Recommended Flutter Integration Shape

- create a dedicated Flutter platform bridge
- expose one Dart service to the auth layer
- keep Telegram SDK specifics out of auth UI code

Suggested layers:

- `core/platform/telegram_native_auth_client.dart`
- `core/platform/telegram_native_auth_method_channel.dart`
- `ios/Runner/...` native adapter
- `android/app/...` native adapter
- `features/auth/...` provider orchestration

## Current Repo Readiness

The current mobile app already has some reusable foundations:

- deep link parsing for Telegram and generic OAuth callbacks
- `singleTask` Android activity launch mode
- iOS Associated Domains capability already enabled
- Telegram login entry points on login and register screens

The current mobile app is not yet ready for official native Telegram SDK callback handling:

- the active Telegram flow is still driven by `TELEGRAM_BOT_USERNAME`
- the active callback path is `cybervpn://telegram/callback`
- the committed iOS associated domain is `applinks:cybervpn.app`, not a Telegram `tg.dev` domain
- the committed Android App Link host is `cybervpn.app`, not a Telegram `tg.dev` host

## Flutter Auth Provider Flow

1. User taps Telegram button.
2. Provider calls `TelegramNativeAuthClient.login()`.
3. Native layer returns `idToken`.
4. Flutter calls `POST /api/v1/mobile/auth/telegram/oidc`.
5. Backend returns either:
   - `AuthResponse`
   - `requires_2fa`
6. Flutter stores first-party tokens or routes to TOTP UI.

Important rule:

- `idToken` is never treated as authenticated app state on the client

## iOS Integration

Based on the official iOS SDK README:

- install via Swift Package Manager
- configure globally with `TelegramLogin.configure(...)`
- call `TelegramLogin.login(...)`
- handle callback via `.onOpenURL` or `SceneDelegate`
- pass callback URL into `TelegramLogin.handle(url)`
- current public example shows `clientId`, `redirectUri` and `scopes`
- current public example does not document `nonce` or `state`

Phase 1 iOS checklist:

- add SDK package
- configure `clientId`
- configure `redirectUri`
- configure scopes
- add `Associated Domains`
- wire callback handling in the app entry point
- bridge `loginData.idToken` back to Flutter

## Android Integration

Based on the official Android SDK README:

- add GitHub Packages Maven repository
- add dependency `org.telegram:login-sdk:1.0.0`
- initialize SDK with `TelegramLogin.init(...)`
- start login with `TelegramLogin.startLogin(...)`
- handle callback through `onNewIntent` or `onCreate`
- pass callback URI into `TelegramLogin.handleLoginResponse(...)`
- current public example shows `clientId`, `redirectUri` and `scopes`
- current public example does not document `nonce` or `state`

Phase 1 Android checklist:

- add repository and dependency
- configure `clientId`
- configure `redirectUri`
- configure scopes
- add App Link intent-filter
- verify host before passing URI to SDK
- bridge `loginData.idToken` back to Flutter

## Android Build And CI Requirements

- store GitHub Packages credentials in CI secret storage
- token must have `read:packages`
- verify CI can resolve `org.telegram:login-sdk:1.0.0`
- document fallback plan if the GitHub Packages artifact is unavailable

## Scope Policy In Mobile Layer

Phase 1 recommendation:

- product-level target scopes: `openid profile`
- enable `phone` scope only behind feature flag

Implementation note:

- the official native SDK README examples show `profile` and optional `phone`
- the official native SDK README examples expose `clientId`, `redirectUri`, `scopes` and success `idToken`
- if the SDK API exposes only Telegram login permission scopes, use:
  - Phase 1 default: `["profile"]`
  - Phase 1 with phone: `["profile", "phone"]`
- backend must still treat the returned token as an OIDC `id_token` and validate it accordingly

## UI Behavior

Telegram button states:

- idle
- launching native login
- waiting for Telegram callback
- exchanging `id_token` with backend
- pending 2FA
- cancelled
- success
- error

Fallback behavior:

- if native feature flag is disabled, use current legacy flow
- if SDK initialization fails in internal builds, show actionable error
- production should prefer hiding broken native path over silently creating partial auth state
- cancelled login is not an error toast by default

## Phase 0 Integration Consequences

- native login cannot be enabled only by backend work; mobile callback surfaces must be reconfigured first
- legacy `TELEGRAM_BOT_USERNAME` support should remain available until old flow deprecation is approved
- new environment config should model Telegram `clientId` and `redirectUri` explicitly
- platform code must validate the callback host before passing the URL or Intent to the Telegram SDK

## Development Logging

### Flutter / Dart

```dart
print('[TelegramNativeAuth] start login');
print('[TelegramNativeAuth] idToken received=${idToken.isNotEmpty}');
print('[TelegramNativeAuth] backend exchange started');
```

### Android / Kotlin

```kotlin
Log.d("TelegramLogin", "startLogin")
Log.d("TelegramLogin", "idToken received=${idToken.isNotBlank()}")
Log.e("TelegramLogin", "Login failed", error)
```

### iOS / Swift

```swift
print("[TelegramLogin] start login")
print("[TelegramLogin] idToken received: \(!loginData.idToken.isEmpty)")
print("[TelegramLogin] error: \(error.localizedDescription)")
```

Do not log:

- raw `id_token`
- full phone number
- access/refresh tokens

## External References

- Telegram Login SDK for iOS: <https://github.com/TelegramMessenger/telegram-login-ios>
- Telegram Login SDK for Android: <https://github.com/TelegramMessenger/telegram-login-android>
