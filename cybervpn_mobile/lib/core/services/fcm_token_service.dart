import 'dart:io';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Service for managing FCM device token registration with the backend.
///
/// Handles:
/// * Retrieving the FCM device token from Firebase.
/// * Collecting device metadata (platform, OS version).
/// * Sending token and device info to the backend API.
/// * Error handling for network failures and FCM issues.
///
/// Usage:
/// ```dart
/// final service = ref.read(fcmTokenServiceProvider);
/// await service.registerToken();
/// ```
class FcmTokenService {
  final ApiClient _apiClient;

  FcmTokenService({required ApiClient apiClient}) : _apiClient = apiClient;

  /// Retrieves the FCM device token and registers it with the backend.
  ///
  /// Returns `true` if registration was successful, `false` otherwise.
  /// Errors are logged but not thrown to prevent blocking the auth flow.
  Future<bool> registerToken() async {
    try {
      // Get FCM token from Firebase
      final token = await FirebaseMessaging.instance.getToken();

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
        platform: deviceInfo['platform'] as String,
        osVersion: deviceInfo['os_version'] as String,
      );

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
  /// Returns a map with `platform` (android/ios) and `os_version`.
  Future<Map<String, String>> _getDeviceInfo() async {
    final deviceInfoPlugin = DeviceInfoPlugin();

    if (Platform.isAndroid) {
      final androidInfo = await deviceInfoPlugin.androidInfo;
      return {
        'platform': 'android',
        'os_version': 'Android ${androidInfo.version.release} (SDK ${androidInfo.version.sdkInt})',
      };
    } else if (Platform.isIOS) {
      final iosInfo = await deviceInfoPlugin.iosInfo;
      return {
        'platform': 'ios',
        'os_version': 'iOS ${iosInfo.systemVersion}',
      };
    }

    // Fallback for unsupported platforms
    return {
      'platform': Platform.operatingSystem,
      'os_version': Platform.operatingSystemVersion,
    };
  }

  /// Sends the FCM token to the backend API.
  ///
  /// Throws on network errors or server errors.
  Future<void> _sendTokenToBackend({
    required String token,
    required String platform,
    required String osVersion,
  }) async {
    final payload = {
      'fcm_token': token,
      'platform': platform,
      'os_version': osVersion,
    };

    AppLogger.debug(
      'Sending FCM token to backend',
      category: 'fcm_token_service',
      data: payload,
    );

    // POST to backend endpoint (will return 404 until backend implements it)
    await _apiClient.post<void>(
      ApiConstants.registerFcmToken,
      data: payload,
    );
  }
}

/// Provider for [FcmTokenService].
///
/// Requires an [ApiClient] instance. Override in tests with a mock.
final fcmTokenServiceProvider = Provider<FcmTokenService>((ref) {
  throw UnimplementedError(
    'fcmTokenServiceProvider must be overridden with a concrete '
    'FcmTokenService instance (e.g. via ProviderScope overrides).',
  );
});
