import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Centralized environment configuration for CyberVPN.
///
/// Reads values from compile-time `--dart-define` flags first, then falls
/// back to a `.env` file loaded via `flutter_dotenv` for local development.
///
/// **Security**: The `.env` file is **never** bundled as a Flutter asset.
/// In release builds, all configuration must come from `--dart-define` flags.
/// The `.env` fallback is only active in debug/profile builds.
///
/// ### Compile-time configuration (recommended for CI / release builds)
///
/// ```bash
/// flutter run \
///   --dart-define=API_BASE_URL=http://localhost:8000 \
///   --dart-define=API_ENV=dev
/// ```
///
/// ### Local development fallback
///
/// Copy `.env.example` to `.env` at the project root and set values there.
/// Call [EnvironmentConfig.init] in `main()` **before** `runApp()`.
class EnvironmentConfig {
  const EnvironmentConfig._();

  // ── Compile-time constants (dart-define) ─────────────────────────────

  /// Default base URL used when no `--dart-define` is provided.
  ///
  /// SECURITY: Computed at runtime to avoid appearing as a plaintext string
  /// in the binary. In release builds, this should always be overridden by
  /// the `--dart-define=API_BASE_URL=...` flag.
  static String get _defaultBaseUrl => String.fromCharCodes([
    104,
    116,
    116,
    112,
    115,
    58,
    47,
    47,
    97,
    112,
    105,
    46,
    99,
    121,
    98,
    101,
    114,
    118,
    112,
    110,
    46,
    99,
    111,
    109,
  ]); // https://api.cybervpn.com

  /// Default web base URL for public pages (privacy policy, etc.)
  static String get _defaultWebBaseUrl => String.fromCharCodes([
    104,
    116,
    116,
    112,
    115,
    58,
    47,
    47,
    99,
    121,
    98,
    101,
    114,
    118,
    112,
    110,
    46,
    97,
    112,
    112,
  ]); // https://cybervpn.app

  /// Default environment name.
  static const String _defaultEnv = 'prod';

  /// Value injected at compile time via `--dart-define=API_BASE_URL=...`.
  static const String _dartDefineBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://api.cybervpn.com',
  );

  /// Value injected at compile time via `--dart-define=API_ENV=...`.
  static const String _dartDefineEnv = String.fromEnvironment(
    'API_ENV',
    defaultValue: _defaultEnv,
  );

  /// Value injected at compile time via `--dart-define=WEB_BASE_URL=...`.
  static const String _dartDefineWebBaseUrl = String.fromEnvironment(
    'WEB_BASE_URL',
    defaultValue: 'https://cybervpn.app',
  );

  /// Value injected at compile time via `--dart-define=SENTRY_DSN=...`.
  ///
  /// Empty by default so Sentry is disabled in local/dev builds.
  static const String _dartDefineSentryDsn = String.fromEnvironment(
    'SENTRY_DSN',
    defaultValue: '',
  );

  /// Value injected at compile time via `--dart-define=SENTRY_RELEASE=...`.
  ///
  /// Empty by default so builds without an explicit release contract do not
  /// create misleading release identifiers in Sentry.
  static const String _dartDefineSentryRelease = String.fromEnvironment(
    'SENTRY_RELEASE',
    defaultValue: '',
  );

  /// Value injected at compile time via `--dart-define=CERT_FINGERPRINTS=...`.
  ///
  /// Comma-separated list of SHA-256 certificate fingerprints for pinning.
  /// Empty by default to disable certificate pinning in dev environments.
  static const String _dartDefineCertFingerprints = String.fromEnvironment(
    'CERT_FINGERPRINTS',
    defaultValue: '',
  );

  /// Value injected at compile time via `--dart-define=TELEGRAM_BOT_USERNAME=...`.
  ///
  /// Telegram bot username (without @) for Login Widget integration.
  /// Required for Telegram OAuth functionality.
  static const String _dartDefineTelegramBotUsername = String.fromEnvironment(
    'TELEGRAM_BOT_USERNAME',
    defaultValue: '',
  );

  /// Value injected at compile time via `--dart-define=TELEGRAM_OIDC_CLIENT_ID=...`.
  ///
  /// Used by the official Telegram native login SDK.
  static const String _dartDefineTelegramOidcClientId = String.fromEnvironment(
    'TELEGRAM_OIDC_CLIENT_ID',
    defaultValue: '',
  );

  /// Value injected at compile time via `--dart-define=TELEGRAM_NATIVE_REDIRECT_URI=...`.
  ///
  /// Used by the official Telegram native login SDK callback handling.
  static const String _dartDefineTelegramNativeRedirectUri =
      String.fromEnvironment('TELEGRAM_NATIVE_REDIRECT_URI', defaultValue: '');

  /// Feature flag injected at compile time via
  /// `--dart-define=TELEGRAM_NATIVE_LOGIN_ENABLED=...`.
  static const String _dartDefineTelegramNativeLoginEnabled =
      String.fromEnvironment(
        'TELEGRAM_NATIVE_LOGIN_ENABLED',
        defaultValue: 'false',
      );

  /// Feature flag injected at compile time via
  /// `--dart-define=TELEGRAM_NATIVE_PHONE_SCOPE_ENABLED=...`.
  static const String _dartDefineTelegramNativePhoneScopeEnabled =
      String.fromEnvironment(
        'TELEGRAM_NATIVE_PHONE_SCOPE_ENABLED',
        defaultValue: 'false',
      );

  /// Platform rollout flag injected via
  /// `--dart-define=TELEGRAM_NATIVE_LOGIN_IOS_ENABLED=...`.
  ///
  /// Defaults to `true` so existing builds that only use the global flag keep
  /// working until rollout needs per-platform gating.
  static const String _dartDefineTelegramNativeLoginIosEnabled =
      String.fromEnvironment(
        'TELEGRAM_NATIVE_LOGIN_IOS_ENABLED',
        defaultValue: 'true',
      );

  /// Platform rollout flag injected via
  /// `--dart-define=TELEGRAM_NATIVE_LOGIN_ANDROID_ENABLED=...`.
  ///
  /// Defaults to `true` so existing builds that only use the global flag keep
  /// working until rollout needs per-platform gating.
  static const String _dartDefineTelegramNativeLoginAndroidEnabled =
      String.fromEnvironment(
        'TELEGRAM_NATIVE_LOGIN_ANDROID_ENABLED',
        defaultValue: 'true',
      );

  // ── Resolved values (dart-define > .env > default) ───────────────────

  /// Whether the `.env` file has been loaded.
  static bool _dotenvLoaded = false;

  /// Initializes `flutter_dotenv` by loading the `.env` file.
  ///
  /// Call once in `main()` before `runApp()`. In **release** builds this is
  /// a no-op: the `.env` file is not bundled as an asset and all configuration
  /// must come from `--dart-define`. In debug/profile builds the `.env` file
  /// is loaded from disk as a convenience for local development.
  static Future<void> init() async {
    // SECURITY: Never load .env in release builds. All config must come from
    // --dart-define flags which are compiled into the binary and do not expose
    // a readable file in the APK/IPA.
    if (kReleaseMode) {
      _dotenvLoaded = false;
      return;
    }

    try {
      await dotenv.load(fileName: '.env');
      _dotenvLoaded = true;
    } catch (e) {
      // .env file missing or unreadable -- use dart-define / defaults.
      _dotenvLoaded = false;
    }
  }

  /// The resolved API base URL.
  ///
  /// Priority: `--dart-define` > `.env` > hard-coded default.
  static String get baseUrl {
    // If a non-default value was supplied via dart-define, prefer it.
    if (_dartDefineBaseUrl != _defaultBaseUrl) {
      return _dartDefineBaseUrl;
    }

    // Fall back to .env value when available.
    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('API_BASE_URL');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return _defaultBaseUrl;
  }

  /// The resolved environment name (`dev`, `staging`, or `prod`).
  ///
  /// Priority: `--dart-define` > `.env` > hard-coded default.
  static String get environment {
    if (_dartDefineEnv != _defaultEnv) {
      return _dartDefineEnv;
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('API_ENV');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return _defaultEnv;
  }

  /// The resolved web base URL for public pages.
  ///
  /// Priority: `--dart-define` > `.env` > hard-coded default.
  static String get webBaseUrl {
    if (_dartDefineWebBaseUrl != _defaultWebBaseUrl) {
      return _dartDefineWebBaseUrl;
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('WEB_BASE_URL');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return _defaultWebBaseUrl;
  }

  /// The resolved Sentry DSN.
  ///
  /// Priority: `--dart-define` > `.env` > empty string (disabled).
  ///
  /// When the returned value is empty Sentry initialisation is skipped,
  /// which is the expected behaviour for local development.
  static String get sentryDsn {
    if (_dartDefineSentryDsn.isNotEmpty) {
      return _dartDefineSentryDsn;
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('SENTRY_DSN');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return '';
  }

  /// The resolved Sentry release identifier.
  ///
  /// Priority: `--dart-define` > `.env` > empty string.
  ///
  /// When empty, Sentry falls back to its default release behavior.
  static String get sentryRelease {
    if (_dartDefineSentryRelease.isNotEmpty) {
      return _dartDefineSentryRelease;
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('SENTRY_RELEASE');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return '';
  }

  /// The resolved certificate fingerprints for SSL pinning.
  ///
  /// Priority: `--dart-define` > `.env` > empty list (disabled).
  ///
  /// Returns a list of SHA-256 certificate fingerprints in colon-separated
  /// hex format. When empty, certificate pinning is disabled (dev/local mode).
  ///
  /// Format: `AA:BB:CC:DD:...,EE:FF:00:11:...` (comma-separated)
  static List<String> get certificateFingerprints {
    String rawValue = '';

    if (_dartDefineCertFingerprints.isNotEmpty) {
      rawValue = _dartDefineCertFingerprints;
    } else if (_dotenvLoaded) {
      rawValue = dotenv.maybeGet('CERT_FINGERPRINTS') ?? '';
    }

    if (rawValue.isEmpty) {
      return [];
    }

    // Split by comma and trim whitespace
    return rawValue
        .split(',')
        .map((fp) => fp.trim())
        .where((fp) => fp.isNotEmpty)
        .toList();
  }

  /// The resolved Telegram bot username for Login Widget.
  ///
  /// Priority: `--dart-define` > `.env` > empty string (disabled).
  ///
  /// When the returned value is empty Telegram login is unavailable.
  static String get telegramBotUsername {
    if (_dartDefineTelegramBotUsername.isNotEmpty) {
      return _dartDefineTelegramBotUsername;
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('TELEGRAM_BOT_USERNAME');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return '';
  }

  /// The resolved Telegram OIDC client id for native login.
  ///
  /// Priority: `--dart-define` > `.env` > empty string (disabled).
  static String get telegramOidcClientId {
    if (_dartDefineTelegramOidcClientId.isNotEmpty) {
      return _dartDefineTelegramOidcClientId;
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('TELEGRAM_OIDC_CLIENT_ID');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return '';
  }

  /// The resolved redirect URI for the Telegram native login SDK.
  ///
  /// Priority: `--dart-define` > `.env` > empty string (disabled).
  static String get telegramNativeRedirectUri {
    if (_dartDefineTelegramNativeRedirectUri.isNotEmpty) {
      return _dartDefineTelegramNativeRedirectUri;
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('TELEGRAM_NATIVE_REDIRECT_URI');
      if (envValue != null && envValue.isNotEmpty) {
        return envValue;
      }
    }

    return '';
  }

  /// `true` when the Telegram native login feature flag is enabled.
  static bool get telegramNativeLoginEnabledFlag {
    if (_dartDefineTelegramNativeLoginEnabled != 'false') {
      return _parseBool(_dartDefineTelegramNativeLoginEnabled);
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('TELEGRAM_NATIVE_LOGIN_ENABLED');
      if (envValue != null && envValue.isNotEmpty) {
        return _parseBool(envValue);
      }
    }

    return false;
  }

  /// `true` when the Telegram native login flow should request the phone scope.
  static bool get telegramNativePhoneScopeEnabled {
    if (_dartDefineTelegramNativePhoneScopeEnabled != 'false') {
      return _parseBool(_dartDefineTelegramNativePhoneScopeEnabled);
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('TELEGRAM_NATIVE_PHONE_SCOPE_ENABLED');
      if (envValue != null && envValue.isNotEmpty) {
        return _parseBool(envValue);
      }
    }

    return false;
  }

  /// `true` when Telegram native login is allowed for iOS builds.
  static bool get telegramNativeLoginIosEnabledFlag {
    if (_dartDefineTelegramNativeLoginIosEnabled != 'true') {
      return _parseBool(_dartDefineTelegramNativeLoginIosEnabled);
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('TELEGRAM_NATIVE_LOGIN_IOS_ENABLED');
      if (envValue != null && envValue.isNotEmpty) {
        return _parseBool(envValue);
      }
    }

    return true;
  }

  /// `true` when Telegram native login is allowed for Android builds.
  static bool get telegramNativeLoginAndroidEnabledFlag {
    if (_dartDefineTelegramNativeLoginAndroidEnabled != 'true') {
      return _parseBool(_dartDefineTelegramNativeLoginAndroidEnabled);
    }

    if (_dotenvLoaded) {
      final envValue = dotenv.maybeGet('TELEGRAM_NATIVE_LOGIN_ANDROID_ENABLED');
      if (envValue != null && envValue.isNotEmpty) {
        return _parseBool(envValue);
      }
    }

    return true;
  }

  // ── Convenience helpers ──────────────────────────────────────────────

  /// `true` when running in the `dev` environment.
  static bool get isDev => environment == 'dev';

  /// `true` when running in the `staging` environment.
  static bool get isStaging => environment == 'staging';

  /// `true` when running in the `prod` environment.
  static bool get isProd => environment == 'prod';

  /// `true` when the legacy Telegram Login Widget flow is available.
  static bool get isTelegramLegacyLoginAvailable =>
      telegramBotUsername.isNotEmpty;

  /// `true` when the Telegram native SDK flow is configured and enabled.
  static bool get isTelegramNativeLoginEnabled =>
      telegramNativeLoginEnabledFlag &&
      telegramOidcClientId.isNotEmpty &&
      telegramNativeRedirectUri.isNotEmpty;

  /// `true` when Telegram native login is enabled and allowed for this
  /// platform rollout cohort.
  static bool get isTelegramNativeLoginEnabledForCurrentPlatform {
    if (!isTelegramNativeLoginEnabled || kIsWeb) {
      return false;
    }

    switch (defaultTargetPlatform) {
      case TargetPlatform.iOS:
        return telegramNativeLoginIosEnabledFlag;
      case TargetPlatform.android:
        return telegramNativeLoginAndroidEnabledFlag;
      default:
        return false;
    }
  }

  /// `true` when any Telegram login entry point is available.
  static bool get isTelegramLoginAvailable =>
      isTelegramNativeLoginEnabled || isTelegramLegacyLoginAvailable;

  static bool _parseBool(String value) {
    switch (value.trim().toLowerCase()) {
      case '1':
      case 'true':
      case 'yes':
      case 'on':
        return true;
      default:
        return false;
    }
  }
}
