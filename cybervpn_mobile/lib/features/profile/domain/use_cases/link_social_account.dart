import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for initiating the OAuth linking flow for a social account
///
/// Returns the authorization URL that should be opened in a browser.
/// The actual linking completion happens via [CompleteSocialAccountLinkUseCase].
class LinkSocialAccountUseCase {
  final ProfileRepository _repository;

  const LinkSocialAccountUseCase(this._repository);

  /// Gets the OAuth authorization URL for the specified [provider].
  ///
  /// Checks that the provider is not already linked before proceeding.
  /// Throws [StateError] if the provider is already linked.
  /// Returns the authorization URL to open in a browser.
  Future<Result<String>> call({
    required OAuthProvider provider,
    required List<OAuthProvider> currentlyLinked,
  }) async {
    if (currentlyLinked.contains(provider)) {
      throw StateError('${provider.name} is already linked to this account');
    }
    return _repository.getOAuthAuthorizationUrl(provider);
  }
}

/// Use case for completing the OAuth linking flow with the callback code
class CompleteSocialAccountLinkUseCase {
  final ProfileRepository _repository;

  const CompleteSocialAccountLinkUseCase(this._repository);

  /// Completes the OAuth linking flow by sending the [code] to the backend.
  Future<Result<void>> call({
    required OAuthProvider provider,
    required String code,
  }) async {
    return _repository.completeOAuthLink(provider, code);
  }
}
