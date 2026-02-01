import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for unlinking an OAuth provider from the user's account
///
/// Removes the specified provider's association with the user's account.
class UnlinkSocialAccountUseCase {
  final ProfileRepository _repository;

  const UnlinkSocialAccountUseCase(this._repository);

  /// Unlinks the specified [provider] from the current user's account.
  ///
  /// Validates that the provider is currently linked before attempting removal.
  /// Throws [StateError] if the provider is not linked.
  Future<void> call({
    required OAuthProvider provider,
    required List<OAuthProvider> currentlyLinked,
  }) async {
    if (!currentlyLinked.contains(provider)) {
      throw StateError('${provider.name} is not linked to this account');
    }
    return _repository.unlinkOAuth(provider);
  }
}
