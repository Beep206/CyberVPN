import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:package_info_plus/package_info_plus.dart';

import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Service for collecting and managing device information.
///
/// Provides device info for authentication requests and session management.
/// Uses SecureStorage to persist device_id across app launches.
class DeviceService {
  final SecureStorageWrapper _storage;
  final DeviceInfoPlugin _deviceInfo;

  DeviceInfo? _cachedDeviceInfo;
  String? _cachedPushToken;

  DeviceService({
    required SecureStorageWrapper storage,
    DeviceInfoPlugin? deviceInfo,
  })  : _storage = storage,
        _deviceInfo = deviceInfo ?? DeviceInfoPlugin();

  /// Gets the current device information for auth requests.
  ///
  /// Caches the result for performance. Call [clearCache] to refresh.
  /// The [pushToken] parameter allows setting FCM token.
  Future<DeviceInfo> getDeviceInfo({String? pushToken}) async {
    if (_cachedDeviceInfo != null && pushToken == _cachedPushToken) {
      return _cachedDeviceInfo!;
    }

    try {
      // Get or create persistent device ID
      final deviceId = await _storage.getOrCreateDeviceId();

      // Get platform-specific info
      final platform = _getPlatform();
      final platformId = await _getPlatformId();
      final osVersion = await _getOsVersion();
      final deviceModel = await _getDeviceModel();
      final appVersion = await _getAppVersion();

      _cachedDeviceInfo = DeviceInfo(
        deviceId: deviceId,
        platform: platform,
        platformId: platformId,
        osVersion: osVersion,
        appVersion: appVersion,
        deviceModel: deviceModel,
        pushToken: pushToken,
      );
      _cachedPushToken = pushToken;

      AppLogger.info('Device info collected: $deviceModel ($platform)');

      return _cachedDeviceInfo!;
    } catch (e, st) {
      AppLogger.error('Failed to collect device info', error: e, stackTrace: st);
      rethrow;
    }
  }

  /// Updates the push token and returns updated device info.
  Future<DeviceInfo> updatePushToken(String pushToken) async {
    _cachedPushToken = pushToken;
    if (_cachedDeviceInfo != null) {
      _cachedDeviceInfo = _cachedDeviceInfo!.copyWith(pushToken: pushToken);
      return _cachedDeviceInfo!;
    }
    return getDeviceInfo(pushToken: pushToken);
  }

  /// Clears cached device info. Call to refresh on next [getDeviceInfo].
  void clearCache() {
    _cachedDeviceInfo = null;
    _cachedPushToken = null;
  }

  /// Gets the persistent device ID.
  Future<String> getDeviceId() async {
    return _storage.getOrCreateDeviceId();
  }

  DevicePlatform _getPlatform() {
    if (Platform.isIOS) {
      return DevicePlatform.ios;
    } else if (Platform.isAndroid) {
      return DevicePlatform.android;
    }
    // Default to android for other platforms (should not happen in mobile)
    return DevicePlatform.android;
  }

  Future<String> _getPlatformId() async {
    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        // Android ID - unique per app signing key
        return androidInfo.id;
      } else if (Platform.isIOS) {
        final iosInfo = await _deviceInfo.iosInfo;
        // identifierForVendor - unique per vendor
        return iosInfo.identifierForVendor ?? 'unknown';
      }
    } catch (e) {
      AppLogger.warning('Failed to get platform ID', error: e);
    }
    return 'unknown';
  }

  Future<String> _getOsVersion() async {
    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        return androidInfo.version.release;
      } else if (Platform.isIOS) {
        final iosInfo = await _deviceInfo.iosInfo;
        return iosInfo.systemVersion;
      }
    } catch (e) {
      AppLogger.warning('Failed to get OS version', error: e);
    }
    return 'unknown';
  }

  Future<String> _getDeviceModel() async {
    try {
      if (Platform.isAndroid) {
        final androidInfo = await _deviceInfo.androidInfo;
        final manufacturer = androidInfo.manufacturer;
        final model = androidInfo.model;
        return '$manufacturer $model';
      } else if (Platform.isIOS) {
        final iosInfo = await _deviceInfo.iosInfo;
        // Return human-readable model name
        return iosInfo.utsname.machine;
      }
    } catch (e) {
      AppLogger.warning('Failed to get device model', error: e);
    }
    return 'Unknown Device';
  }

  Future<String> _getAppVersion() async {
    try {
      final packageInfo = await PackageInfo.fromPlatform();
      return packageInfo.version;
    } catch (e) {
      AppLogger.warning('Failed to get app version', error: e);
    }
    return '1.0.0';
  }
}
