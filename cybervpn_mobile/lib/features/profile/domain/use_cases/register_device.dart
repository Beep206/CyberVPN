import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for registering the current device
///
/// Registers the device with the backend so it appears in the user's device list.
/// Should be called on first VPN connection or when device is not yet registered.
@immutable
class RegisterDeviceUseCase {
  final ProfileRepository _repository;

  const RegisterDeviceUseCase(this._repository);

  /// Registers the current device with the backend.
  ///
  /// Parameters:
  /// - [deviceName]: Human-readable device name (e.g., "iPhone 15 Pro")
  /// - [platform]: Platform identifier (e.g., "iOS", "Android")
  /// - [deviceId]: Unique device identifier
  ///
  /// Returns the registered [Device] entity.
  ///
  /// Throws [ArgumentError] if any parameter is empty.
  Future<Result<Device>> call({
    required String deviceName,
    required String platform,
    required String deviceId,
  }) async {
    if (deviceName.isEmpty) {
      throw ArgumentError('Device name must not be empty');
    }
    if (platform.isEmpty) {
      throw ArgumentError('Platform must not be empty');
    }
    if (deviceId.isEmpty) {
      throw ArgumentError('Device ID must not be empty');
    }

    return _repository.registerDevice(
      deviceName: deviceName,
      platform: platform,
      deviceId: deviceId,
    );
  }
}
