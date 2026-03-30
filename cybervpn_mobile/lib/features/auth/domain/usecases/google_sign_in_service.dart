import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';

/// Service for native Google Sign-In using the google_sign_in package.
///
/// Returns the server auth code that the backend exchanges for tokens.
/// The [serverClientId] should be your web-client OAuth 2.0 client ID
/// (not the Android or iOS client ID) so that the backend can exchange
/// the auth code for server-side tokens.
class GoogleSignInService {
  GoogleSignInService({
    String? clientId,
    List<String> scopes = const ['email', 'profile'],
  }) : _serverClientId = clientId,
       _scopes = List<String>.unmodifiable(scopes);

  final GoogleSignIn _googleSignIn = GoogleSignIn.instance;
  final String? _serverClientId;
  final List<String> _scopes;

  static Future<void>? _initialization;

  Future<void> _ensureInitialized() {
    return _initialization ??= _googleSignIn.initialize(
      serverClientId: _serverClientId,
    );
  }

  /// Trigger native Google Sign-In flow.
  ///
  /// Returns a [GoogleSignInResult] containing the server auth code and
  /// user profile data for backend token exchange, or `null` if the user
  /// cancelled the sign-in flow.
  Future<GoogleSignInResult?> signIn() async {
    try {
      await _ensureInitialized();

      if (!_googleSignIn.supportsAuthenticate()) {
        throw UnsupportedError(
          'Interactive Google Sign-In is not supported on this platform.',
        );
      }

      final account = await _googleSignIn.authenticate(scopeHint: _scopes);
      final auth = account.authentication;
      final serverAuthorization = await account.authorizationClient
          .authorizeServer(_scopes);

      return GoogleSignInResult(
        serverAuthCode: serverAuthorization?.serverAuthCode,
        idToken: auth.idToken,
        email: account.email,
        displayName: account.displayName,
        photoUrl: account.photoUrl,
      );
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled ||
          e.code == GoogleSignInExceptionCode.interrupted) {
        return null;
      }
      rethrow;
    } catch (e) {
      rethrow;
    }
  }

  /// Sign out from Google.
  ///
  /// This disconnects the current Google account from the app but does
  /// not revoke access. Call this when the user logs out of CyberVPN.
  Future<void> signOut() async {
    await _ensureInitialized();
    await _googleSignIn.signOut();
  }

  /// Check if user is currently signed in with Google.
  Future<bool> isSignedIn() async {
    await _ensureInitialized();
    final attempt = _googleSignIn.attemptLightweightAuthentication();
    if (attempt == null) {
      return false;
    }
    return (await attempt) != null;
  }
}

/// Result of a Google Sign-In operation.
///
/// Contains both the server auth code (for backend exchange) and
/// client-side profile data that can be used immediately.
class GoogleSignInResult {
  /// Server authorization code for backend token exchange.
  ///
  /// Pass this to the backend's OAuth callback endpoint so it can
  /// exchange it for Google access and refresh tokens server-side.
  final String? serverAuthCode;

  /// Google ID token for client-side identity verification.
  final String? idToken;

  /// Google access token for client-side API calls (if needed).
  final String? accessToken;

  /// The user's email address.
  final String email;

  /// The user's display name, if available.
  final String? displayName;

  /// URL to the user's profile photo, if available.
  final String? photoUrl;

  GoogleSignInResult({
    this.serverAuthCode,
    this.idToken,
    this.accessToken,
    required this.email,
    this.displayName,
    this.photoUrl,
  });
}

// ---------------------------------------------------------------------------
// Riverpod Provider
// ---------------------------------------------------------------------------

/// Provider for [GoogleSignInService].
///
/// Provides native Google Sign-In capabilities. The [serverClientId] should
/// be configured via environment variables or build-time constants.
final googleSignInServiceProvider = Provider<GoogleSignInService>((ref) {
  return GoogleSignInService();
});
