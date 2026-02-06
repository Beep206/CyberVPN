import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for retrieving the current user's profile
///
/// Simple passthrough to the repository for consistency
/// with the use case pattern used across the domain layer.
class GetProfileUseCase {
  final ProfileRepository _repository;

  const GetProfileUseCase(this._repository);

  Future<Result<Profile>> call() async {
    return _repository.getProfile();
  }
}
