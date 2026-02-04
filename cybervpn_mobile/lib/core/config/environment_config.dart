import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Centralized environment configuration for CyberVPN.
///
/// Reads values from compile-time `--dart-define` flags first, then falls
/// back to a `.env` file loaded via `flutter_dotenv` for local development.
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
  static const String _defaultBaseUrl = 'https://api.cybervpn.com';

  /// Default web base URL for public pages (privacy policy, etc.)
  static const String _defaultWebBaseUrl = 'https://cybervpn.app';

  /// Default environment name.
  static const String _defaultEnv = 'prod';

  /// Value injected at compile time via `--dart-define=API_BASE_URL=...`.
  static const String _dartDefineBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: _defaultBaseUrl,
  );

  /// Value injected at compile time via `--dart-define=API_ENV=...`.
  static const String _dartDefineEnv = String.fromEnvironment(
    'API_ENV',
    defaultValue: _defaultEnv,
  );

  /// Value injected at compile time via `--dart-define=WEB_BASE_URL=...`.
  static const String _dartDefineWebBaseUrl = String.fromEnvironment(
    'WEB_BASE_URL',
    defaultValue: _defaultWebBaseUrl,
  );

  /// Value injected at compile time via `--dart-define=SENTRY_DSN=...`.
  ///
  /// Empty by default so Sentry is disabled in local/dev builds.
  static const String _dartDefineSentryDsn = String.fromEnvironment(
    'SENTRY_DSN',
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

  // ── Resolved values (dart-define > .env > default) ───────────────────

  /// Whether the `.env` file has been loaded.
  static bool _dotenvLoaded = false;

  /// Initializes `flutter_dotenv` by loading the `.env` file.
  ///
  /// Call once in `main()` before `runApp()`. If the `.env` file does not
  /// exist the call is a no-op (errors are silently caught so the app can
  /// still start with compile-time defaults).
  static Future<void> init() async {
    try {
      await dotenv.load(fileName: '.env');
      _dotenvLoaded = true;
    } catch (_) {
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

  // ── Convenience helpers ──────────────────────────────────────────────

  /// `true` when running in the `dev` environment.
  static bool get isDev => environment == 'dev';

  /// `true` when running in the `staging` environment.
  static bool get isStaging => environment == 'staging';

  /// `true` when running in the `prod` environment.
  static bool get isProd => environment == 'prod';

  /// `true` when Telegram login is available.
  static bool get isTelegramLoginAvailable => telegramBotUsername.isNotEmpty;
}
