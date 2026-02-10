import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show apiClientProvider, localStorageProvider;
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// SharedPreferences key for the pending FCM token.
const _pendingFcmTokenKey = 'pending_fcm_token';

/// Service for managing FCM device token registration with the backend.
///
/// Handles:
/// * Retrieving the FCM device token from Firebase.
/// * Storing the token locally before auth so it survives app restarts.
/// * Collecting device metadata (platform, OS version).
/// * Sending token and device info to the backend API.
/// * Clearing the pending token on successful registration.
/// * Error handling for network failures and FCM issues.
///
/// Usage:
/// ```dart
/// final service = ref.read(fcmTokenServiceProvider);
/// await service.registerToken();
/// ```
class FcmTokenService {
  final ApiClient _apiClient;
  final LocalStorageWrapper _localStorage;

  FcmTokenService({
    required ApiClient apiClient,
    required LocalStorageWrapper localStorage,
  })  : _apiClient = apiClient,
        _localStorage = localStorage;

  /// Stores the FCM token locally so it survives app restarts.
  ///
  /// Call this immediately when a token is received (e.g. from
  /// [FirebaseMessaging.onTokenRefresh]), regardless of auth state.
  /// The token will be registered with the backend on the next
  /// [registerToken] call.
  Future<void> storePendingToken(String token) async {
    await _localStorage.setString(_pendingFcmTokenKey, token);
    AppLogger.debug(
      'Stored pending FCM token locally',
      category: 'fcm_token_service',
      data: {'token_length': token.length},
    );
  }

  /// Retrieves the FCM device token and registers it with the backend.
  ///
  /// Checks for a locally stored pending token first, then falls back to
  /// requesting a fresh token from Firebase. On successful backend
  /// registration, the pending token is cleared.
  ///
  /// Returns `true` if registration was successful, `false` otherwise.
  /// Errors are logged but not thrown to prevent blocking the auth flow.
  Future<bool> registerToken() async {
    try {
      // Prefer locally cached token (may have been stored before auth).
      var token = await _localStorage.getString(_pendingFcmTokenKey);

      // Fall back to requesting a fresh token from Firebase.
      if (token == null || token.isEmpty) {
        token = await FirebaseMessaging.instance.getToken();
      }

      if (token == null || token.isEmpty) {
        AppLogger.warning(
          'FCM token is null or empty - skipping registration',
          category: 'fcm_token_service',
        );
        return false;
      }

      AppLogger.debug(
        'Retrieved FCM token for registration',
        category: 'fcm_token_service',
        data: {'token_length': token.length},
      );

      // Collect device information
      final deviceInfo = await _getDeviceInfo();

      // Send to backend
      await _sendTokenToBackend(
        token: token,
        deviceId: deviceInfo['device_id'] as String,
        platform: deviceInfo['platform'] as String,
      );

      // Clear pending token on success.
      await _localStorage.remove(_pendingFcmTokenKey);

      AppLogger.info(
        'FCM token registered successfully',
        category: 'fcm_token_service',
      );

      return true;
    } catch (e, st) {
      AppLogger.error(
        'Failed to register FCM token',
        error: e,
        stackTrace: st,
        category: 'fcm_token_service',
      );
      return false;
    }
  }

  /// Collects device metadata for FCM token registration.
  ///
  /// Returns a map with `platform` (android/ios) and `device_id`.
  Future<Map<String, String>> _getDeviceInfo() async {
    final deviceInfoPlugin = DeviceInfoPlugin();

    if (Platform.isAndroid) {
      final androidInfo = await deviceInfoPlugin.androidInfo;
      return {
        'platform': 'android',
        'device_id': androidInfo.id,
      };
    } else if (Platform.isIOS) {
      final iosInfo = await deviceInfoPlugin.iosInfo;
      return {
        'platform': 'ios',
        'device_id': iosInfo.identifierForVendor ?? 'unknown',
      };
    }

    // Fallback for unsupported platforms
    return {
      'platform': Platform.operatingSystem,
      'device_id': 'unknown',
    };
  }

  /// Sends the FCM token to the backend API.
  ///
  /// Throws on network errors or server errors.
  Future<void> _sendTokenToBackend({
    required String token,
    required String deviceId,
    required String platform,
  }) async {
    final payload = {
      'token': token,
      'device_id': deviceId,
      'platform': platform,
    };

    AppLogger.debug(
      'Sending FCM token to backend',
      category: 'fcm_token_service',
      data: {
        'token_prefix': token.length >= 8 ? '${token.substring(0, 8)}...' : '(short)',
        'device_id': deviceId,
        'platform': platform,
      },
    );

    await _apiClient.post<void>(
      ApiConstants.registerFcmToken,
      data: payload,
    );
  }
}

/// Provider for [FcmTokenService].
///
/// Lazily resolved via [apiClientProvider] and [localStorageProvider].
/// Override in tests with a mock.
final fcmTokenServiceProvider = Provider<FcmTokenService>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final localStorage = ref.watch(localStorageProvider);
  return FcmTokenService(apiClient: apiClient, localStorage: localStorage);
});
