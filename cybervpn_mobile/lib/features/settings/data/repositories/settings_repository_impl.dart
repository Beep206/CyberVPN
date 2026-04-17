import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
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
  static const _kRoutingEnabled = 'settings.routingEnabled';
  static const _kRoutingProfiles = 'settings.routingProfiles';
  static const _kActiveRoutingProfileId = 'settings.activeRoutingProfileId';
  static const _kBypassSubnets = 'settings.bypassSubnets';
  static const _kExcludedRouteEntries = 'settings.excludedRouteEntries';
  static const _kSplitTunneling = 'settings.splitTunneling';
  static const _kPerAppProxyMode = 'settings.perAppProxyMode';
  static const _kPerAppProxyAppIds = 'settings.perAppProxyAppIds';
  static const _kDnsProvider = 'settings.dnsProvider';
  static const _kCustomDns = 'settings.customDns';
  static const _kUseLocalDns = 'settings.useLocalDns';
  static const _kLocalDnsPort = 'settings.localDnsPort';
  static const _kUseDnsFromJson = 'settings.useDnsFromJson';
  static const _kFragmentationEnabled = 'settings.fragmentationEnabled';
  static const _kMuxEnabled = 'settings.muxEnabled';
  static const _kPreferredIpType = 'settings.preferredIpType';
  static const _kSniffingEnabled = 'settings.sniffingEnabled';
  static const _kVpnRunMode = 'settings.vpnRunMode';
  static const _kServerAddressResolveEnabled =
      'settings.serverAddressResolveEnabled';
  static const _kServerAddressResolveDohUrl =
      'settings.serverAddressResolveDohUrl';
  static const _kServerAddressResolveDnsIp =
      'settings.serverAddressResolveDnsIp';
  static const _kPingMode = 'settings.pingMode';
  static const _kPingTestUrl = 'settings.pingTestUrl';
  static const _kPingDisplayMode = 'settings.pingDisplayMode';
  static const _kPingResultMode = 'settings.pingResultMode';
  static const _kMtuMode = 'settings.mtuMode';
  static const _kMtuValue = 'settings.mtuValue';
  static const _kSubscriptionAutoUpdateEnabled =
      'settings.subscriptionAutoUpdateEnabled';
  static const _kSubscriptionAutoUpdateIntervalHours =
      'settings.subscriptionAutoUpdateIntervalHours';
  static const _kSubscriptionUpdateNotificationsEnabled =
      'settings.subscriptionUpdateNotificationsEnabled';
  static const _kSubscriptionAutoUpdateOnOpen =
      'settings.subscriptionAutoUpdateOnOpen';
  static const _kSubscriptionPingOnOpenEnabled =
      'settings.subscriptionPingOnOpenEnabled';
  static const _kSubscriptionConnectStrategy =
      'settings.subscriptionConnectStrategy';
  static const _kPreventDuplicateImports = 'settings.preventDuplicateImports';
  static const _kCollapseSubscriptions = 'settings.collapseSubscriptions';
  static const _kSubscriptionNoFilter = 'settings.subscriptionNoFilter';
  static const _kSubscriptionUserAgentMode =
      'settings.subscriptionUserAgentMode';
  static const _kSubscriptionUserAgentValue =
      'settings.subscriptionUserAgentValue';
  static const _kSubscriptionSortMode = 'settings.subscriptionSortMode';
  static const _kAllowLanConnections = 'settings.allowLanConnections';
  static const _kAppAutoStart = 'settings.appAutoStart';
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
    _kRoutingEnabled,
    _kRoutingProfiles,
    _kActiveRoutingProfileId,
    _kBypassSubnets,
    _kExcludedRouteEntries,
    _kSplitTunneling,
    _kPerAppProxyMode,
    _kPerAppProxyAppIds,
    _kDnsProvider,
    _kCustomDns,
    _kUseLocalDns,
    _kLocalDnsPort,
    _kUseDnsFromJson,
    _kFragmentationEnabled,
    _kMuxEnabled,
    _kPreferredIpType,
    _kSniffingEnabled,
    _kVpnRunMode,
    _kServerAddressResolveEnabled,
    _kServerAddressResolveDohUrl,
    _kServerAddressResolveDnsIp,
    _kPingMode,
    _kPingTestUrl,
    _kPingDisplayMode,
    _kPingResultMode,
    _kMtuMode,
    _kMtuValue,
    _kSubscriptionAutoUpdateEnabled,
    _kSubscriptionAutoUpdateIntervalHours,
    _kSubscriptionUpdateNotificationsEnabled,
    _kSubscriptionAutoUpdateOnOpen,
    _kSubscriptionPingOnOpenEnabled,
    _kSubscriptionConnectStrategy,
    _kPreventDuplicateImports,
    _kCollapseSubscriptions,
    _kSubscriptionNoFilter,
    _kSubscriptionUserAgentMode,
    _kSubscriptionUserAgentValue,
    _kSubscriptionSortMode,
    _kAllowLanConnections,
    _kAppAutoStart,
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

  static List<RoutingProfile> _readRoutingProfiles(String? stored) {
    if (stored == null || stored.isEmpty) return const <RoutingProfile>[];

    try {
      final decoded = jsonDecode(stored);
      if (decoded is! List) return const <RoutingProfile>[];

      return decoded
          .whereType<Map<String, dynamic>>()
          .map(RoutingProfile.fromStorageJson)
          .where((profile) => profile.id.isNotEmpty && profile.name.isNotEmpty)
          .toList();
    } catch (_) {
      return const <RoutingProfile>[];
    }
  }

  static List<ExcludedRouteEntry> _readExcludedRouteEntries(String? stored) {
    if (stored == null || stored.isEmpty) {
      return const <ExcludedRouteEntry>[];
    }

    try {
      final decoded = jsonDecode(stored);
      if (decoded is! List) return const <ExcludedRouteEntry>[];

      return decoded
          .whereType<Map<String, dynamic>>()
          .map(ExcludedRouteEntry.fromStorageJson)
          .where((entry) => entry.normalizedValue.isNotEmpty)
          .toList();
    } catch (_) {
      return const <ExcludedRouteEntry>[];
    }
  }

  static List<String> _normalizeStringList(List<String>? items) {
    if (items == null) return const <String>[];

    final result = <String>[];
    for (final item in items) {
      final normalized = item.trim();
      if (normalized.isEmpty || result.contains(normalized)) continue;
      result.add(normalized);
    }
    return result;
  }

  static List<ExcludedRouteEntry> _normalizeExcludedRouteEntries(
    List<ExcludedRouteEntry> entries,
  ) {
    final byValue = <String, ExcludedRouteEntry>{};
    for (final entry in entries) {
      final normalized = entry.normalizedValue;
      if (normalized.isEmpty) continue;
      byValue[normalized] = ExcludedRouteEntry.parse(normalized);
    }

    final result = byValue.values.toList()
      ..sort((a, b) => a.normalizedValue.compareTo(b.normalizedValue));
    return result;
  }

  static List<String> _effectiveExcludedRouteValues({
    required List<String> bypassSubnets,
    required List<ExcludedRouteEntry> excludedRouteEntries,
  }) {
    if (excludedRouteEntries.isNotEmpty) {
      return excludedRouteEntries
          .map((entry) => entry.normalizedValue)
          .toList(growable: false);
    }

    return bypassSubnets;
  }

  static PingResultMode _readPingResultMode(
    SharedPreferences prefs,
    PingResultMode defaultValue,
  ) {
    final stored = prefs.getString(_kPingResultMode);
    if (stored != null) {
      return _readEnum(stored, PingResultMode.values, defaultValue);
    }

    return switch (prefs.getString(_kPingDisplayMode)) {
      'quality' => PingResultMode.icon,
      _ => PingResultMode.time,
    };
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
      final storedBypassSubnets = _normalizeStringList(
        _prefs.getStringList(_kBypassSubnets),
      );
      final storedExcludedRouteEntries = _normalizeExcludedRouteEntries(
        _readExcludedRouteEntries(_prefs.getString(_kExcludedRouteEntries)),
      );
      final effectiveExcludedRouteEntries =
          storedExcludedRouteEntries.isNotEmpty
          ? storedExcludedRouteEntries
          : storedBypassSubnets.map(ExcludedRouteEntry.parse).toList();
      final effectiveBypassSubnets = _effectiveExcludedRouteValues(
        bypassSubnets: storedBypassSubnets,
        excludedRouteEntries: effectiveExcludedRouteEntries,
      );

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
            _prefs.getBool(_kAutoConnectOnLaunch) ??
            defaults.autoConnectOnLaunch,
        autoConnectUntrustedWifi:
            _prefs.getBool(_kAutoConnectUntrustedWifi) ??
            defaults.autoConnectUntrustedWifi,
        killSwitch: _prefs.getBool(_kKillSwitch) ?? defaults.killSwitch,
        routingEnabled:
            _prefs.getBool(_kRoutingEnabled) ?? defaults.routingEnabled,
        routingProfiles: _readRoutingProfiles(
          _prefs.getString(_kRoutingProfiles),
        ),
        activeRoutingProfileId:
            _prefs.getString(_kActiveRoutingProfileId) ??
            defaults.activeRoutingProfileId,
        bypassSubnets: effectiveBypassSubnets.isEmpty
            ? defaults.bypassSubnets
            : effectiveBypassSubnets,
        excludedRouteEntries: effectiveExcludedRouteEntries,
        splitTunneling:
            _prefs.getBool(_kSplitTunneling) ?? defaults.splitTunneling,
        perAppProxyMode: _readEnum(
          _prefs.getString(_kPerAppProxyMode),
          PerAppProxyMode.values,
          defaults.perAppProxyMode,
        ),
        perAppProxyAppIds:
            _prefs.getStringList(_kPerAppProxyAppIds) ??
            defaults.perAppProxyAppIds,
        dnsProvider: _readEnum(
          _prefs.getString(_kDnsProvider),
          DnsProvider.values,
          defaults.dnsProvider,
        ),
        customDns: _prefs.getString(_kCustomDns) ?? defaults.customDns,
        useLocalDns: _prefs.getBool(_kUseLocalDns) ?? defaults.useLocalDns,
        localDnsPort: _prefs.getInt(_kLocalDnsPort) ?? defaults.localDnsPort,
        useDnsFromJson:
            _prefs.getBool(_kUseDnsFromJson) ?? defaults.useDnsFromJson,
        fragmentationEnabled:
            _prefs.getBool(_kFragmentationEnabled) ??
            defaults.fragmentationEnabled,
        muxEnabled: _prefs.getBool(_kMuxEnabled) ?? defaults.muxEnabled,
        preferredIpType: _readEnum(
          _prefs.getString(_kPreferredIpType),
          PreferredIpType.values,
          defaults.preferredIpType,
        ),
        sniffingEnabled:
            _prefs.getBool(_kSniffingEnabled) ?? defaults.sniffingEnabled,
        vpnRunMode: _readEnum(
          _prefs.getString(_kVpnRunMode),
          VpnRunMode.values,
          defaults.vpnRunMode,
        ),
        serverAddressResolveEnabled:
            _prefs.getBool(_kServerAddressResolveEnabled) ??
            defaults.serverAddressResolveEnabled,
        serverAddressResolveDohUrl:
            _prefs.getString(_kServerAddressResolveDohUrl) ??
            defaults.serverAddressResolveDohUrl,
        serverAddressResolveDnsIp:
            _prefs.getString(_kServerAddressResolveDnsIp) ??
            defaults.serverAddressResolveDnsIp,
        pingMode: _readEnum(
          _prefs.getString(_kPingMode),
          PingMode.values,
          defaults.pingMode,
        ),
        pingTestUrl: _prefs.getString(_kPingTestUrl) ?? defaults.pingTestUrl,
        pingDisplayMode: _readEnum(
          _prefs.getString(_kPingDisplayMode),
          PingDisplayMode.values,
          defaults.pingDisplayMode,
        ),
        pingResultMode: _readPingResultMode(_prefs, defaults.pingResultMode),
        mtuMode: _readEnum(
          _prefs.getString(_kMtuMode),
          MtuMode.values,
          defaults.mtuMode,
        ),
        mtuValue: _prefs.getInt(_kMtuValue) ?? defaults.mtuValue,
        subscriptionAutoUpdateEnabled:
            _prefs.getBool(_kSubscriptionAutoUpdateEnabled) ??
            defaults.subscriptionAutoUpdateEnabled,
        subscriptionAutoUpdateIntervalHours:
            _prefs.getInt(_kSubscriptionAutoUpdateIntervalHours) ??
            defaults.subscriptionAutoUpdateIntervalHours,
        subscriptionUpdateNotificationsEnabled:
            _prefs.getBool(_kSubscriptionUpdateNotificationsEnabled) ??
            defaults.subscriptionUpdateNotificationsEnabled,
        subscriptionAutoUpdateOnOpen:
            _prefs.getBool(_kSubscriptionAutoUpdateOnOpen) ??
            defaults.subscriptionAutoUpdateOnOpen,
        subscriptionPingOnOpenEnabled:
            _prefs.getBool(_kSubscriptionPingOnOpenEnabled) ??
            defaults.subscriptionPingOnOpenEnabled,
        subscriptionConnectStrategy: _readEnum(
          _prefs.getString(_kSubscriptionConnectStrategy),
          SubscriptionConnectStrategy.values,
          defaults.subscriptionConnectStrategy,
        ),
        preventDuplicateImports:
            _prefs.getBool(_kPreventDuplicateImports) ??
            defaults.preventDuplicateImports,
        collapseSubscriptions:
            _prefs.getBool(_kCollapseSubscriptions) ??
            defaults.collapseSubscriptions,
        subscriptionNoFilter:
            _prefs.getBool(_kSubscriptionNoFilter) ??
            defaults.subscriptionNoFilter,
        subscriptionUserAgentMode: _readEnum(
          _prefs.getString(_kSubscriptionUserAgentMode),
          SubscriptionUserAgentMode.values,
          defaults.subscriptionUserAgentMode,
        ),
        subscriptionUserAgentValue:
            _prefs.getString(_kSubscriptionUserAgentValue) ??
            defaults.subscriptionUserAgentValue,
        subscriptionSortMode: _readEnum(
          _prefs.getString(_kSubscriptionSortMode),
          SubscriptionSortMode.values,
          defaults.subscriptionSortMode,
        ),
        allowLanConnections:
            _prefs.getBool(_kAllowLanConnections) ??
            defaults.allowLanConnections,
        appAutoStart: _prefs.getBool(_kAppAutoStart) ?? defaults.appAutoStart,
        locale: _prefs.getString(_kLocale) ?? defaults.locale,
        notificationConnection:
            _prefs.getBool(_kNotificationConnection) ??
            defaults.notificationConnection,
        notificationExpiry:
            _prefs.getBool(_kNotificationExpiry) ?? defaults.notificationExpiry,
        notificationPromotional:
            _prefs.getBool(_kNotificationPromotional) ??
            defaults.notificationPromotional,
        notificationReferral:
            _prefs.getBool(_kNotificationReferral) ??
            defaults.notificationReferral,
        notificationVpnSpeed:
            _prefs.getBool(_kNotificationVpnSpeed) ??
            defaults.notificationVpnSpeed,
        preferMapView:
            _prefs.getBool(_kPreferMapView) ?? defaults.preferMapView,
        clipboardAutoDetect:
            _prefs.getBool(_kClipboardAutoDetect) ??
            defaults.clipboardAutoDetect,
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
        _kPreferredProtocol,
        settings.preferredProtocol.name,
      );
      await _prefs.setBool(_kAutoConnectOnLaunch, settings.autoConnectOnLaunch);
      await _prefs.setBool(
        _kAutoConnectUntrustedWifi,
        settings.autoConnectUntrustedWifi,
      );
      await _prefs.setBool(_kKillSwitch, settings.killSwitch);
      await _prefs.setBool(_kRoutingEnabled, settings.routingEnabled);
      await _prefs.setString(
        _kRoutingProfiles,
        jsonEncode(
          settings.routingProfiles
              .map((profile) => profile.toStorageJson())
              .toList(),
        ),
      );
      if (settings.activeRoutingProfileId != null) {
        await _prefs.setString(
          _kActiveRoutingProfileId,
          settings.activeRoutingProfileId!,
        );
      } else {
        await _prefs.remove(_kActiveRoutingProfileId);
      }
      final excludedRouteEntries = _normalizeExcludedRouteEntries(
        settings.excludedRouteEntries,
      );
      final bypassSubnets = _effectiveExcludedRouteValues(
        bypassSubnets: _normalizeStringList(settings.bypassSubnets),
        excludedRouteEntries: excludedRouteEntries,
      );
      await _prefs.setStringList(_kBypassSubnets, bypassSubnets);
      await _prefs.setString(
        _kExcludedRouteEntries,
        jsonEncode(
          excludedRouteEntries.map((entry) => entry.toStorageJson()).toList(),
        ),
      );
      await _prefs.setBool(_kSplitTunneling, settings.splitTunneling);
      await _prefs.setString(_kPerAppProxyMode, settings.perAppProxyMode.name);
      await _prefs.setStringList(
        _kPerAppProxyAppIds,
        settings.perAppProxyAppIds,
      );
      await _prefs.setString(_kDnsProvider, settings.dnsProvider.name);
      if (settings.customDns != null) {
        await _prefs.setString(_kCustomDns, settings.customDns!);
      } else {
        await _prefs.remove(_kCustomDns);
      }
      await _prefs.setBool(_kUseLocalDns, settings.useLocalDns);
      await _prefs.setInt(_kLocalDnsPort, settings.localDnsPort);
      await _prefs.setBool(_kUseDnsFromJson, settings.useDnsFromJson);
      await _prefs.setBool(
        _kFragmentationEnabled,
        settings.fragmentationEnabled,
      );
      await _prefs.setBool(_kMuxEnabled, settings.muxEnabled);
      await _prefs.setString(_kPreferredIpType, settings.preferredIpType.name);
      await _prefs.setBool(_kSniffingEnabled, settings.sniffingEnabled);
      await _prefs.setString(_kVpnRunMode, settings.vpnRunMode.name);
      await _prefs.setBool(
        _kServerAddressResolveEnabled,
        settings.serverAddressResolveEnabled,
      );
      if (settings.serverAddressResolveDohUrl != null) {
        await _prefs.setString(
          _kServerAddressResolveDohUrl,
          settings.serverAddressResolveDohUrl!,
        );
      } else {
        await _prefs.remove(_kServerAddressResolveDohUrl);
      }
      if (settings.serverAddressResolveDnsIp != null) {
        await _prefs.setString(
          _kServerAddressResolveDnsIp,
          settings.serverAddressResolveDnsIp!,
        );
      } else {
        await _prefs.remove(_kServerAddressResolveDnsIp);
      }
      await _prefs.setString(_kPingMode, settings.pingMode.name);
      await _prefs.setString(_kPingTestUrl, settings.pingTestUrl);
      await _prefs.setString(_kPingDisplayMode, settings.pingDisplayMode.name);
      await _prefs.setString(_kPingResultMode, settings.pingResultMode.name);
      await _prefs.setString(_kMtuMode, settings.mtuMode.name);
      await _prefs.setInt(_kMtuValue, settings.mtuValue);
      await _prefs.setBool(
        _kSubscriptionAutoUpdateEnabled,
        settings.subscriptionAutoUpdateEnabled,
      );
      await _prefs.setInt(
        _kSubscriptionAutoUpdateIntervalHours,
        settings.subscriptionAutoUpdateIntervalHours,
      );
      await _prefs.setBool(
        _kSubscriptionUpdateNotificationsEnabled,
        settings.subscriptionUpdateNotificationsEnabled,
      );
      await _prefs.setBool(
        _kSubscriptionAutoUpdateOnOpen,
        settings.subscriptionAutoUpdateOnOpen,
      );
      await _prefs.setBool(
        _kSubscriptionPingOnOpenEnabled,
        settings.subscriptionPingOnOpenEnabled,
      );
      await _prefs.setString(
        _kSubscriptionConnectStrategy,
        settings.subscriptionConnectStrategy.name,
      );
      await _prefs.setBool(
        _kPreventDuplicateImports,
        settings.preventDuplicateImports,
      );
      await _prefs.setBool(
        _kCollapseSubscriptions,
        settings.collapseSubscriptions,
      );
      await _prefs.setBool(
        _kSubscriptionNoFilter,
        settings.subscriptionNoFilter,
      );
      await _prefs.setString(
        _kSubscriptionUserAgentMode,
        settings.subscriptionUserAgentMode.name,
      );
      if (settings.subscriptionUserAgentValue != null) {
        await _prefs.setString(
          _kSubscriptionUserAgentValue,
          settings.subscriptionUserAgentValue!,
        );
      } else {
        await _prefs.remove(_kSubscriptionUserAgentValue);
      }
      await _prefs.setString(
        _kSubscriptionSortMode,
        settings.subscriptionSortMode.name,
      );
      await _prefs.setBool(_kAllowLanConnections, settings.allowLanConnections);
      await _prefs.setBool(_kAppAutoStart, settings.appAutoStart);
      await _prefs.setString(_kLocale, settings.locale);
      await _prefs.setBool(
        _kNotificationConnection,
        settings.notificationConnection,
      );
      await _prefs.setBool(_kNotificationExpiry, settings.notificationExpiry);
      await _prefs.setBool(
        _kNotificationPromotional,
        settings.notificationPromotional,
      );
      await _prefs.setBool(
        _kNotificationReferral,
        settings.notificationReferral,
      );
      await _prefs.setBool(
        _kNotificationVpnSpeed,
        settings.notificationVpnSpeed,
      );
      await _prefs.setBool(_kPreferMapView, settings.preferMapView);
      await _prefs.setBool(_kClipboardAutoDetect, settings.clipboardAutoDetect);
      await _prefs.setBool(_kHapticsEnabled, settings.hapticsEnabled);
      await _prefs.setStringList(
        _kTrustedWifiNetworks,
        settings.trustedWifiNetworks,
      );
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
