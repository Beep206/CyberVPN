import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

@immutable
class UpdateSubscriptionsUseCase {
  final ProfileRepository _repository;

  const UpdateSubscriptionsUseCase(this._repository);

  /// Refreshes all remote profiles whose update interval has elapsed.
  ///
  /// Returns the number of profiles that were updated.
  Future<Result<int>> call() => _repository.updateAllDueSubscriptions();
}
