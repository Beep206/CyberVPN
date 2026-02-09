import 'package:meta/meta.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/oauth_remote_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';

/// Result of a successful web-based OAuth login.
@immutable
class OAuthLoginResult {
  /// The authenticated user entity.
  final UserEntity user;

  /// Access and refresh tokens for the session.
  final TokenModel tokens;

  /// Whether this is a newly created account.
  final bool isNewUser;

  /// Whether the user has 2FA enabled and must complete verification.
  final bool requires2fa;

  /// Temporary token for 2FA verification (non-null when [requires2fa] is true).
  final String? tfaToken;

  const OAuthLoginResult({
    required this.user,
    required this.tokens,
    required this.isNewUser,
    required this.requires2fa,
    this.tfaToken,
  });
}

/// Use case for web-based OAuth login flows (Discord, Microsoft, X/Twitter).
///
/// These providers lack native Flutter SDKs, so authentication is handled by:
/// 1. Fetching the authorization URL from the CyberVPN backend
/// 2. Storing a CSRF state token in [SecureStorageWrapper]
/// 3. Launching the provider's consent page in an external browser
/// 4. Processing the authorization code when the app receives a deep link callback
///
/// Usage:
/// ```dart
/// final useCase = OAuthLoginUseCase(
///   oauthDataSource: oauthRemoteDs,
///   secureStorage: secureStorage,
/// );
///
/// // Step 1 -- start the flow
/// final startResult = await useCase.startFlow(
///   provider: OAuthProvider.discord,
///   redirectUri: 'cybervpn://oauth/callback',
/// );
///
/// // Step 2 -- process deep link callback (code & state from URL)
/// final loginResult = await useCase.processCallback(
///   code: code,
///   state: state,
///   redirectUri: 'cybervpn://oauth/callback',
/// );
/// ```
@immutable
class OAuthLoginUseCase {
  final OAuthRemoteDataSource _oauthDataSource;
  final SecureStorageWrapper _secureStorage;

  /// Secure storage key for the CSRF state token.
  static const _stateKey = 'oauth_state';

  /// Secure storage key for the provider name.
  static const _providerKey = 'oauth_provider';

  static const _logCategory = 'auth.oauth';

  const OAuthLoginUseCase({
    required OAuthRemoteDataSource oauthDataSource,
    required SecureStorageWrapper secureStorage,
  })  : _oauthDataSource = oauthDataSource,
        _secureStorage = secureStorage;

  /// Supported providers for this web-based OAuth flow.
  static const Set<OAuthProvider> supportedProviders = {
    OAuthProvider.discord,
    OAuthProvider.microsoft,
    OAuthProvider.twitter,
  };

  // ---------------------------------------------------------------------------
  // Step 1 -- Start OAuth flow
  // ---------------------------------------------------------------------------

  /// Initiates the OAuth flow by launching the provider's authorization page.
  ///
  /// [provider] must be one of [supportedProviders] (discord, microsoft, twitter).
  /// [redirectUri] is the deep link URI the provider redirects back to.
  ///
  /// Returns [Success] with `void` when the browser is launched successfully.
  /// Returns [Failure] with [AuthFailure] if the provider is unsupported,
  /// the backend call fails, or the URL cannot be launched.
  Future<Result<void>> startFlow({
    required OAuthProvider provider,
    required String redirectUri,
  }) async {
    // Validate provider
    if (!supportedProviders.contains(provider)) {
      AppLogger.warning(
        'Unsupported OAuth provider for web flow: ${provider.name}',
        category: _logCategory,
      );
      return Failure(AuthFailure(
        message: 'Provider ${provider.name} is not supported for web-based '
            'OAuth login. Supported: ${supportedProviders.map((p) => p.name).join(", ")}',
      ));
    }

    try {
      AppLogger.info(
        'Starting OAuth flow for ${provider.name}',
        category: _logCategory,
      );

      // Fetch authorization URL from the backend
      final response = await _oauthDataSource.getAuthorizeUrl(
        provider: provider.name,
        redirectUri: redirectUri,
      );

      // Persist state and provider in secure storage for callback validation
      await _secureStorage.write(key: _stateKey, value: response.state);
      await _secureStorage.write(key: _providerKey, value: provider.name);

      // Launch authorization URL in external browser
      final uri = Uri.parse(response.authorizeUrl);
      if (!await canLaunchUrl(uri)) {
        AppLogger.error(
          'Cannot launch OAuth URL for ${provider.name}',
          category: _logCategory,
        );
        await _cleanup();
        return const Failure(AuthFailure(
          message: 'Unable to open the login page. '
              'Please ensure you have a web browser installed.',
        ));
      }

      final launched = await launchUrl(
        uri,
        mode: LaunchMode.externalApplication,
      );
      if (!launched) {
        AppLogger.error(
          'launchUrl returned false for ${provider.name}',
          category: _logCategory,
        );
        await _cleanup();
        return const Failure(AuthFailure(
          message: 'Failed to open the login page in your browser.',
        ));
      }

      AppLogger.info(
        'OAuth browser launched for ${provider.name}',
        category: _logCategory,
      );
      return const Success(null);
    } on Exception catch (e, st) {
      AppLogger.error(
        'Failed to start OAuth flow for ${provider.name}',
        error: e,
        stackTrace: st,
        category: _logCategory,
      );
      await _cleanup();
      return Failure(AuthFailure(
        message: 'Could not start ${provider.name} login: $e',
      ));
    }
  }

  // ---------------------------------------------------------------------------
  // Step 2 -- Process deep link callback
  // ---------------------------------------------------------------------------

  /// Processes the OAuth callback after the user returns from the provider.
  ///
  /// [code] is the authorization code from the provider's redirect.
  /// [state] is the state parameter from the callback URL (CSRF validation).
  /// [redirectUri] must match the value passed to [startFlow].
  ///
  /// Returns [Success] with [OAuthLoginResult] on successful authentication.
  /// Returns [Failure] with [AuthFailure] on state mismatch, missing provider,
  /// or backend errors.
  Future<Result<OAuthLoginResult>> processCallback({
    required String code,
    required String state,
    required String redirectUri,
  }) async {
    try {
      // Validate CSRF state token
      final storedState = await _secureStorage.read(key: _stateKey);
      final storedProvider = await _secureStorage.read(key: _providerKey);

      if (storedState == null || storedState != state) {
        AppLogger.error(
          'OAuth state mismatch (possible CSRF)',
          category: _logCategory,
        );
        await _cleanup();
        return const Failure(AuthFailure(
          message: 'Login session expired or was tampered with. '
              'Please try again.',
        ));
      }

      if (storedProvider == null) {
        AppLogger.error(
          'OAuth provider not found in secure storage',
          category: _logCategory,
        );
        await _cleanup();
        return const Failure(AuthFailure(
          message: 'Login session is invalid. Please try again.',
        ));
      }

      // Clear stored state before the network call (single-use)
      await _cleanup();

      AppLogger.info(
        'Processing OAuth callback for $storedProvider',
        category: _logCategory,
      );

      // Exchange authorization code for tokens via backend
      final response = await _oauthDataSource.loginCallback(
        provider: storedProvider,
        code: code,
        state: state,
        redirectUri: redirectUri,
      );

      final result = OAuthLoginResult(
        user: response.user.toEntity(),
        tokens: response.toTokenModel(),
        isNewUser: response.isNewUser,
        requires2fa: response.requires2fa,
        tfaToken: response.tfaToken,
      );

      AppLogger.info(
        'OAuth login successful for $storedProvider '
        '(new_user: ${result.isNewUser}, 2fa: ${result.requires2fa})',
        category: _logCategory,
      );

      return Success(result);
    } on Exception catch (e, st) {
      AppLogger.error(
        'OAuth callback processing failed',
        error: e,
        stackTrace: st,
        category: _logCategory,
      );
      await _cleanup();
      return Failure(AuthFailure(
        message: 'Login failed. Please try again.',
      ));
    }
  }

  // ---------------------------------------------------------------------------
  // Cleanup
  // ---------------------------------------------------------------------------

  /// Clears any stored OAuth state.
  ///
  /// Call this on error, user cancellation, or timeout to prevent stale state
  /// from interfering with subsequent login attempts.
  Future<Result<void>> cancel() async {
    AppLogger.info('OAuth flow cancelled, cleaning up', category: _logCategory);
    await _cleanup();
    return const Success(null);
  }

  /// Internal cleanup -- removes CSRF state and provider from secure storage.
  Future<void> _cleanup() async {
    await _secureStorage.delete(key: _stateKey);
    await _secureStorage.delete(key: _providerKey);
  }
}
