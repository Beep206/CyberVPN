import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for retrieving the list of active device sessions
///
/// Returns all devices/sessions currently associated with the user's account.
class GetDevicesUseCase {
  final ProfileRepository _repository;

  const GetDevicesUseCase(this._repository);

  Future<List<Device>> call() async {
    return _repository.getDevices();
  }
}
