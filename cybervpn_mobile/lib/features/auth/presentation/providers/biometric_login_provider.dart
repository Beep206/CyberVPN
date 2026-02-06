import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show secureStorageProvider;

/// State for biometric login flow.
sealed class BiometricLoginState {
  const BiometricLoginState();
}

/// Initial state - not yet checked.
class BiometricLoginIdle extends BiometricLoginState {
  const BiometricLoginIdle();
}

/// Biometric login is available and ready to be triggered.
class BiometricLoginAvailable extends BiometricLoginState {
  const BiometricLoginAvailable();
}

/// Biometric login is not available (not enabled, no credentials, etc.).
class BiometricLoginUnavailable extends BiometricLoginState {
  const BiometricLoginUnavailable();
}

/// Biometric prompt is being shown.
class BiometricLoginAuthenticating extends BiometricLoginState {
  const BiometricLoginAuthenticating();
}

/// Biometric succeeded, logging in with stored credentials.
class BiometricLoginLoggingIn extends BiometricLoginState {
  const BiometricLoginLoggingIn();
}

/// Biometric login succeeded.
class BiometricLoginSuccess extends BiometricLoginState {
  const BiometricLoginSuccess();
}

/// Biometric login failed.
class BiometricLoginFailed extends BiometricLoginState {
  final String message;
  const BiometricLoginFailed(this.message);
}

/// Stored credentials are invalid (password changed), credentials cleared.
/// User should re-enter password manually.
class BiometricLoginCredentialsInvalid extends BiometricLoginState {
  final String message;
  const BiometricLoginCredentialsInvalid(this.message);
}

/// Biometric login cancelled by user.
class BiometricLoginCancelled extends BiometricLoginState {
  const BiometricLoginCancelled();
}

/// Biometric enrollment has changed, credentials invalidated.
/// User needs to re-enable biometric login.
class BiometricLoginEnrollmentChanged extends BiometricLoginState {
  const BiometricLoginEnrollmentChanged();
}

/// Notifier for biometric login flow.
class BiometricLoginNotifier extends Notifier<BiometricLoginState> {
  @override
  BiometricLoginState build() => const BiometricLoginIdle();

  BiometricService get _biometricService =>
      ref.read(biometricServiceProvider);
  SecureStorageWrapper get _storage => ref.read(secureStorageProvider);
  AuthNotifier get _authNotifier => ref.read(authProvider.notifier);

  /// Checks if biometric login should be available for the user.
  ///
  /// Returns `true` if:
  /// - Biometric hardware is available on the device
  /// - User has enabled biometric login in settings
  /// - User has stored credentials from a previous login
  Future<bool> checkAvailability() async {
    try {
      // Check if biometric hardware is available
      final isAvailable = await _biometricService.isBiometricAvailable();
      if (!isAvailable) {
        AppLogger.info(
          'Biometric login unavailable: no biometric hardware',
          category: 'auth.biometric',
        );
        state = const BiometricLoginUnavailable();
        return false;
      }

      // Check if user has enabled biometric login
      final isEnabled = await _biometricService.isBiometricEnabled();
      if (!isEnabled) {
        AppLogger.info(
          'Biometric login unavailable: not enabled by user',
          category: 'auth.biometric',
        );
        state = const BiometricLoginUnavailable();
        return false;
      }

      // Check if enrollment has changed
      final enrollmentChanged = await _biometricService.hasEnrollmentChanged();
      if (enrollmentChanged) {
        AppLogger.warning(
          'Biometric enrollment changed - invalidating credentials',
          category: 'auth.biometric',
        );
        // Clear stored credentials
        await _storage.clearBiometricCredentials();
        // Disable biometric login (user needs to re-enable)
        await _biometricService.setBiometricEnabled(false);
        state = const BiometricLoginEnrollmentChanged();
        return false;
      }

      // Check if credentials are stored
      final credentials = await _storage.getBiometricCredentials();
      if (credentials == null) {
        AppLogger.info(
          'Biometric login unavailable: no stored credentials',
          category: 'auth.biometric',
        );
        state = const BiometricLoginUnavailable();
        return false;
      }

      AppLogger.info(
        'Biometric login is available',
        category: 'auth.biometric',
      );
      state = const BiometricLoginAvailable();
      return true;
    } catch (e, st) {
      AppLogger.error(
        'Failed to check biometric availability',
        error: e,
        stackTrace: st,
        category: 'auth.biometric',
      );
      state = const BiometricLoginUnavailable();
      return false;
    }
  }

  /// Triggers biometric authentication and logs in on success.
  ///
  /// Call [checkAvailability] first to ensure biometric login is available.
  Future<void> authenticate({
    String reason = 'Authenticate to sign in',
  }) async {
    // Ensure we're in a valid state to authenticate
    if (state is BiometricLoginAuthenticating ||
        state is BiometricLoginLoggingIn) {
      return;
    }

    state = const BiometricLoginAuthenticating();

    try {
      // Show biometric prompt
      final authenticated =
          await _biometricService.authenticate(reason: reason);

      if (!authenticated) {
        AppLogger.info(
          'Biometric authentication cancelled or failed',
          category: 'auth.biometric',
        );
        state = const BiometricLoginCancelled();
        return;
      }

      // Biometric succeeded - retrieve credentials and log in
      state = const BiometricLoginLoggingIn();

      final credentials = await _storage.getBiometricCredentials();
      if (credentials == null) {
        AppLogger.warning(
          'Biometric succeeded but no credentials found',
          category: 'auth.biometric',
        );
        state = const BiometricLoginFailed('No stored credentials');
        return;
      }

      // Perform login with stored credentials
      await _authNotifier.login(
        credentials.email,
        credentials.password,
        rememberMe: true, // Biometric users want to stay logged in
      );

      // Check if login was successful by reading the auth state
      final authState = ref.read(authProvider).value;
      if (authState is AuthError) {
        // Login failed - credentials are likely invalid (password changed)
        AppLogger.warning(
          'Biometric login failed: ${authState.message}',
          category: 'auth.biometric',
        );

        // Clear invalid credentials
        await _storage.clearBiometricCredentials();
        AppLogger.info(
          'Cleared invalid biometric credentials',
          category: 'auth.biometric',
        );

        state = BiometricLoginCredentialsInvalid(authState.message);
        return;
      }

      AppLogger.info(
        'Biometric login successful',
        category: 'auth.biometric',
      );
      state = const BiometricLoginSuccess();
    } catch (e, st) {
      AppLogger.error(
        'Biometric login failed',
        error: e,
        stackTrace: st,
        category: 'auth.biometric',
      );

      // If it's an auth-related error, clear credentials
      final errorMsg = e.toString().toLowerCase();
      if (errorMsg.contains('unauthorized') ||
          errorMsg.contains('invalid') ||
          errorMsg.contains('401')) {
        await _storage.clearBiometricCredentials();
        state = BiometricLoginCredentialsInvalid(e.toString());
      } else {
        state = BiometricLoginFailed(e.toString());
      }
    }
  }

  /// Resets the state to idle.
  void reset() {
    state = const BiometricLoginIdle();
  }
}

// ---------------------------------------------------------------------------
// Riverpod Providers
// ---------------------------------------------------------------------------

/// Provider for [BiometricLoginNotifier].
final biometricLoginProvider =
    NotifierProvider<BiometricLoginNotifier, BiometricLoginState>(
  BiometricLoginNotifier.new,
);

/// Provider that checks if biometric login should be shown on the login screen.
///
/// Returns `true` if biometric login is available and configured.
final shouldShowBiometricLoginProvider = FutureProvider<bool>((ref) async {
  final notifier = ref.read(biometricLoginProvider.notifier);
  return notifier.checkAvailability();
});
