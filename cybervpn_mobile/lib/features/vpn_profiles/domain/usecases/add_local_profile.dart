import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

@immutable
class AddLocalProfileUseCase {
  final ProfileRepository _repository;

  const AddLocalProfileUseCase(this._repository);

  Future<Result<VpnProfile>> call(
    String name,
    List<ProfileServer> servers,
  ) =>
      _repository.addLocalProfile(name, servers);
}
