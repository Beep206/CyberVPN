import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

/// Service for native Sign In with Apple.
///
/// Returns the authorization code and identity token that the backend
/// exchanges for tokens. Apple only provides the user's email and name
/// on the **first** sign-in; subsequent sign-ins return only the
/// authorization code and identity token.
class AppleSignInService {
  /// Check if Sign In with Apple is available on this device.
  ///
  /// Returns `false` on Android devices (unless a web-based fallback is
  /// configured) and on iOS versions below 13.0.
  Future<bool> isAvailable() async {
    return await SignInWithApple.isAvailable();
  }

  /// Trigger native Sign In with Apple flow.
  ///
  /// Returns an [AppleSignInResult] containing the authorization code,
  /// identity token, and (on first sign-in) the user's name and email.
  /// Returns `null` if the user cancelled the sign-in flow.
  Future<AppleSignInResult?> signIn() async {
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
      );

      return AppleSignInResult(
        authorizationCode: credential.authorizationCode,
        identityToken: credential.identityToken,
        email: credential.email,
        givenName: credential.givenName,
        familyName: credential.familyName,
        userIdentifier: credential.userIdentifier,
      );
    } on SignInWithAppleAuthorizationException catch (e) {
      if (e.code == AuthorizationErrorCode.canceled) {
        return null; // User cancelled
      }
      rethrow;
    }
  }
}

/// Result of an Apple Sign-In operation.
///
/// Contains the authorization code and identity token for backend
/// exchange, plus optional profile data (only provided on first sign-in).
class AppleSignInResult {
  /// Authorization code for backend token exchange.
  ///
  /// Pass this to the backend's OAuth callback endpoint so it can
  /// exchange it for Apple tokens server-side.
  final String authorizationCode;

  /// Identity token (JWT) for server-side identity verification.
  ///
  /// The backend should validate this token with Apple's public keys
  /// to confirm the user's identity.
  final String? identityToken;

  /// The user's email address (only provided on first sign-in).
  ///
  /// Apple may provide a private relay email if the user chose to
  /// hide their email. The backend should store this on first sign-in.
  final String? email;

  /// The user's given (first) name (only provided on first sign-in).
  final String? givenName;

  /// The user's family (last) name (only provided on first sign-in).
  final String? familyName;

  /// Apple's stable user identifier for this app.
  ///
  /// This identifier is consistent across sign-ins and can be used
  /// to look up the user in the backend database.
  final String? userIdentifier;

  AppleSignInResult({
    required this.authorizationCode,
    this.identityToken,
    this.email,
    this.givenName,
    this.familyName,
    this.userIdentifier,
  });

  /// Full display name from given + family name.
  ///
  /// Returns `null` if neither name component is available
  /// (which happens on subsequent sign-ins after the first).
  String? get displayName {
    final parts = [givenName, familyName].whereType<String>().toList();
    return parts.isEmpty ? null : parts.join(' ');
  }
}

// ---------------------------------------------------------------------------
// Riverpod Provider
// ---------------------------------------------------------------------------

/// Provider for [AppleSignInService].
///
/// Provides native Sign In with Apple capabilities. Use
/// [isAppleSignInAvailableProvider] to check device support before
/// showing the Apple sign-in button.
final appleSignInServiceProvider = Provider<AppleSignInService>((ref) {
  return AppleSignInService();
});

/// Provider that checks if Sign In with Apple is available on this device.
///
/// Returns `true` on iOS 13+ devices and `false` on Android (unless a
/// web-based fallback is configured). Use this to conditionally show
/// the Apple sign-in button in the UI.
final isAppleSignInAvailableProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(appleSignInServiceProvider);
  return service.isAvailable();
});
