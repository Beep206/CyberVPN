import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/repositories/settings_repository.dart';

/// Concrete implementation of [SettingsRepository] backed by [SharedPreferences].
///
/// Persists each settings field under a typed key prefixed with `settings.`.
/// Missing keys fall back to the defaults defined in [AppSettings].
class SettingsRepositoryImpl implements SettingsRepository {
  final SharedPreferences _prefs;

  SettingsRepositoryImpl({required SharedPreferences sharedPreferences})
      : _prefs = sharedPreferences;

  // ---------------------------------------------------------------------------
  // SharedPreferences key constants
  // ---------------------------------------------------------------------------

  static const _kThemeMode = 'settings.themeMode';
  static const _kBrightness = 'settings.brightness';
  static const _kDynamicColor = 'settings.dynamicColor';
  static const _kPreferredProtocol = 'settings.preferredProtocol';
  static const _kAutoConnectOnLaunch = 'settings.autoConnectOnLaunch';
  static const _kAutoConnectUntrustedWifi = 'settings.autoConnectUntrustedWifi';
  static const _kKillSwitch = 'settings.killSwitch';
  static const _kSplitTunneling = 'settings.splitTunneling';
  static const _kDnsProvider = 'settings.dnsProvider';
  static const _kCustomDns = 'settings.customDns';
  static const _kMtuMode = 'settings.mtuMode';
  static const _kMtuValue = 'settings.mtuValue';
  static const _kLocale = 'settings.locale';
  static const _kNotificationConnection = 'settings.notificationConnection';
  static const _kNotificationExpiry = 'settings.notificationExpiry';
  static const _kNotificationPromotional = 'settings.notificationPromotional';
  static const _kNotificationReferral = 'settings.notificationReferral';
  static const _kNotificationVpnSpeed = 'settings.notificationVpnSpeed';
  static const _kPreferMapView = 'settings.preferMapView';
  static const _kClipboardAutoDetect = 'settings.clipboardAutoDetect';
  static const _kLogLevel = 'settings.logLevel';
  static const _kOledMode = 'settings.oledMode';
  static const _kScanlineEffect = 'settings.scanlineEffect';
  static const _kTextScale = 'settings.textScale';
  static const _kHapticsEnabled = 'settings.hapticsEnabled';
  static const _kTrustedWifiNetworks = 'settings.trustedWifiNetworks';

  /// All keys managed by this repository, used for [resetSettings].
  static const _allKeys = [
    _kThemeMode,
    _kBrightness,
    _kDynamicColor,
    _kOledMode,
    _kScanlineEffect,
    _kTextScale,
    _kPreferredProtocol,
    _kAutoConnectOnLaunch,
    _kAutoConnectUntrustedWifi,
    _kKillSwitch,
    _kSplitTunneling,
    _kDnsProvider,
    _kCustomDns,
    _kMtuMode,
    _kMtuValue,
    _kLocale,
    _kNotificationConnection,
    _kNotificationExpiry,
    _kNotificationPromotional,
    _kNotificationReferral,
    _kNotificationVpnSpeed,
    _kPreferMapView,
    _kClipboardAutoDetect,
    _kHapticsEnabled,
    _kTrustedWifiNetworks,
    _kLogLevel,
  ];

  // ---------------------------------------------------------------------------
  // Enum serialization helpers
  // ---------------------------------------------------------------------------

  /// Reads an enum value from [SharedPreferences] by its [name].
  ///
  /// Returns the matching enum constant from [values], or [defaultValue] if
  /// the stored string does not match any constant.
  static T _readEnum<T extends Enum>(
    String? stored,
    List<T> values,
    T defaultValue,
  ) {
    if (stored == null) return defaultValue;
    return values.firstWhere(
      (e) => e.name == stored,
      orElse: () => defaultValue,
    );
  }

  // ---------------------------------------------------------------------------
  // SettingsRepository implementation
  // ---------------------------------------------------------------------------

  @override
  Future<Result<AppSettings>> getSettings() async {
    try {
      // One-time migration from legacy theme keys (System A) to unified keys.
      await _migrateLegacyThemeKeys();

      // Construct AppSettings by reading each key with a fallback to the
      // default value defined in the freezed factory constructor.
      const defaults = AppSettings();

      final settings = AppSettings(
        themeMode: _readEnum(
          _prefs.getString(_kThemeMode),
          AppThemeMode.values,
          defaults.themeMode,
        ),
        brightness: _readEnum(
          _prefs.getString(_kBrightness),
          AppBrightness.values,
          defaults.brightness,
        ),
        dynamicColor: _prefs.getBool(_kDynamicColor) ?? defaults.dynamicColor,
        oledMode: _prefs.getBool(_kOledMode) ?? defaults.oledMode,
        scanlineEffect:
            _prefs.getBool(_kScanlineEffect) ?? defaults.scanlineEffect,
        textScale: _readEnum(
          _prefs.getString(_kTextScale),
          TextScale.values,
          defaults.textScale,
        ),
        preferredProtocol: _readEnum(
          _prefs.getString(_kPreferredProtocol),
          PreferredProtocol.values,
          defaults.preferredProtocol,
        ),
        autoConnectOnLaunch:
            _prefs.getBool(_kAutoConnectOnLaunch) ?? defaults.autoConnectOnLaunch,
        autoConnectUntrustedWifi: _prefs.getBool(_kAutoConnectUntrustedWifi) ??
            defaults.autoConnectUntrustedWifi,
        killSwitch: _prefs.getBool(_kKillSwitch) ?? defaults.killSwitch,
        splitTunneling:
            _prefs.getBool(_kSplitTunneling) ?? defaults.splitTunneling,
        dnsProvider: _readEnum(
          _prefs.getString(_kDnsProvider),
          DnsProvider.values,
          defaults.dnsProvider,
        ),
        customDns: _prefs.getString(_kCustomDns) ?? defaults.customDns,
        mtuMode: _readEnum(
          _prefs.getString(_kMtuMode),
          MtuMode.values,
          defaults.mtuMode,
        ),
        mtuValue: _prefs.getInt(_kMtuValue) ?? defaults.mtuValue,
        locale: _prefs.getString(_kLocale) ?? defaults.locale,
        notificationConnection: _prefs.getBool(_kNotificationConnection) ??
            defaults.notificationConnection,
        notificationExpiry:
            _prefs.getBool(_kNotificationExpiry) ?? defaults.notificationExpiry,
        notificationPromotional: _prefs.getBool(_kNotificationPromotional) ??
            defaults.notificationPromotional,
        notificationReferral:
            _prefs.getBool(_kNotificationReferral) ?? defaults.notificationReferral,
        notificationVpnSpeed:
            _prefs.getBool(_kNotificationVpnSpeed) ?? defaults.notificationVpnSpeed,
        preferMapView:
            _prefs.getBool(_kPreferMapView) ?? defaults.preferMapView,
        clipboardAutoDetect:
            _prefs.getBool(_kClipboardAutoDetect) ?? defaults.clipboardAutoDetect,
        hapticsEnabled:
            _prefs.getBool(_kHapticsEnabled) ?? defaults.hapticsEnabled,
        trustedWifiNetworks:
            _prefs.getStringList(_kTrustedWifiNetworks) ??
                defaults.trustedWifiNetworks,
        logLevel: _readEnum(
          _prefs.getString(_kLogLevel),
          LogLevel.values,
          defaults.logLevel,
        ),
      );

      return Success(settings);
    } catch (e) {
      return Failure(CacheFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> updateSettings(AppSettings settings) async {
    try {
      await _prefs.setString(_kThemeMode, settings.themeMode.name);
      await _prefs.setString(_kBrightness, settings.brightness.name);
      await _prefs.setBool(_kDynamicColor, settings.dynamicColor);
      await _prefs.setBool(_kOledMode, settings.oledMode);
      await _prefs.setBool(_kScanlineEffect, settings.scanlineEffect);
      await _prefs.setString(_kTextScale, settings.textScale.name);
      await _prefs.setString(
          _kPreferredProtocol, settings.preferredProtocol.name);
      await _prefs.setBool(_kAutoConnectOnLaunch, settings.autoConnectOnLaunch);
      await _prefs.setBool(
          _kAutoConnectUntrustedWifi, settings.autoConnectUntrustedWifi);
      await _prefs.setBool(_kKillSwitch, settings.killSwitch);
      await _prefs.setBool(_kSplitTunneling, settings.splitTunneling);
      await _prefs.setString(_kDnsProvider, settings.dnsProvider.name);
      if (settings.customDns != null) {
        await _prefs.setString(_kCustomDns, settings.customDns!);
      } else {
        await _prefs.remove(_kCustomDns);
      }
      await _prefs.setString(_kMtuMode, settings.mtuMode.name);
      await _prefs.setInt(_kMtuValue, settings.mtuValue);
      await _prefs.setString(_kLocale, settings.locale);
      await _prefs.setBool(
          _kNotificationConnection, settings.notificationConnection);
      await _prefs.setBool(_kNotificationExpiry, settings.notificationExpiry);
      await _prefs.setBool(
          _kNotificationPromotional, settings.notificationPromotional);
      await _prefs.setBool(_kNotificationReferral, settings.notificationReferral);
      await _prefs.setBool(_kNotificationVpnSpeed, settings.notificationVpnSpeed);
      await _prefs.setBool(_kPreferMapView, settings.preferMapView);
      await _prefs.setBool(_kClipboardAutoDetect, settings.clipboardAutoDetect);
      await _prefs.setBool(_kHapticsEnabled, settings.hapticsEnabled);
      await _prefs.setStringList(
          _kTrustedWifiNetworks, settings.trustedWifiNetworks);
      await _prefs.setString(_kLogLevel, settings.logLevel.name);
      return const Success(null);
    } catch (e) {
      return Failure(CacheFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> resetSettings() async {
    try {
      for (final key in _allKeys) {
        await _prefs.remove(key);
      }
      return const Success(null);
    } catch (e) {
      return Failure(CacheFailure(message: e.toString()));
    }
  }

  // ---------------------------------------------------------------------------
  // Legacy key migration
  // ---------------------------------------------------------------------------

  /// Legacy SharedPreferences keys from the old ThemeNotifier system.
  static const _kLegacyThemeMode = 'theme_mode';
  static const _kLegacyBrightness = 'theme_brightness';
  static const _kLegacyOledMode = 'theme_oled_mode';

  /// One-time migration from legacy theme keys to the unified `settings.*` keys.
  ///
  /// If the new `settings.themeMode` key does not exist but the legacy
  /// `theme_mode` key does, copies all legacy values to the new keys
  /// and removes the legacy keys.
  Future<void> _migrateLegacyThemeKeys() async {
    if (_prefs.containsKey(_kThemeMode)) return; // Already migrated or fresh

    final legacyMode = _prefs.getString(_kLegacyThemeMode);
    if (legacyMode == null) return; // No legacy data

    await _prefs.setString(_kThemeMode, legacyMode);
    final legacyBrightness = _prefs.getString(_kLegacyBrightness);
    if (legacyBrightness != null) {
      await _prefs.setString(_kBrightness, legacyBrightness);
    }
    final legacyOled = _prefs.getBool(_kLegacyOledMode);
    if (legacyOled != null) {
      await _prefs.setBool(_kOledMode, legacyOled);
    }

    // Clean up legacy keys
    await _prefs.remove(_kLegacyThemeMode);
    await _prefs.remove(_kLegacyBrightness);
    await _prefs.remove(_kLegacyOledMode);
  }
}
