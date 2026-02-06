import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for revoking a device session
///
/// Removes the specified device session, logging it out remotely.
/// Prevents the user from removing their current device session.
@immutable
class RemoveDeviceUseCase {
  final ProfileRepository _repository;

  const RemoveDeviceUseCase(this._repository);

  /// Removes the device session with the given [deviceId].
  ///
  /// Throws [ArgumentError] if [deviceId] is empty.
  /// Throws [StateError] if attempting to remove the current device
  /// (identified by [currentDeviceId]).
  Future<Result<void>> call({
    required String deviceId,
    required String currentDeviceId,
  }) async {
    if (deviceId.isEmpty) {
      throw ArgumentError('Device ID must not be empty');
    }
    if (deviceId == currentDeviceId) {
      throw StateError('Cannot remove the current device session');
    }
    return _repository.removeDevice(deviceId);
  }
}
