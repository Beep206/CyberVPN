import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show apiClientProvider, secureStorageProvider;

/// Service that manages device-bound tokens for biometric re-authentication.
///
/// Instead of storing plaintext credentials, this service obtains a
/// cryptographic device token from the backend that is bound to the device.
class DeviceBoundTokenService {
  final ApiClient _apiClient;
  final SecureStorageWrapper _storage;

  DeviceBoundTokenService({
    required ApiClient apiClient,
    required SecureStorageWrapper storage,
  })  : _apiClient = apiClient,
        _storage = storage;

  /// Enrolls the current device for biometric re-authentication.
  ///
  /// Calls POST /mobile/auth/biometric/enroll with the device ID.
  /// On success, stores the returned device token in secure storage.
  ///
  /// Requires a valid JWT access token (user must be authenticated).
  /// Returns the device token on success, `null` on failure.
  Future<String?> enroll() async {
    try {
      final deviceId = await _storage.getOrCreateDeviceId();

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiConstants.biometricEnroll,
        data: {'device_id': deviceId},
      );

      final data = response.data;
      if (data == null) {
        AppLogger.warning(
          'Biometric enroll returned null response',
          category: 'auth.biometric',
        );
        return null;
      }

      final deviceToken = data['device_token'] as String?;
      if (deviceToken == null || deviceToken.isEmpty) {
        AppLogger.warning(
          'Biometric enroll returned empty device token',
          category: 'auth.biometric',
        );
        return null;
      }

      await _storage.setDeviceToken(deviceToken);
      AppLogger.info(
        'Device enrolled for biometric auth',
        category: 'auth.biometric',
      );
      return deviceToken;
    } catch (e, st) {
      AppLogger.error(
        'Failed to enroll device for biometric auth',
        error: e,
        stackTrace: st,
        category: 'auth.biometric',
      );
      return null;
    }
  }

  /// Authenticates using the stored device-bound token.
  ///
  /// Calls POST /mobile/auth/biometric/login with the device token + device ID.
  /// On success, stores the returned JWT tokens and returns `true`.
  Future<bool> login() async {
    try {
      final deviceToken = await _storage.getDeviceToken();
      if (deviceToken == null || deviceToken.isEmpty) {
        AppLogger.warning(
          'No device token found for biometric login',
          category: 'auth.biometric',
        );
        return false;
      }

      final deviceId = await _storage.getOrCreateDeviceId();

      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiConstants.biometricLogin,
        data: {
          'device_token': deviceToken,
          'device_id': deviceId,
        },
      );

      final data = response.data;
      if (data == null) {
        AppLogger.warning(
          'Biometric login returned null response',
          category: 'auth.biometric',
        );
        return false;
      }

      final accessToken = data['access_token'] as String?;
      final refreshToken = data['refresh_token'] as String?;

      if (accessToken == null || refreshToken == null) {
        AppLogger.warning(
          'Biometric login returned incomplete tokens',
          category: 'auth.biometric',
        );
        return false;
      }

      await _storage.setTokens(
        accessToken: accessToken,
        refreshToken: refreshToken,
      );

      AppLogger.info(
        'Biometric login successful via device token',
        category: 'auth.biometric',
      );
      return true;
    } catch (e, st) {
      AppLogger.error(
        'Device-bound token login failed',
        error: e,
        stackTrace: st,
        category: 'auth.biometric',
      );
      return false;
    }
  }

  /// Whether a device token is enrolled for biometric auth.
  Future<bool> isEnrolled() async {
    final token = await _storage.getDeviceToken();
    return token != null && token.isNotEmpty;
  }

  /// Revokes the current device enrollment.
  Future<void> revoke() async {
    await _storage.clearDeviceToken();
    AppLogger.info(
      'Device biometric enrollment revoked',
      category: 'auth.biometric',
    );
  }
}

// ---------------------------------------------------------------------------
// Riverpod Provider
// ---------------------------------------------------------------------------

final deviceBoundTokenServiceProvider =
    Provider<DeviceBoundTokenService>((ref) {
  return DeviceBoundTokenService(
    apiClient: ref.watch(apiClientProvider),
    storage: ref.watch(secureStorageProvider),
  );
});
