import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb, visibleForTesting;
import 'package:flutter/services.dart';
import 'package:network_info_plus/network_info_plus.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class LanProxyStatus {
  const LanProxyStatus({
    required this.isSupported,
    required this.enabled,
    required this.socksPort,
    required this.httpPort,
    this.wifiIpv4,
    this.wifiIpv6,
  });

  const LanProxyStatus.unsupported({required this.enabled})
    : isSupported = false,
      socksPort = 10807,
      httpPort = 10808,
      wifiIpv4 = null,
      wifiIpv6 = null;

  final bool isSupported;
  final bool enabled;
  final int socksPort;
  final int httpPort;
  final String? wifiIpv4;
  final String? wifiIpv6;

  bool get hasWifiAddress =>
      (wifiIpv4 != null && wifiIpv4!.isNotEmpty) ||
      (wifiIpv6 != null && wifiIpv6!.isNotEmpty);
}

class AppAutoStartStatus {
  const AppAutoStartStatus({
    required this.isSupported,
    required this.enabled,
    required this.bootReceiverReady,
    required this.oemSettingsAvailable,
    required this.batteryOptimizationIgnored,
    required this.manufacturer,
    this.lastBootHandledAt,
  });

  const AppAutoStartStatus.unsupported({required this.enabled})
    : isSupported = false,
      bootReceiverReady = false,
      oemSettingsAvailable = false,
      batteryOptimizationIgnored = false,
      manufacturer = 'unsupported',
      lastBootHandledAt = null;

  final bool isSupported;
  final bool enabled;
  final bool bootReceiverReady;
  final bool oemSettingsAvailable;
  final bool batteryOptimizationIgnored;
  final String manufacturer;
  final DateTime? lastBootHandledAt;
}

abstract class AndroidSystemIntegrationService {
  bool get isSupported;
  Future<LanProxyStatus> readLanProxyStatus({required bool enabled});
  Future<AppAutoStartStatus> readAppAutoStartStatus({required bool enabled});
  Future<void> syncAppAutoStartPreference(bool enabled);
  Future<bool> openAppAutoStartSettings();
  Future<bool> openBatteryOptimizationSettings();
}

class MethodChannelAndroidSystemIntegrationService
    implements AndroidSystemIntegrationService {
  MethodChannelAndroidSystemIntegrationService({
    NetworkInfo? networkInfo,
    Future<String?> Function()? wifiIpLoader,
    Future<String?> Function()? wifiIpv6Loader,
  }) : _networkInfo = networkInfo ?? NetworkInfo(),
       _wifiIpLoader = wifiIpLoader,
       _wifiIpv6Loader = wifiIpv6Loader;

  static const MethodChannel _channel = MethodChannel(
    'com.cybervpn.cybervpn_mobile/android_system',
  );

  @visibleForTesting
  static bool? debugIsSupportedOverride;

  final NetworkInfo _networkInfo;
  final Future<String?> Function()? _wifiIpLoader;
  final Future<String?> Function()? _wifiIpv6Loader;

  @override
  bool get isSupported {
    final override = debugIsSupportedOverride;
    if (override != null) {
      return override;
    }

    if (kIsWeb) {
      return false;
    }

    return Platform.isAndroid;
  }

  @override
  Future<LanProxyStatus> readLanProxyStatus({required bool enabled}) async {
    if (!isSupported) {
      return LanProxyStatus.unsupported(enabled: enabled);
    }

    try {
      final statusMap = await _channel.invokeMapMethod<String, dynamic>(
        'getLanProxyStatus',
      );
      final addresses = await Future.wait<String?>([
        _safeWifiLookup(_wifiIpLoader ?? _networkInfo.getWifiIP),
        _safeWifiLookup(_wifiIpv6Loader ?? _networkInfo.getWifiIPv6),
      ]);

      return LanProxyStatus(
        isSupported: true,
        enabled: enabled,
        socksPort: (statusMap?['socksPort'] as num?)?.toInt() ?? 10807,
        httpPort: (statusMap?['httpPort'] as num?)?.toInt() ?? 10808,
        wifiIpv4: addresses[0],
        wifiIpv6: addresses[1],
      );
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Failed to read LAN proxy status',
        error: error,
        stackTrace: stackTrace,
      );
      return LanProxyStatus.unsupported(enabled: enabled);
    }
  }

  @override
  Future<AppAutoStartStatus> readAppAutoStartStatus({
    required bool enabled,
  }) async {
    if (!isSupported) {
      return AppAutoStartStatus.unsupported(enabled: enabled);
    }

    try {
      final statusMap = await _channel.invokeMapMethod<String, dynamic>(
        'getAppAutoStartStatus',
      );
      final lastBootHandledAtMs =
          (statusMap?['lastBootHandledAtMs'] as num?)?.toInt();

      return AppAutoStartStatus(
        isSupported: true,
        enabled: enabled,
        bootReceiverReady: statusMap?['bootReceiverReady'] as bool? ?? false,
        oemSettingsAvailable:
            statusMap?['oemSettingsAvailable'] as bool? ?? false,
        batteryOptimizationIgnored:
            statusMap?['batteryOptimizationIgnored'] as bool? ?? false,
        manufacturer:
            (statusMap?['manufacturer'] as String?)?.trim().isNotEmpty == true
            ? statusMap!['manufacturer'] as String
            : 'android',
        lastBootHandledAt: lastBootHandledAtMs == null || lastBootHandledAtMs <= 0
            ? null
            : DateTime.fromMillisecondsSinceEpoch(lastBootHandledAtMs),
      );
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Failed to read app auto-start status',
        error: error,
        stackTrace: stackTrace,
      );
      return AppAutoStartStatus.unsupported(enabled: enabled);
    }
  }

  @override
  Future<void> syncAppAutoStartPreference(bool enabled) async {
    if (!isSupported) {
      return;
    }

    try {
      await _channel.invokeMethod<void>('setAppAutoStartEnabled', {
        'enabled': enabled,
      });
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Failed to sync app auto-start preference',
        error: error,
        stackTrace: stackTrace,
      );
    }
  }

  @override
  Future<bool> openAppAutoStartSettings() async {
    if (!isSupported) {
      return false;
    }

    try {
      return await _channel.invokeMethod<bool>('openAppAutoStartSettings') ??
          false;
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Failed to open app auto-start settings',
        error: error,
        stackTrace: stackTrace,
      );
      return false;
    }
  }

  @override
  Future<bool> openBatteryOptimizationSettings() async {
    if (!isSupported) {
      return false;
    }

    try {
      return await _channel.invokeMethod<bool>(
            'openBatteryOptimizationSettings',
          ) ??
          false;
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Failed to open battery optimization settings',
        error: error,
        stackTrace: stackTrace,
      );
      return false;
    }
  }

  Future<String?> _safeWifiLookup(Future<String?> Function() loader) async {
    try {
      final value = await loader();
      final trimmed = value?.trim();
      return trimmed == null || trimmed.isEmpty ? null : trimmed;
    } catch (error, stackTrace) {
      AppLogger.debug(
        'WiFi address lookup skipped',
        category: 'settings.android',
        data: {'error': error.toString(), 'stackTrace': stackTrace.toString()},
      );
      return null;
    }
  }
}
