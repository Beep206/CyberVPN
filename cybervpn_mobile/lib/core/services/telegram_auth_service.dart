import 'dart:io' show Platform;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
import 'package:cybervpn_mobile/core/network/auth_interceptor.dart';
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
  final String? tfaToken;
  final String? method;

  const TelegramAuthException({
    required this.code,
    required this.message,
    this.tfaToken,
    this.method,
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

  /// Checks if the Telegram app is installed on the device.
  ///
  /// Uses the `tg://` URL scheme to detect Telegram.
  Future<bool> isTelegramInstalled() async {
    final telegramUri = Uri.parse('tg://resolve');
    try {
      return await canLaunchUrl(telegramUri);
    } catch (e) {
      AppLogger.warning(
        'Error checking Telegram installation: $e',
        category: 'auth.telegram',
      );
      return false;
    }
  }

  /// Opens the app store to install Telegram.
  ///
  /// Returns `true` if the store was opened successfully.
  Future<bool> openTelegramAppStore() async {
    final Uri storeUrl;
    if (Platform.isIOS) {
      storeUrl = Uri.parse(
        'https://apps.apple.com/app/telegram-messenger/id686449807',
      );
    } else {
      storeUrl = Uri.parse(
        'https://play.google.com/store/apps/details?id=org.telegram.messenger',
      );
    }

    AppLogger.info(
      'Opening Telegram app store: $storeUrl',
      category: 'auth.telegram',
    );

    try {
      return await launchUrl(storeUrl, mode: LaunchMode.externalApplication);
    } catch (e, st) {
      AppLogger.error(
        'Error opening app store',
        error: e,
        stackTrace: st,
        category: 'auth.telegram',
      );
      return false;
    }
  }

  /// Launches Telegram login via web browser (t.me bot link).
  ///
  /// This is a fallback when the Telegram app is not installed.
  /// The user authenticates via t.me web interface.
  Future<bool> launchTelegramWebLogin() async {
    final botUsername = EnvironmentConfig.telegramBotUsername;
    if (botUsername.isEmpty) {
      AppLogger.error(
        'Telegram bot username not configured',
        category: 'auth.telegram',
      );
      return false;
    }

    // Web fallback: t.me bot link
    final webUrl = Uri.parse('https://t.me/$botUsername?start=login');

    AppLogger.info(
      'Launching Telegram web login: $webUrl',
      category: 'auth.telegram',
    );

    try {
      return await launchUrl(webUrl, mode: LaunchMode.externalApplication);
    } catch (e, st) {
      AppLogger.error(
        'Error launching Telegram web login',
        error: e,
        stackTrace: st,
        category: 'auth.telegram',
      );
      return false;
    }
  }

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
        data: {'auth_data': authData, 'device': device.toJson()},
      );
      return _consumeAuthResponse(
        response.data!,
        successLogMessage: 'Telegram authentication successful',
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

  /// Authenticates with the backend using a Telegram native SDK `id_token`.
  Future<TelegramAuthResult> authenticateWithIdToken({
    required String idToken,
    required DeviceInfo device,
  }) async {
    AppLogger.info(
      'Authenticating with Telegram native id_token',
      category: 'auth.telegram.native',
    );

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiConstants.telegramOidcAuth,
        data: {'id_token': idToken, 'device': device.toJson()},
      );

      return _consumeAuthResponse(
        response.data!,
        successLogMessage: 'Telegram native authentication successful',
      );
    } on TelegramAuthException {
      rethrow;
    } catch (e, st) {
      AppLogger.error(
        'Telegram native authentication failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram.native',
      );

      if (e is Exception) {
        final errorStr = e.toString();
        if (errorStr.contains('INVALID_TELEGRAM_ID_TOKEN')) {
          throw const TelegramAuthException(
            code: 'INVALID_TELEGRAM_ID_TOKEN',
            message: 'Invalid Telegram identity token.',
          );
        }
      }

      throw TelegramAuthException(
        code: 'TELEGRAM_NATIVE_AUTH_FAILED',
        message: 'Telegram authentication failed: $e',
      );
    }
  }

  /// Completes a Telegram login paused behind a pending TOTP challenge.
  Future<TelegramAuthResult> completeTwoFactor({
    required String tfaToken,
    required String code,
  }) async {
    AppLogger.info(
      'Completing Telegram native login 2FA challenge',
      category: 'auth.telegram.native',
    );

    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiConstants.mobile2faComplete,
        data: {'code': code},
        options: Options(
          headers: {'Authorization': 'Bearer $tfaToken'},
          extra: {
            AuthInterceptor.skipAuthHeaderKey: true,
            AuthInterceptor.skipAuthRefreshHandlingKey: true,
          },
        ),
      );

      return _consumeAuthResponse(
        response.data!,
        successLogMessage:
            'Telegram native authentication successful after 2FA',
      );
    } on TelegramAuthException {
      rethrow;
    } catch (e, st) {
      AppLogger.error(
        'Telegram native 2FA completion failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram.native',
      );

      if (e is Exception) {
        final errorStr = e.toString();
        if (errorStr.contains('INVALID_2FA_CODE')) {
          throw const TelegramAuthException(
            code: 'INVALID_2FA_CODE',
            message: 'Invalid verification code.',
          );
        }
        if (errorStr.contains('INVALID_2FA_TOKEN')) {
          throw const TelegramAuthException(
            code: 'INVALID_2FA_TOKEN',
            message: 'Two-factor login session expired. Please try again.',
          );
        }
      }

      throw TelegramAuthException(
        code: 'TELEGRAM_NATIVE_2FA_FAILED',
        message: 'Telegram 2FA verification failed: $e',
      );
    }
  }

  /// Links a Telegram native SDK `id_token` to the currently authenticated user.
  Future<void> linkCurrentUserWithIdToken({required String idToken}) async {
    AppLogger.info(
      'Linking Telegram native identity to current mobile user',
      category: 'auth.telegram.native',
    );

    try {
      await _apiClient.post<Map<String, dynamic>>(
        ApiConstants.telegramOidcLink,
        data: {'id_token': idToken},
      );
    } catch (e, st) {
      AppLogger.error(
        'Telegram native account linking failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram.native',
      );

      if (e is Exception) {
        final errorStr = e.toString();
        if (errorStr.contains('TELEGRAM_IDENTITY_ALREADY_LINKED')) {
          throw const TelegramAuthException(
            code: 'TELEGRAM_IDENTITY_ALREADY_LINKED',
            message: 'Telegram account is already linked to another user.',
          );
        }
        if (errorStr.contains('INVALID_TELEGRAM_ID_TOKEN')) {
          throw const TelegramAuthException(
            code: 'INVALID_TELEGRAM_ID_TOKEN',
            message: 'Invalid Telegram identity token.',
          );
        }
      }

      throw TelegramAuthException(
        code: 'TELEGRAM_LINK_FAILED',
        message: 'Telegram account linking failed: $e',
      );
    }
  }

  /// Unlinks Telegram from the currently authenticated user.
  Future<void> unlinkCurrentUserTelegram() async {
    AppLogger.info(
      'Unlinking Telegram identity from current mobile user',
      category: 'auth.telegram.native',
    );

    try {
      await _apiClient.delete<Map<String, dynamic>>(ApiConstants.telegramOidcLink);
    } catch (e, st) {
      AppLogger.error(
        'Telegram unlink failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram.native',
      );
      throw TelegramAuthException(
        code: 'TELEGRAM_UNLINK_FAILED',
        message: 'Telegram account unlink failed: $e',
      );
    }
  }

  Future<TelegramAuthResult> _consumeAuthResponse(
    Map<String, dynamic> responseData, {
    required String successLogMessage,
  }) async {
    if (responseData['requires_2fa'] == true) {
      throw TelegramAuthException(
        code: 'TWO_FACTOR_REQUIRED',
        message: 'Two-factor authentication is required.',
        tfaToken: responseData['tfa_token'] as String?,
        method: responseData['method'] as String?,
      );
    }

    final tokensData =
        responseData['tokens'] as Map<String, dynamic>? ?? const {};
    final userData = responseData['user'] as Map<String, dynamic>? ?? const {};
    final isNewUser = responseData['is_new_user'] as bool? ?? false;

    final tokens = TokenModel.fromJson(_normalizeTokensJson(tokensData));
    final user = UserModel.fromJson(_normalizeUserJson(userData));

    await _storage.setTokens(
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
    );

    AppLogger.info(
      '$successLogMessage (new_user: $isNewUser)',
      category: 'auth.telegram',
    );

    return TelegramAuthResult(user: user, tokens: tokens, isNewUser: isNewUser);
  }

  Map<String, dynamic> _normalizeTokensJson(Map<String, dynamic> json) {
    return <String, dynamic>{
      'accessToken': json['accessToken'] ?? json['access_token'],
      'refreshToken': json['refreshToken'] ?? json['refresh_token'],
      'expiresIn': json['expiresIn'] ?? json['expires_in'],
      'tokenType': json['tokenType'] ?? json['token_type'],
    };
  }

  Map<String, dynamic> _normalizeUserJson(Map<String, dynamic> json) {
    return <String, dynamic>{
      'id': (json['id'] ?? '').toString(),
      'email': (json['email'] ?? '').toString(),
      'username': json['username'],
      'avatarUrl': json['avatarUrl'] ?? json['avatar_url'] ?? json['picture'],
      'telegramId': (json['telegramId'] ?? json['telegram_id'])?.toString(),
      'isEmailVerified':
          json['isEmailVerified'] ?? json['is_email_verified'] ?? false,
      'isPremium': json['isPremium'] ?? json['is_premium'] ?? false,
      'referralCode': json['referralCode'] ?? json['referral_code'],
      'createdAt': json['createdAt'] ?? json['created_at'],
      'lastLoginAt': json['lastLoginAt'] ?? json['last_login_at'],
    };
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provider for [TelegramAuthService].
final telegramAuthServiceProvider = Provider<TelegramAuthService>((ref) {
  return TelegramAuthService(ref);
});
