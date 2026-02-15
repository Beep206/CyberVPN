import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

@immutable
class MigrateLegacyProfilesUseCase {
  final ProfileRepository _repository;

  const MigrateLegacyProfilesUseCase(this._repository);

  Future<Result<void>> call() => _repository.migrateFromLegacy();
}
