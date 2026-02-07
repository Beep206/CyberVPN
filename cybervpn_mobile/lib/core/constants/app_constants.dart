/// Application-wide constants for CyberVPN.
class AppConstants {
  const AppConstants._();

  // ── App Metadata ──────────────────────────────────────────────────────

  static const String appName = 'CyberVPN';
  static const String appVersion = '1.0.0';
  static const String appBuildNumber = '1';
  static const String appPackageId = 'com.cybervpn.app';

  // ── Support & Legal ───────────────────────────────────────────────────

  static const String supportEmail = 'support@cybervpn.com';
  static const String privacyPolicyUrl = 'https://cybervpn.com/privacy';
  static const String termsOfServiceUrl = 'https://cybervpn.com/terms';
  static const String websiteUrl = 'https://cybervpn.com';

  // ── Animation Durations (milliseconds) ────────────────────────────────

  static const int animDurationFast = 150;
  static const int animDurationNormal = 300;
  static const int animDurationSlow = 500;
  static const int animDurationVerySlow = 1000;

  /// Delay before showing splash-to-home transition.
  static const int splashDuration = 2000;

  /// Debounce delay for search input.
  static const int searchDebounce = 400;

  // ── Padding & Spacing ─────────────────────────────────────────────────

  static const double paddingXS = 4.0;
  static const double paddingSM = 8.0;
  static const double paddingMD = 16.0;
  static const double paddingLG = 24.0;
  static const double paddingXL = 32.0;
  static const double paddingXXL = 48.0;

  // ── Border Radius ─────────────────────────────────────────────────────

  static const double radiusSM = 4.0;
  static const double radiusMD = 8.0;
  static const double radiusLG = 12.0;
  static const double radiusXL = 16.0;
  static const double radiusRound = 999.0;

  // ── Layout ────────────────────────────────────────────────────────────

  static const double maxContentWidth = 600.0;
  static const double appBarHeight = 56.0;
  static const double bottomNavHeight = 64.0;

  // ── Pagination ────────────────────────────────────────────────────────

  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  // ── Secure Storage Keys ───────────────────────────────────────────────

  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userIdKey = 'user_id';
  static const String onboardingCompleteKey = 'onboarding_complete';
  static const String selectedLocaleKey = 'selected_locale';

  // ── Feature Flags ─────────────────────────────────────────────────────

  static const bool enableReferralSystem = true;
  static const bool enableTrialMode = true;
  static const bool enableCryptoPayments = true;
}
