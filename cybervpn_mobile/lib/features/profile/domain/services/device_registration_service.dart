import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/register_device.dart';

/// Service for managing device registration with the backend.
///
/// Handles:
/// - Detecting current device information
/// - Checking if device is already registered
/// - Auto-registering device on first VPN connection
class DeviceRegistrationService {
  final RegisterDeviceUseCase _registerDevice;
  final SecureStorageWrapper _storage;

  static const String _deviceRegisteredKey = 'device_registered';
  static const String _deviceIdKey = 'current_device_id';

  const DeviceRegistrationService({
    required RegisterDeviceUseCase registerDevice,
    required SecureStorageWrapper storage,
  })  : _registerDevice = registerDevice,
        _storage = storage;

  /// Check if the current device is registered with the backend.
  Future<bool> isDeviceRegistered() async {
    try {
      final registered = await _storage.read(key: _deviceRegisteredKey);
      return registered == 'true';
    } catch (e) {
      AppLogger.warning('Failed to check device registration status', error: e);
      return false;
    }
  }

  /// Get the stored device ID for the current device.
  Future<String?> getStoredDeviceId() async {
    try {
      return await _storage.read(key: _deviceIdKey);
    } catch (e) {
      AppLogger.warning('Failed to get stored device ID', error: e);
      return null;
    }
  }

  /// Get the current device ID from the platform.
  Future<String?> getCurrentDeviceId() async {
    try {
      final deviceInfo = DeviceInfoPlugin();

      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        return androidInfo.id;
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        return iosInfo.identifierForVendor;
      }

      return null;
    } catch (e, st) {
      AppLogger.error('Failed to get device ID', error: e, stackTrace: st);
      return null;
    }
  }

  /// Get a human-readable device name.
  Future<String> getDeviceName() async {
    try {
      final deviceInfo = DeviceInfoPlugin();

      if (Platform.isAndroid) {
        final androidInfo = await deviceInfo.androidInfo;
        final manufacturer = androidInfo.manufacturer;
        final model = androidInfo.model;
        return '$manufacturer $model';
      } else if (Platform.isIOS) {
        final iosInfo = await deviceInfo.iosInfo;
        return iosInfo.utsname.machine;
      }

      return 'Unknown Device';
    } catch (e, st) {
      AppLogger.error('Failed to get device name', error: e, stackTrace: st);
      return 'Unknown Device';
    }
  }

  /// Get the platform name.
  String getPlatform() {
    if (Platform.isAndroid) {
      return 'Android';
    } else if (Platform.isIOS) {
      return 'iOS';
    } else if (Platform.isMacOS) {
      return 'macOS';
    } else if (Platform.isWindows) {
      return 'Windows';
    } else if (Platform.isLinux) {
      return 'Linux';
    }
    return 'Unknown';
  }

  /// Register the current device with the backend.
  ///
  /// Should be called on first VPN connection.
  /// Stores registration status locally to avoid duplicate registrations.
  ///
  /// Returns the registered [Device] or null if registration failed.
  Future<Device?> registerCurrentDevice() async {
    try {
      // Check if already registered
      if (await isDeviceRegistered()) {
        AppLogger.info('Device already registered, skipping');
        return null;
      }

      final deviceId = await getCurrentDeviceId();
      if (deviceId == null) {
        AppLogger.error('Cannot register device: device ID is null');
        return null;
      }

      final deviceName = await getDeviceName();
      final platform = getPlatform();

      AppLogger.info('Registering device: $deviceName ($platform)');

      final device = await _registerDevice.call(
        deviceName: deviceName,
        platform: platform,
        deviceId: deviceId,
      );

      // Mark as registered locally
      await _storage.write(key: _deviceRegisteredKey, value: 'true');
      await _storage.write(key: _deviceIdKey, value: deviceId);

      AppLogger.info('Device registered successfully: ${device.id}');

      return device;
    } catch (e, st) {
      AppLogger.error(
        'Failed to register device',
        error: e,
        stackTrace: st,
      );
      return null;
    }
  }

  /// Clear the device registration status (for testing or logout).
  Future<void> clearRegistration() async {
    try {
      await _storage.delete(key: _deviceRegisteredKey);
      await _storage.delete(key: _deviceIdKey);
      AppLogger.info('Device registration cleared');
    } catch (e) {
      AppLogger.warning('Failed to clear device registration', error: e);
    }
  }
}
