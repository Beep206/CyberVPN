import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/platform/telegram_native_auth_client.dart';
import 'package:cybervpn_mobile/core/platform/telegram_native_auth_method_channel.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
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

/// Launching the native Telegram SDK flow.
class TelegramAuthLaunchingNative extends TelegramAuthState {
  const TelegramAuthLaunchingNative();
}

/// Processing the callback auth_data.
class TelegramAuthProcessing extends TelegramAuthState {
  const TelegramAuthProcessing();
}

/// Exchanging Telegram native SDK `id_token` with the backend.
class TelegramAuthExchangingToken extends TelegramAuthState {
  const TelegramAuthExchangingToken();
}

/// Login is paused behind a pending TOTP challenge.
class TelegramAuthRequiresTwoFactor extends TelegramAuthState {
  final String method;

  const TelegramAuthRequiresTwoFactor({required this.method});
}

/// Completing a pending TOTP challenge.
class TelegramAuthCompletingTwoFactor extends TelegramAuthState {
  const TelegramAuthCompletingTwoFactor();
}

/// Authentication completed successfully.
class TelegramAuthSuccess extends TelegramAuthState {
  final UserEntity user;
  final bool isNewUser;

  const TelegramAuthSuccess({required this.user, required this.isNewUser});
}

/// Authentication failed.
class TelegramAuthError extends TelegramAuthState {
  final String code;
  final String message;

  const TelegramAuthError({required this.code, required this.message});
}

/// Telegram app is not installed on device.
class TelegramAuthNotInstalled extends TelegramAuthState {
  const TelegramAuthNotInstalled();
}

/// User cancelled the native Telegram SDK flow.
class TelegramAuthCancelled extends TelegramAuthState {
  const TelegramAuthCancelled();
}

/// Notifier for managing Telegram OAuth flow.
/// Uses [autoDispose] because Telegram auth state is only needed on login/register
/// screens. Resources are released when navigating away.
class TelegramAuthNotifier extends AsyncNotifier<TelegramAuthState> {
  String? _pendingTwoFactorToken;
  String? _pendingTwoFactorMethod;

  @override
  FutureOr<TelegramAuthState> build() {
    return const TelegramAuthIdle();
  }

  TelegramAuthService get _telegramService =>
      ref.read(telegramAuthServiceProvider);
  TelegramNativeAuthClient get _telegramNativeClient =>
      ref.read(telegramNativeAuthClientProvider);

  /// Starts the Telegram OAuth flow by launching the Login Widget.
  ///
  /// First checks if Telegram is installed. If not, transitions to
  /// [TelegramAuthNotInstalled] state so the UI can show install options.
  Future<void> startLogin() async {
    if (ref.read(telegramNativeLoginEnabledProvider)) {
      await loginWithTelegramNative();
      return;
    }

    if (!ref.read(telegramLegacyLoginAvailableProvider)) {
      state = const AsyncValue.data(
        TelegramAuthError(
          code: 'NOT_CONFIGURED',
          message: 'Telegram login is not configured',
        ),
      );
      return;
    }

    // Check if Telegram app is installed
    final isInstalled = await _telegramService.isTelegramInstalled();
    if (!isInstalled) {
      AppLogger.info(
        'Telegram app not installed, showing options',
        category: 'auth.telegram',
      );
      state = const AsyncValue.data(TelegramAuthNotInstalled());
      return;
    }

    state = const AsyncValue.data(TelegramAuthWaitingForCallback());

    AppLogger.info('Starting Telegram login flow', category: 'auth.telegram');

    final launched = await _telegramService.launchTelegramLogin();
    if (!launched) {
      state = const AsyncValue.data(
        TelegramAuthError(
          code: 'LAUNCH_FAILED',
          message: 'Could not open Telegram login',
        ),
      );
    }
    // If launched successfully, we stay in WaitingForCallback state
    // until handleCallback is called with auth_data
  }

  /// Starts Telegram login using the native iOS/Android SDK bridge.
  Future<void> loginWithTelegramNative() async {
    state = const AsyncValue.data(TelegramAuthLaunchingNative());

    try {
      final nativeResult = await _telegramNativeClient.login(
        requestPhone: ref.read(telegramNativePhoneScopeEnabledProvider),
      );

      state = const AsyncValue.data(TelegramAuthExchangingToken());
      final deviceService = ref.read(deviceServiceProvider);
      final deviceInfo = await deviceService.getDeviceInfo();

      final result = await _telegramService.authenticateWithIdToken(
        idToken: nativeResult.idToken,
        device: deviceInfo,
      );

      _completeAuthentication(result);
      AppLogger.info(
        'Telegram native auth successful (new_user: ${result.isNewUser})',
        category: 'auth.telegram.native',
      );
    } on TelegramNativeAuthCancelled {
      state = const AsyncValue.data(TelegramAuthCancelled());
      AppLogger.info(
        'Telegram native login cancelled by user',
        category: 'auth.telegram.native',
      );
    } on TelegramNativeAuthFailure catch (e) {
      _clearPendingTwoFactor();
      state = AsyncValue.data(
        TelegramAuthError(code: e.code, message: e.message),
      );
    } on TelegramAuthException catch (e) {
      if (e.code == 'TWO_FACTOR_REQUIRED' && e.tfaToken != null) {
        _pendingTwoFactorToken = e.tfaToken;
        _pendingTwoFactorMethod = e.method ?? 'totp';
        state = AsyncValue.data(
          TelegramAuthRequiresTwoFactor(
            method: _pendingTwoFactorMethod!,
          ),
        );
        return;
      }
      _clearPendingTwoFactor();
      state = AsyncValue.data(
        TelegramAuthError(code: e.code, message: e.message),
      );
    } catch (e, st) {
      _clearPendingTwoFactor();
      AppLogger.error(
        'Telegram native login failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram.native',
      );
      state = const AsyncValue.data(
        TelegramAuthError(
          code: 'NATIVE_AUTH_FAILED',
          message: 'Telegram native login failed.',
        ),
      );
    }
  }

  /// Opens the app store to install Telegram.
  Future<void> openAppStore() async {
    await _telegramService.openTelegramAppStore();
  }

  /// Uses web fallback for Telegram login (t.me link).
  Future<void> useWebFallback() async {
    state = const AsyncValue.data(TelegramAuthWaitingForCallback());

    final launched = await _telegramService.launchTelegramWebLogin();
    if (!launched) {
      state = const AsyncValue.data(
        TelegramAuthError(
          code: 'WEB_LAUNCH_FAILED',
          message: 'Could not open Telegram web login',
        ),
      );
    }
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
      _completeAuthentication(result);

      AppLogger.info(
        'Telegram auth successful (new_user: ${result.isNewUser})',
        category: 'auth.telegram',
      );
    } on TelegramAuthException catch (e) {
      _clearPendingTwoFactor();
      state = AsyncValue.data(
        TelegramAuthError(code: e.code, message: e.message),
      );
    } catch (e, st) {
      _clearPendingTwoFactor();
      AppLogger.error(
        'Telegram callback processing failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram',
      );
      state = const AsyncValue.data(
        TelegramAuthError(
          code: 'AUTH_FAILED',
          message: 'Telegram authentication failed',
        ),
      );
    }
  }

  /// Cancels the current login flow and resets to idle state.
  void cancel() {
    _clearPendingTwoFactor();
    state = const AsyncValue.data(TelegramAuthIdle());
  }

  /// Resets any error state back to idle.
  void resetError() {
    if (state.value is TelegramAuthError) {
      if (_pendingTwoFactorToken != null) {
        state = AsyncValue.data(
          TelegramAuthRequiresTwoFactor(
            method: _pendingTwoFactorMethod ?? 'totp',
          ),
        );
      } else {
        state = const AsyncValue.data(TelegramAuthIdle());
      }
    }
  }

  /// Completes a pending Telegram TOTP challenge.
  Future<void> completeTwoFactor(String code) async {
    final tfaToken = _pendingTwoFactorToken;
    if (tfaToken == null) {
      throw const TelegramAuthException(
        code: 'INVALID_2FA_TOKEN',
        message: 'Two-factor login session expired. Please try again.',
      );
    }

    state = const AsyncValue.data(TelegramAuthCompletingTwoFactor());

    try {
      final result = await _telegramService.completeTwoFactor(
        tfaToken: tfaToken,
        code: code,
      );
      _clearPendingTwoFactor();
      _completeAuthentication(result);
      AppLogger.info(
        'Telegram native 2FA challenge completed successfully',
        category: 'auth.telegram.native',
      );
    } on TelegramAuthException {
      state = AsyncValue.data(
        TelegramAuthRequiresTwoFactor(
          method: _pendingTwoFactorMethod ?? 'totp',
        ),
      );
      rethrow;
    } catch (e, st) {
      state = AsyncValue.data(
        TelegramAuthRequiresTwoFactor(
          method: _pendingTwoFactorMethod ?? 'totp',
        ),
      );
      AppLogger.error(
        'Telegram native 2FA completion failed',
        error: e,
        stackTrace: st,
        category: 'auth.telegram.native',
      );
      rethrow;
    }
  }

  void _completeAuthentication(TelegramAuthResult result) {
    _clearPendingTwoFactor();
    final userEntity = UserEntity(
      id: result.user.id,
      email: result.user.email,
      username: result.user.username,
      avatarUrl: result.user.avatarUrl,
      telegramId: result.user.telegramId,
      isEmailVerified: result.user.isEmailVerified,
      isPremium: result.user.isPremium,
      referralCode: result.user.referralCode,
      createdAt: result.user.createdAt,
      lastLoginAt: result.user.lastLoginAt,
    );

    state = AsyncValue.data(
      TelegramAuthSuccess(user: userEntity, isNewUser: result.isNewUser),
    );

    ref.read(authProvider.notifier).state = AsyncValue.data(
      AuthAuthenticated(userEntity),
    );
  }

  void _clearPendingTwoFactor() {
    _pendingTwoFactorToken = null;
    _pendingTwoFactorMethod = null;
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Provider for [TelegramAuthNotifier].
final telegramAuthProvider =
    AsyncNotifierProvider.autoDispose<TelegramAuthNotifier, TelegramAuthState>(
      TelegramAuthNotifier.new,
    );

/// Convenience provider for checking if Telegram login is available.
final isTelegramLoginAvailableProvider = Provider<bool>((ref) {
  return ref.watch(telegramNativeLoginEnabledProvider) ||
      ref.watch(telegramLegacyLoginAvailableProvider);
});

/// Convenience provider for checking if Telegram auth is in progress.
final isTelegramAuthLoadingProvider = Provider.autoDispose<bool>((ref) {
  final state = ref.watch(telegramAuthProvider).value;
  return state is TelegramAuthLaunchingNative ||
      state is TelegramAuthExchangingToken ||
      state is TelegramAuthCompletingTwoFactor ||
      state is TelegramAuthWaitingForCallback ||
      state is TelegramAuthProcessing;
});

final telegramLegacyLoginAvailableProvider = Provider<bool>((ref) {
  return EnvironmentConfig.isTelegramLegacyLoginAvailable;
});

final telegramNativeLoginIosEnabledProvider = Provider<bool>((ref) {
  return EnvironmentConfig.telegramNativeLoginIosEnabledFlag;
});

final telegramNativeLoginAndroidEnabledProvider = Provider<bool>((ref) {
  return EnvironmentConfig.telegramNativeLoginAndroidEnabledFlag;
});

final telegramNativeLoginEnabledProvider = Provider<bool>((ref) {
  return EnvironmentConfig.isTelegramNativeLoginEnabledForCurrentPlatform;
});

final telegramNativePhoneScopeEnabledProvider = Provider<bool>((ref) {
  return EnvironmentConfig.telegramNativePhoneScopeEnabled;
});

final isTelegramNativeLoginEnabledProvider = Provider<bool>((ref) {
  return ref.watch(telegramNativeLoginEnabledProvider);
});

final isTelegramLegacyLoginAvailableProvider = Provider<bool>((ref) {
  return ref.watch(telegramLegacyLoginAvailableProvider);
});
