import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb, visibleForTesting;
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/platform/telegram_native_auth_client.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class MethodChannelTelegramNativeAuthClient
    implements TelegramNativeAuthClient {
  const MethodChannelTelegramNativeAuthClient();

  static const MethodChannel _channel = MethodChannel(
    'com.cybervpn.cybervpn_mobile/telegram_native_auth',
  );

  @visibleForTesting
  static bool? debugIsSupportedOverride;

  bool get isSupported {
    final override = debugIsSupportedOverride;
    if (override != null) {
      return override;
    }

    if (kIsWeb) {
      return false;
    }

    return Platform.isIOS || Platform.isAndroid;
  }

  @override
  Future<TelegramNativeAuthResult> login({required bool requestPhone}) async {
    if (!isSupported) {
      throw const TelegramNativeAuthSdkError(
        'Telegram native login is only supported on iOS and Android.',
      );
    }

    final clientId = EnvironmentConfig.telegramOidcClientId;
    final redirectUri = EnvironmentConfig.telegramNativeRedirectUri;
    if (!EnvironmentConfig.isTelegramNativeLoginEnabledForCurrentPlatform ||
        clientId.isEmpty ||
        redirectUri.isEmpty) {
      throw const TelegramNativeAuthNotConfigured();
    }

    try {
      final response = await _channel.invokeMapMethod<String, dynamic>(
        'login',
        <String, dynamic>{
          'clientId': clientId,
          'redirectUri': redirectUri,
          'requestPhone': requestPhone,
          'scopes': <String>['profile', if (requestPhone) 'phone'],
        },
      );

      if (response == null) {
        throw const TelegramNativeAuthSdkError(
          'Telegram native login returned an empty response.',
        );
      }

      final idToken =
          (response['idToken'] as String?)?.trim() ??
          (response['id_token'] as String?)?.trim() ??
          '';
      if (idToken.isEmpty) {
        throw const TelegramNativeAuthSdkError(
          'Telegram native login did not return an ID token.',
        );
      }

      return TelegramNativeAuthResult(
        idToken: idToken,
        username:
            (response['username'] as String?) ??
            (response['preferred_username'] as String?),
        displayName:
            (response['displayName'] as String?) ??
            (response['name'] as String?),
        phoneNumber:
            (response['phoneNumber'] as String?) ??
            (response['phone_number'] as String?),
      );
    } on MissingPluginException catch (error, stackTrace) {
      AppLogger.error(
        'Telegram native login plugin is missing',
        error: error,
        stackTrace: stackTrace,
        category: 'auth.telegram.native',
      );
      throw const TelegramNativeAuthSdkError(
        'Telegram native login is not implemented in this build.',
      );
    } on PlatformException catch (error, stackTrace) {
      AppLogger.error(
        'Telegram native login platform call failed',
        error: error,
        stackTrace: stackTrace,
        category: 'auth.telegram.native',
      );
      switch (error.code) {
        case 'CANCELLED':
          throw const TelegramNativeAuthCancelled();
        case 'NOT_CONFIGURED':
          throw const TelegramNativeAuthNotConfigured();
        default:
          throw TelegramNativeAuthSdkError(
            error.message ?? 'Telegram native login failed.',
          );
      }
    }
  }
}

final telegramNativeAuthClientProvider = Provider<TelegramNativeAuthClient>((
  ref,
) {
  return const MethodChannelTelegramNativeAuthClient();
});
