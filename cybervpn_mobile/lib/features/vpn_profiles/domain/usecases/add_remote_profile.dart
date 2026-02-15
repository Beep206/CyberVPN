import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

@immutable
class AddRemoteProfileUseCase {
  final ProfileRepository _repository;

  const AddRemoteProfileUseCase(this._repository);

  Future<Result<VpnProfile>> call(String url, {String? name}) =>
      _repository.addRemoteProfile(url, name: name);
}
