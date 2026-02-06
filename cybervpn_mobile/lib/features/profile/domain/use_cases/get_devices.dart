import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for retrieving the list of active device sessions
///
/// Returns all devices/sessions currently associated with the user's account.
@immutable
class GetDevicesUseCase {
  final ProfileRepository _repository;

  const GetDevicesUseCase(this._repository);

  Future<Result<List<Device>>> call() async {
    return _repository.getDevices();
  }
}
