import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:cybervpn_mobile/core/services/telegram_auth_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';

/// State for Telegram OAuth flow.
sealed class TelegramAuthState {
  const TelegramAuthState();
}

/// Initial state - not started.
class TelegramAuthIdle extends TelegramAuthState {
  const TelegramAuthIdle();
}

/// Waiting for user to complete Telegram login in external app.
class TelegramAuthWaitingForCallback extends TelegramAuthState {
  const TelegramAuthWaitingForCallback();
}

/// Processing the callback auth_data.
class TelegramAuthProcessing extends TelegramAuthState {
  const TelegramAuthProcessing();
}

/// Authentication completed successfully.
class TelegramAuthSuccess extends TelegramAuthState {
  final UserEntity user;
  final bool isNewUser;

  const TelegramAuthSuccess({
    required this.user,
    required this.isNewUser,
  });
}

/// Authentication failed.
class TelegramAuthError extends TelegramAuthState {
  final String code;
  final String message;

  const TelegramAuthError({
    required this.code,
    required this.message,
  });
}

/// Notifier for managing Telegram OAuth flow.
class TelegramAuthNotifier extends AsyncNotifier<TelegramAuthState> {
  @override
  FutureOr<TelegramAuthState> build() {
    return const TelegramAuthIdle();
  }

  TelegramAuthService get _telegramService =>
      ref.read(telegramAuthServiceProvider);

  /// Starts the Telegram OAuth flow by launching the Login Widget.
  Future<void> startLogin() async {
    if (!EnvironmentConfig.isTelegramLoginAvailable) {
      state = const AsyncValue.data(TelegramAuthError(
        code: 'NOT_CONFIGURED',
        message: 'Telegram login is not configured',
      ));
      return;
    }

    state = const AsyncValue.data(TelegramAuthWaitingForCallback());

    AppLogger.info('Starting Telegram login flow', category: 'auth.telegram');

    final launched = await _telegramService.launchTelegramLogin();
    if (!launched) {
      state = const AsyncValue.data(TelegramAuthError(
        code: 'LAUNCH_FAILED',
        message: 'Could not open Telegram. Is the app installed?',
      ));
    }
    // If launched successfully, we stay in WaitingForCallback state
    // until handleCallback is called with auth_data
  }

  /// Handles the deep link callback with Telegram auth_data.
  ///
  /// Called when the app receives a [TelegramAuthRoute] deep link.
  Future<void> handleCallback(String authData) async {
    state = const AsyncValue.data(TelegramAuthProcessing());

    AppLogger.info(
      'Processing Telegram callback auth_data',
      category: 'auth.telegram',
    );

    try {
      final deviceService = ref.read(deviceServiceProvider);
      final deviceInfo = await deviceService.getDeviceInfo();

      final result = await _telegramService.authenticateWithAuthData(
        authData: authData,
        device: deviceInfo,
      );

      // Convert UserModel to UserEntity
      final userEntity = UserEntity(
        id: result.user.id,
        email: result.user.email,
        username: result.user.username,
      );

      state = AsyncValue.data(TelegramAuthSuccess(
        user: userEntity,
        isNewUser: result.isNewUser,
      ));

      // Update the main auth provider state
      ref.read(authProvider.notifier).state = AsyncValue.data(
        AuthAuthenticated(userEntity),
      );

      AppLogger.info(
        'Telegram auth successful (new_user: ${result.isNewUser})',
        category: 'auth.telegram',
      );
    } on TelegramAuthException catch (e) {
      state = AsyncValue.data(TelegramAuthError(
        code: e.code,
        message: e.message,
      ));
    } catch (e, st) {
      AppLogger.error(
        'Telegram callback processing failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram',
      );
      state = const AsyncValue.data(TelegramAuthError(
        code: 'AUTH_FAILED',
        message: 'Telegram authentication failed',
      ));
    }
  }

  /// Cancels the current login flow and resets to idle state.
  void cancel() {
    state = const AsyncValue.data(TelegramAuthIdle());
  }

  /// Resets any error state back to idle.
  void resetError() {
    if (state.value is TelegramAuthError) {
      state = const AsyncValue.data(TelegramAuthIdle());
    }
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Provider for [TelegramAuthNotifier].
final telegramAuthProvider =
    AsyncNotifierProvider<TelegramAuthNotifier, TelegramAuthState>(
  TelegramAuthNotifier.new,
);

/// Convenience provider for checking if Telegram login is available.
final isTelegramLoginAvailableProvider = Provider<bool>((ref) {
  return EnvironmentConfig.isTelegramLoginAvailable;
});

/// Convenience provider for checking if Telegram auth is in progress.
final isTelegramAuthLoadingProvider = Provider<bool>((ref) {
  final state = ref.watch(telegramAuthProvider).value;
  return state is TelegramAuthWaitingForCallback ||
      state is TelegramAuthProcessing;
});
