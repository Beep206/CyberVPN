import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';

/// Repository interface for user profile management
///
/// Follows the repository pattern from Clean Architecture.
/// Provides methods for profile retrieval, two-factor authentication,
/// OAuth provider linking, device session management, and account deletion.
abstract class ProfileRepository {
  /// Get the current user's profile
  Future<Profile> getProfile();

  // -- Two-Factor Authentication --

  /// Initiate 2FA setup, returning the secret and QR code URI
  Future<Setup2FAResult> setup2FA();

  /// Verify a TOTP code during 2FA setup to confirm configuration
  Future<bool> verify2FA(String code);

  /// Validate a TOTP code for authentication purposes
  Future<bool> validate2FA(String code);

  /// Disable 2FA on the account (requires valid TOTP code)
  Future<void> disable2FA(String code);

  // -- OAuth Provider Linking --

  /// Get the OAuth authorization URL for the specified provider.
  /// The caller must launch this URL in a browser to initiate the OAuth flow.
  Future<String> getOAuthAuthorizationUrl(OAuthProvider provider);

  /// Complete the OAuth linking flow with the authorization code from the callback.
  Future<void> completeOAuthLink(OAuthProvider provider, String code);

  /// Unlink an OAuth provider from the user's account
  Future<void> unlinkOAuth(OAuthProvider provider);

  // -- Device / Session Management --

  /// Get all active device sessions for the current user
  Future<List<Device>> getDevices();

  /// Register the current device
  Future<Device> registerDevice({
    required String deviceName,
    required String platform,
    required String deviceId,
  });

  /// Remove (revoke) a device session by its ID
  Future<void> removeDevice(String id);

  // -- Account Deletion --

  /// Permanently delete the user's account
  ///
  /// Requires [password] for confirmation.
  /// If 2FA is enabled, [totpCode] must also be provided.
  Future<void> deleteAccount(String password, {String? totpCode});
}
