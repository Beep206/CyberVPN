import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

@immutable
class DeleteProfileUseCase {
  final ProfileRepository _repository;

  const DeleteProfileUseCase(this._repository);

  Future<Result<void>> call(String profileId) =>
      _repository.delete(profileId);
}
