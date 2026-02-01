import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';

/// Remote data source for profile-related API calls.
///
/// Encapsulates all HTTP communication with the backend for user profile,
/// two-factor authentication, OAuth provider linking, device management,
/// and account deletion endpoints.
abstract class ProfileRemoteDataSource {
  // -- Profile --

  /// Fetches the current user's profile from `GET /auth/me`.
  Future<Profile> getProfile();

  // -- Two-Factor Authentication --

  /// Initiates 2FA setup via `POST /2fa/setup`.
  Future<Setup2FAResult> setup2FA();

  /// Verifies a TOTP code during setup via `POST /2fa/verify`.
  Future<bool> verify2FA(String code);

  /// Validates a TOTP code for authentication via `POST /2fa/validate`.
  Future<bool> validate2FA(String code);

  /// Disables 2FA on the account via `POST /2fa/disable`.
  Future<void> disable2FA(String code);

  // -- OAuth Provider Linking --

  /// Initiates OAuth linking for [provider] via
  /// `GET /oauth/{provider}/authorize` and returns the authorization URL.
  /// The caller must launch this URL in a browser and handle the callback.
  Future<String> getOAuthAuthorizationUrl(OAuthProvider provider);

  /// Completes the OAuth linking flow by sending the authorization code
  /// to `POST /oauth/{provider}/callback`.
  Future<void> completeOAuthLink(OAuthProvider provider, String code);

  /// Removes an OAuth provider via `DELETE /oauth/{provider}`.
  Future<void> unlinkOAuth(OAuthProvider provider);

  // -- Device / Session Management --

  /// Fetches active device sessions via `GET /auth/me/devices`.
  Future<List<Device>> getDevices();

  /// Registers the current device via `POST /auth/me/devices`.
  Future<Device> registerDevice({
    required String deviceName,
    required String platform,
    required String deviceId,
  });

  /// Removes a device session via `DELETE /auth/me/devices/{id}`.
  Future<void> removeDevice(String id);

  // -- Account Deletion --

  /// Permanently deletes the user's account via `DELETE /auth/me`.
  Future<void> deleteAccount(String password, {String? totpCode});
}

class ProfileRemoteDataSourceImpl implements ProfileRemoteDataSource {
  final ApiClient _apiClient;

  ProfileRemoteDataSourceImpl(this._apiClient);

  // -- Profile --

  @override
  Future<Profile> getProfile() async {
    final response = await _apiClient.get(ApiConstants.me);
    final data = response.data as Map<String, dynamic>;
    return _mapToProfile(data);
  }

  // -- Two-Factor Authentication --

  @override
  Future<Setup2FAResult> setup2FA() async {
    final response = await _apiClient.post(ApiConstants.setup2fa);
    final data = response.data as Map<String, dynamic>;
    return Setup2FAResult(
      secret: data['secret'] as String,
      qrCodeUri: data['qr_code_uri'] as String,
    );
  }

  @override
  Future<bool> verify2FA(String code) async {
    final response = await _apiClient.post(
      ApiConstants.verify2fa,
      data: {'code': code},
    );
    final data = response.data as Map<String, dynamic>;
    return data['verified'] as bool? ?? false;
  }

  @override
  Future<bool> validate2FA(String code) async {
    final response = await _apiClient.post(
      ApiConstants.validate2fa,
      data: {'code': code},
    );
    final data = response.data as Map<String, dynamic>;
    return data['valid'] as bool? ?? false;
  }

  @override
  Future<void> disable2FA(String code) async {
    await _apiClient.post(
      ApiConstants.disable2fa,
      data: {'code': code},
    );
  }

  // -- OAuth Provider Linking --

  @override
  Future<String> getOAuthAuthorizationUrl(OAuthProvider provider) async {
    final providerName = provider.name;
    final authResponse = await _apiClient.get(
      '${ApiConstants.apiPrefix}/oauth/$providerName/authorize',
    );
    final authData = authResponse.data as Map<String, dynamic>;
    return authData['authorization_url'] as String;
  }

  @override
  Future<void> completeOAuthLink(OAuthProvider provider, String code) async {
    final providerName = provider.name;
    await _apiClient.post(
      '${ApiConstants.apiPrefix}/oauth/$providerName/callback',
      data: {'code': code},
    );
  }

  @override
  Future<void> unlinkOAuth(OAuthProvider provider) async {
    await _apiClient.delete(
      '${ApiConstants.oauthUnlink}${provider.name}',
    );
  }

  // -- Device / Session Management --

  @override
  Future<List<Device>> getDevices() async {
    final response = await _apiClient.get(
      '${ApiConstants.me}/devices',
    );
    final data = response.data as List<dynamic>;
    return data
        .map((json) => _mapToDevice(json as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<Device> registerDevice({
    required String deviceName,
    required String platform,
    required String deviceId,
  }) async {
    final response = await _apiClient.post(
      '${ApiConstants.me}/devices',
      data: {
        'device_name': deviceName,
        'os': platform,
        'device_id': deviceId,
      },
    );
    final data = response.data as Map<String, dynamic>;
    return _mapToDevice(data);
  }

  @override
  Future<void> removeDevice(String id) async {
    await _apiClient.delete('${ApiConstants.me}/devices/$id');
  }

  // -- Account Deletion --

  @override
  Future<void> deleteAccount(String password, {String? totpCode}) async {
    // Use POST for account deletion since the ApiClient's delete method
    // does not support request bodies. The backend accepts this as a
    // confirmation-based deletion endpoint.
    await _apiClient.post(
      '${ApiConstants.deleteAccount}/delete',
      data: {
        'password': password,
        if (totpCode != null) 'totp_code': totpCode,
      },
    );
  }

  // -- Private Helpers --

  Profile _mapToProfile(Map<String, dynamic> json) {
    final linkedProviders = (json['linked_providers'] as List<dynamic>?)
            ?.map((p) => _parseOAuthProvider(p as String))
            .whereType<OAuthProvider>()
            .toList() ??
        [];

    return Profile(
      id: json['id'] as String,
      email: json['email'] as String,
      username: json['username'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      telegramId: json['telegram_id'] as String?,
      isEmailVerified: json['is_email_verified'] as bool? ?? false,
      is2FAEnabled: json['is_2fa_enabled'] as bool? ?? false,
      linkedProviders: linkedProviders,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
      lastLoginAt: json['last_login_at'] != null
          ? DateTime.parse(json['last_login_at'] as String)
          : null,
    );
  }

  OAuthProvider? _parseOAuthProvider(String name) {
    try {
      return OAuthProvider.values.byName(name);
    } catch (_) {
      return null;
    }
  }

  Device _mapToDevice(Map<String, dynamic> json) {
    return Device(
      id: json['id'] as String,
      name: json['name'] as String,
      platform: json['platform'] as String,
      ipAddress: json['ip_address'] as String?,
      lastActiveAt: json['last_active_at'] != null
          ? DateTime.parse(json['last_active_at'] as String)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
      isCurrent: json['is_current'] as bool? ?? false,
    );
  }
}
