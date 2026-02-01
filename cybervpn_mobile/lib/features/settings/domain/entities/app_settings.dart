import 'package:freezed_annotation/freezed_annotation.dart';

part 'app_settings.freezed.dart';

/// Theme mode for the application UI
enum AppThemeMode {
  materialYou,
  cyberpunk,
}

/// Brightness setting for the application
enum AppBrightness {
  system,
  light,
  dark,
}

/// Preferred VPN protocol
enum PreferredProtocol {
  auto,
  vlessReality,
  vlessXhttp,
  vlessWsTls,
}

/// DNS provider for VPN connections
enum DnsProvider {
  system,
  cloudflare,
  google,
  quad9,
  custom,
}

/// MTU mode for VPN connections
enum MtuMode {
  auto,
  manual,
}

/// Log level for application diagnostics
enum LogLevel {
  debug,
  info,
  warning,
  error,
}

/// Application settings entity
///
/// Contains all user-configurable settings including theme, connection,
/// notification, and privacy preferences.
@freezed
abstract class AppSettings with _$AppSettings {
  const factory AppSettings({
    // Appearance
    @Default(AppThemeMode.cyberpunk) AppThemeMode themeMode,
    @Default(AppBrightness.system) AppBrightness brightness,
    @Default(false) bool dynamicColor,

    // Connection
    @Default(PreferredProtocol.auto) PreferredProtocol preferredProtocol,
    @Default(false) bool autoConnectOnLaunch,
    @Default(false) bool autoConnectUntrustedWifi,
    @Default(false) bool killSwitch,

    // Split Tunneling
    @Default(false) bool splitTunneling,

    // DNS
    @Default(DnsProvider.system) DnsProvider dnsProvider,
    String? customDns,

    // MTU
    @Default(MtuMode.auto) MtuMode mtuMode,
    @Default(1400) int mtuValue,

    // Locale
    @Default('en') String locale,

    // Notifications
    @Default(true) bool notificationConnection,
    @Default(true) bool notificationExpiry,
    @Default(false) bool notificationPromotional,
    @Default(true) bool notificationReferral,
    @Default(true) bool notificationVpnSpeed,

    // Privacy
    @Default(false) bool clipboardAutoDetect,

    // Haptics
    @Default(true) bool hapticsEnabled,

    // Diagnostics
    @Default(LogLevel.info) LogLevel logLevel,
  }) = _AppSettings;
}
