import 'dart:async';
import 'dart:io' show Platform;

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:network_info_plus/network_info_plus.dart';
import 'package:permission_handler/permission_handler.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// WiFi Info Model
// ---------------------------------------------------------------------------

/// Represents current WiFi connection information.
class WifiInfo {
  const WifiInfo({
    this.ssid,
    this.bssid,
    this.isConnectedToWifi = false,
  });

  /// The network SSID (name). May contain surrounding quotes on Android.
  /// Null if not connected to WiFi or permissions denied.
  final String? ssid;

  /// The network BSSID (MAC address).
  final String? bssid;

  /// Whether the device is currently connected to a WiFi network.
  final bool isConnectedToWifi;

  /// Returns the SSID without surrounding quotes (Android adds these).
  String? get cleanSsid {
    if (ssid == null) return null;
    // Android returns SSID wrapped in quotes like "MyNetwork"
    return ssid!.replaceAll(RegExp(r'^"|"$'), '');
  }

  /// Returns true if we have valid SSID information.
  bool get hasValidSsid => cleanSsid != null && cleanSsid!.isNotEmpty;

  @override
  String toString() =>
      'WifiInfo(ssid: $ssid, bssid: $bssid, isConnectedToWifi: $isConnectedToWifi)';

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is WifiInfo &&
        other.ssid == ssid &&
        other.bssid == bssid &&
        other.isConnectedToWifi == isConnectedToWifi;
  }

  @override
  int get hashCode => Object.hash(ssid, bssid, isConnectedToWifi);
}

/// Represents the permission status for WiFi SSID access.
enum WifiPermissionStatus {
  /// Permission granted - can access WiFi SSID.
  granted,

  /// Permission denied - user declined.
  denied,

  /// Permission permanently denied - must go to settings.
  permanentlyDenied,

  /// Permission restricted (iOS parental controls).
  restricted,

  /// Platform doesn't support SSID access.
  unsupported,
}

// ---------------------------------------------------------------------------
// WiFi Monitor Service
// ---------------------------------------------------------------------------

/// Service for monitoring WiFi connection changes and detecting SSID.
///
/// Platform requirements:
/// - Android: Requires ACCESS_FINE_LOCATION permission for SSID access.
/// - iOS: Requires Access WiFi Information entitlement and location permission.
///   Note: iOS 13+ has significant restrictions on SSID access.
/// - Web: Not supported.
///
/// Usage:
/// ```dart
/// final service = ref.read(wifiMonitorServiceProvider);
/// final info = await service.getCurrentWifiInfo();
/// print('Connected to: ${info.cleanSsid}');
/// ```
class WifiMonitorService {
  WifiMonitorService({
    Connectivity? connectivity,
    NetworkInfo? networkInfo,
  })  : _connectivity = connectivity ?? Connectivity(),
        _networkInfo = networkInfo ?? NetworkInfo();

  final Connectivity _connectivity;
  final NetworkInfo _networkInfo;

  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;
  final _wifiInfoController = StreamController<WifiInfo>.broadcast();

  /// Stream of WiFi info changes.
  ///
  /// Emits a new [WifiInfo] whenever the WiFi connection changes.
  Stream<WifiInfo> get onWifiChanged => _wifiInfoController.stream;

  /// Check if the platform supports WiFi SSID detection.
  bool get isSupported {
    if (kIsWeb) return false;
    try {
      return Platform.isAndroid || Platform.isIOS;
    } catch (_) {
      return false;
    }
  }

  /// Start monitoring WiFi changes.
  ///
  /// Call this once when the app starts if auto-connect on untrusted WiFi
  /// is enabled.
  void startMonitoring() {
    unawaited(_connectivitySubscription?.cancel());
    _connectivitySubscription = _connectivity.onConnectivityChanged.listen(
      _onConnectivityChanged,
      onError: (Object e) {
        AppLogger.error('WiFi monitor connectivity error', error: e);
      },
    );
    AppLogger.info('WiFi monitor started', category: 'network.wifi');
  }

  /// Stop monitoring WiFi changes.
  void stopMonitoring() {
    unawaited(_connectivitySubscription?.cancel());
    _connectivitySubscription = null;
    AppLogger.info('WiFi monitor stopped', category: 'network.wifi');
  }

  /// Handle connectivity changes and fetch WiFi info.
  Future<void> _onConnectivityChanged(List<ConnectivityResult> results) async {
    final isWifi = results.contains(ConnectivityResult.wifi);

    if (isWifi) {
      final info = await getCurrentWifiInfo();
      _wifiInfoController.add(info);
      AppLogger.debug(
        'WiFi connection detected: ${info.cleanSsid ?? "unknown"}',
        category: 'network.wifi',
      );
    } else {
      _wifiInfoController.add(const WifiInfo(isConnectedToWifi: false));
      AppLogger.debug('WiFi disconnected', category: 'network.wifi');
    }
  }

  /// Get current WiFi connection information.
  ///
  /// Returns a [WifiInfo] with SSID and BSSID if available.
  /// The SSID may be null if:
  /// - Not connected to WiFi
  /// - Location permission not granted
  /// - Platform restrictions (iOS 13+)
  Future<WifiInfo> getCurrentWifiInfo() async {
    if (!isSupported) {
      return const WifiInfo();
    }

    try {
      final results = await _connectivity.checkConnectivity();
      final isWifi = results.contains(ConnectivityResult.wifi);

      if (!isWifi) {
        return const WifiInfo(isConnectedToWifi: false);
      }

      // Try to get SSID (requires permission)
      final ssid = await _networkInfo.getWifiName();
      final bssid = await _networkInfo.getWifiBSSID();

      return WifiInfo(
        ssid: ssid,
        bssid: bssid,
        isConnectedToWifi: true,
      );
    } catch (e) {
      AppLogger.error('Failed to get WiFi info', error: e);
      return const WifiInfo(isConnectedToWifi: true);
    }
  }

  /// Check if we have permission to access WiFi SSID.
  Future<WifiPermissionStatus> checkPermission() async {
    if (!isSupported) {
      return WifiPermissionStatus.unsupported;
    }

    try {
      if (Platform.isAndroid) {
        // Android requires location permission for WiFi SSID
        final status = await Permission.locationWhenInUse.status;
        return _mapPermissionStatus(status);
      }

      if (Platform.isIOS) {
        // iOS requires location permission
        final status = await Permission.locationWhenInUse.status;
        return _mapPermissionStatus(status);
      }

      return WifiPermissionStatus.unsupported;
    } catch (e) {
      AppLogger.error('Failed to check WiFi permission', error: e);
      return WifiPermissionStatus.denied;
    }
  }

  /// Request permission to access WiFi SSID.
  ///
  /// Returns the new permission status after the request.
  Future<WifiPermissionStatus> requestPermission() async {
    if (!isSupported) {
      return WifiPermissionStatus.unsupported;
    }

    try {
      final status = await Permission.locationWhenInUse.request();
      final result = _mapPermissionStatus(status);

      AppLogger.info(
        'WiFi permission request result: ${result.name}',
        category: 'network.wifi',
      );

      return result;
    } catch (e) {
      AppLogger.error('Failed to request WiFi permission', error: e);
      return WifiPermissionStatus.denied;
    }
  }

  WifiPermissionStatus _mapPermissionStatus(PermissionStatus status) {
    return switch (status) {
      PermissionStatus.granted ||
      PermissionStatus.limited =>
        WifiPermissionStatus.granted,
      PermissionStatus.denied => WifiPermissionStatus.denied,
      PermissionStatus.permanentlyDenied =>
        WifiPermissionStatus.permanentlyDenied,
      PermissionStatus.restricted => WifiPermissionStatus.restricted,
      PermissionStatus.provisional => WifiPermissionStatus.denied,
    };
  }

  /// Open app settings for the user to manually grant permission.
  Future<bool> openAppSettings() async {
    return openAppSettings();
  }

  /// Dispose resources.
  void dispose() {
    stopMonitoring();
    unawaited(_wifiInfoController.close());
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provides the [WifiMonitorService] instance.
final wifiMonitorServiceProvider = Provider<WifiMonitorService>((ref) {
  final service = WifiMonitorService();
  ref.onDispose(service.dispose);
  return service;
});

/// Stream provider for current WiFi info changes.
final wifiInfoStreamProvider = StreamProvider<WifiInfo>((ref) {
  final service = ref.watch(wifiMonitorServiceProvider);
  return service.onWifiChanged;
});

/// Provider that returns the current WiFi permission status.
final wifiPermissionStatusProvider = FutureProvider<WifiPermissionStatus>((ref) {
  final service = ref.watch(wifiMonitorServiceProvider);
  return service.checkPermission();
});
