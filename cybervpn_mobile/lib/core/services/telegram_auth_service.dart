import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/logout_provider.dart'
    show apiClientProvider;

/// Result of Telegram authentication.
class TelegramAuthResult {
  final UserModel user;
  final TokenModel tokens;
  final bool isNewUser;

  const TelegramAuthResult({
    required this.user,
    required this.tokens,
    required this.isNewUser,
  });
}

/// Exception thrown when Telegram authentication fails.
class TelegramAuthException implements Exception {
  final String code;
  final String message;

  const TelegramAuthException({
    required this.code,
    required this.message,
  });

  @override
  String toString() => 'TelegramAuthException($code): $message';
}

/// Service for handling Telegram OAuth authentication.
///
/// Provides methods to:
/// - Launch Telegram Login Widget
/// - Authenticate with the backend using auth_data from callback
/// - Store tokens and user data on success
class TelegramAuthService {
  final Ref _ref;

  TelegramAuthService(this._ref);

  ApiClient get _apiClient => _ref.read(apiClientProvider);
  SecureStorageWrapper get _storage => _ref.read(secureStorageProvider);

  /// Launches the Telegram Login Widget in an external browser.
  ///
  /// The widget redirects back to the app via deep link after authentication.
  /// Deep link format: `cybervpn://telegram/callback?auth_data={base64}`
  Future<bool> launchTelegramLogin() async {
    final botUsername = EnvironmentConfig.telegramBotUsername;
    if (botUsername.isEmpty) {
      AppLogger.error(
        'Telegram bot username not configured',
        category: 'auth.telegram',
      );
      return false;
    }

    // Telegram Login Widget URL with callback to our deep link
    // The callback URL is URL-encoded
    const callbackUrl = 'cybervpn://telegram/callback';
    final encodedCallback = Uri.encodeComponent(callbackUrl);

    // Telegram Login Widget uses t.me OAuth link format
    // Reference: https://core.telegram.org/widgets/login
    final telegramUrl = Uri.parse(
      'https://oauth.telegram.org/auth?bot_id=$botUsername'
      '&origin=$encodedCallback'
      '&request_access=write',
    );

    AppLogger.info(
      'Launching Telegram login: $telegramUrl',
      category: 'auth.telegram',
    );

    try {
      final launched = await launchUrl(
        telegramUrl,
        mode: LaunchMode.externalApplication,
      );
      if (!launched) {
        AppLogger.warning(
          'Failed to launch Telegram login URL',
          category: 'auth.telegram',
        );
      }
      return launched;
    } catch (e, st) {
      AppLogger.error(
        'Error launching Telegram login',
        error: e,
        stackTrace: st,
        category: 'auth.telegram',
      );
      return false;
    }
  }

  /// Authenticates with the backend using Telegram auth_data.
  ///
  /// Called when the app receives a deep link callback from Telegram.
  /// Sends auth_data to POST /api/v1/mobile/auth/telegram/callback.
  ///
  /// Returns [TelegramAuthResult] on success.
  /// Throws [TelegramAuthException] on failure.
  Future<TelegramAuthResult> authenticateWithAuthData({
    required String authData,
    required DeviceInfo device,
  }) async {
    AppLogger.info(
      'Authenticating with Telegram auth_data',
      category: 'auth.telegram',
    );

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        '/mobile/auth/telegram/callback',
        data: {
          'auth_data': authData,
          'device': device.toJson(),
        },
      );

      final responseData = response.data!;

      // Parse response
      final tokensData = responseData['tokens'] as Map<String, dynamic>;
      final userData = responseData['user'] as Map<String, dynamic>;
      final isNewUser = responseData['is_new_user'] as bool? ?? false;

      final tokens = TokenModel.fromJson(tokensData);
      final user = UserModel.fromJson(userData);

      // Store tokens atomically
      await _storage.setTokens(
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
      );

      AppLogger.info(
        'Telegram authentication successful (new_user: $isNewUser)',
        category: 'auth.telegram',
      );

      return TelegramAuthResult(
        user: user,
        tokens: tokens,
        isNewUser: isNewUser,
      );
    } on TelegramAuthException {
      rethrow;
    } catch (e, st) {
      AppLogger.error(
        'Telegram authentication failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram',
      );

      // Parse error response if available
      if (e is Exception) {
        final errorStr = e.toString();
        if (errorStr.contains('INVALID_TELEGRAM_AUTH')) {
          throw const TelegramAuthException(
            code: 'INVALID_TELEGRAM_AUTH',
            message: 'Invalid Telegram authentication data',
          );
        }
        if (errorStr.contains('TELEGRAM_AUTH_EXPIRED')) {
          throw const TelegramAuthException(
            code: 'TELEGRAM_AUTH_EXPIRED',
            message: 'Telegram authentication expired. Please try again.',
          );
        }
      }

      throw TelegramAuthException(
        code: 'TELEGRAM_AUTH_FAILED',
        message: 'Telegram authentication failed: $e',
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provider for [TelegramAuthService].
final telegramAuthServiceProvider = Provider<TelegramAuthService>((ref) {
  return TelegramAuthService(ref);
});
