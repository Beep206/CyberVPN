import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/auth/token_refresh_scheduler.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
import 'package:cybervpn_mobile/core/device/device_service.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/utils/performance_profiler.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/login.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/register.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show authRepositoryProvider, loginUseCaseProvider, registerUseCaseProvider;

// ---------------------------------------------------------------------------
// Auth notifier
// ---------------------------------------------------------------------------

/// Manages authentication state for the application.
///
/// On [build] it checks for a cached session (auto-login).  Exposes
/// [login], [register], [logout], and [checkAuthStatus] for explicit
/// auth operations.
class AuthNotifier extends AsyncNotifier<AuthState> {
  AuthRepository get _repo => ref.read(authRepositoryProvider);
  LoginUseCase get _loginUseCase => ref.read(loginUseCaseProvider);
  RegisterUseCase get _registerUseCase => ref.read(registerUseCaseProvider);
  DeviceService get _deviceService => ref.read(deviceServiceProvider);
  SecureStorageWrapper get _storage => ref.read(secureStorageProvider);
  TokenRefreshScheduler get _refreshScheduler =>
      ref.read(tokenRefreshSchedulerProvider);
  WebSocketClient get _webSocketClient =>
      ref.read(webSocketClientProvider);

  @override
  FutureOr<AuthState> build() async {
    // Attempt auto-login from cached tokens.
    return _checkCachedAuth();
  }

  /// Checks whether a cached session exists and returns the appropriate state.
  ///
  /// Performance target: < 200ms for cached auth check.
  /// Hard timeout of 3 seconds prevents the splash screen from hanging
  /// indefinitely when the repository is unreachable.
  Future<AuthState> _checkCachedAuth() async {
    final profiler = AppProfilers.authCheck();
    profiler.start();

    try {
      final result = await _performCachedAuthCheck(profiler)
          .timeout(
        const Duration(seconds: 3),
        onTimeout: () {
          AppLogger.warning(
            'Cached auth check timed out after 3 s, treating as unauthenticated',
            category: 'auth',
          );
          profiler.stop();
          return const AuthUnauthenticated();
        },
      );
      return result;
    } catch (e) {
      profiler.stop();
      return AuthError(e.toString());
    }
  }

  /// Inner implementation extracted so [_checkCachedAuth] can apply a
  /// [Future.timeout] wrapper around the entire operation.
  Future<AuthState> _performCachedAuthCheck(PerformanceProfiler profiler) async {
    final authResult = await _repo.isAuthenticated();
    profiler.checkpoint('token_check');

    final isAuthed = switch (authResult) {
      Success(:final data) => data,
      Failure() => false,
    };

    if (!isAuthed) {
      profiler.stop();
      return const AuthUnauthenticated();
    }

    final userResult = await _repo.getCurrentUser();
    profiler.checkpoint('user_fetch');

    final user = userResult.dataOrNull;

    if (user != null) {
      // Schedule proactive token refresh for existing session (non-blocking)
      _scheduleTokenRefresh();

      // Connect WebSocket for real-time updates (non-blocking)
      _connectWebSocket();

      profiler.stop();
      return AuthAuthenticated(user);
    }

    profiler.stop();
    return const AuthUnauthenticated();
  }

  /// Authenticate with [email] and [password].
  ///
  /// If [rememberMe] is true, the refresh token TTL is extended to 30 days.
  Future<void> login(String email, String password, {bool rememberMe = false}) async {
    state = const AsyncValue.data(AuthLoading());
    try {
      // Get device info for the login request
      final deviceInfo = await _deviceService.getDeviceInfo();

      // UseCase validates email/password before making network request
      final result = await _loginUseCase(
        email: email,
        password: password,
        device: deviceInfo,
        rememberMe: rememberMe,
      );
      switch (result) {
        case Success(:final data):
          final (user, _) = data;
          state = AsyncValue.data(AuthAuthenticated(user));

          // Schedule proactive token refresh (non-blocking)
          _scheduleTokenRefresh();

          // Connect WebSocket for real-time updates (non-blocking)
          _connectWebSocket();
        case Failure(:final failure):
          state = AsyncValue.data(AuthError(failure.message));
      }
    } catch (e) {
      state = AsyncValue.data(AuthError(e.toString()));
    }
  }

  /// Register a new account with [email], [password], and optional [referralCode].
  Future<void> register(String email, String password, {String? referralCode}) async {
    state = const AsyncValue.data(AuthLoading());
    try {
      // Get device info for the register request
      final deviceInfo = await _deviceService.getDeviceInfo();

      // UseCase validates email/password/referralCode before making network request
      final result = await _registerUseCase(
        email: email,
        password: password,
        device: deviceInfo,
        referralCode: referralCode,
      );
      switch (result) {
        case Success(:final data):
          final (user, _) = data;
          state = AsyncValue.data(AuthAuthenticated(user));

          // Schedule proactive token refresh (non-blocking)
          _scheduleTokenRefresh();

          // Connect WebSocket for real-time updates (non-blocking)
          _connectWebSocket();
        case Failure(:final failure):
          state = AsyncValue.data(AuthError(failure.message));
      }
    } catch (e) {
      state = AsyncValue.data(AuthError(e.toString()));
    }
  }

  /// Sign out and clear cached tokens.
  Future<void> logout() async {
    state = const AsyncValue.data(AuthLoading());

    // Cancel proactive token refresh before logout
    _refreshScheduler.cancel();

    // Disconnect WebSocket before clearing auth state
    await _disconnectWebSocket();

    try {
      // Get current tokens and device ID for logout request
      final refreshToken = await _storage.getRefreshToken();
      final deviceId = await _deviceService.getDeviceId();

      if (refreshToken != null && refreshToken.isNotEmpty) {
        final logoutResult = await _repo.logout(
          refreshToken: refreshToken,
          deviceId: deviceId,
        );
        if (logoutResult is Failure) {
          AppLogger.warning('Logout backend returned failure: ${logoutResult.failureOrNull?.message}');
        }
      }
      // Invalidate the notifier so all dependent providers reset.
      ref.invalidateSelf();
      state = const AsyncValue.data(AuthUnauthenticated());
    } catch (e) {
      // Even if backend logout fails, clear local state
      ref.invalidateSelf();
      state = const AsyncValue.data(AuthUnauthenticated());
      AppLogger.warning('Logout backend call failed, cleared local state', error: e);
    }
  }

  /// Re-check authentication status (e.g. after token refresh).
  Future<void> checkAuthStatus() async {
    state = const AsyncValue.data(AuthLoading());
    final result = await _checkCachedAuth();
    state = AsyncValue.data(result);
  }

  // ── Proactive token refresh ────────────────────────────────────────

  /// Schedules proactive token refresh based on access token expiry.
  ///
  /// Runs asynchronously without blocking the auth flow. Errors are logged
  /// but do not affect the authentication state.
  void _scheduleTokenRefresh() {
    unawaited(Future(() async {
      try {
        await _refreshScheduler.scheduleRefresh();
      } catch (e, st) {
        AppLogger.warning(
          'Failed to schedule proactive token refresh',
          error: e,
          stackTrace: st,
          category: 'auth.refresh',
        );
      }
    }));
  }

  // ── WebSocket connection management ──────────────────────────────

  /// Connects the WebSocket client for real-time server events.
  ///
  /// Runs asynchronously without blocking the auth flow. Errors are logged
  /// but do not affect the authentication state.
  void _connectWebSocket() {
    unawaited(Future(() async {
      try {
        await _webSocketClient.connect();
        AppLogger.info(
          'WebSocket connected after authentication',
          category: 'auth.websocket',
        );
      } catch (e, st) {
        AppLogger.warning(
          'Failed to connect WebSocket after authentication',
          error: e,
          stackTrace: st,
          category: 'auth.websocket',
        );
      }
    }));
  }

  /// Disconnects the WebSocket client on logout.
  ///
  /// Awaited to ensure clean disconnection before auth state is cleared.
  Future<void> _disconnectWebSocket() async {
    try {
      await _webSocketClient.disconnect();
      AppLogger.info(
        'WebSocket disconnected on logout',
        category: 'auth.websocket',
      );
    } catch (e, st) {
      AppLogger.warning(
        'Failed to disconnect WebSocket on logout',
        error: e,
        stackTrace: st,
        category: 'auth.websocket',
      );
    }
  }

}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Primary auth state provider backed by [AuthNotifier].
final authProvider = AsyncNotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
);

/// Derived provider that yields the current [UserEntity] or `null`.
final currentUserProvider = Provider<UserEntity?>((ref) {
  return switch (ref.watch(authProvider).value) {
    AuthAuthenticated(:final user) => user,
    _ => null,
  };
});

/// Derived provider that yields `true` when the user is authenticated.
final isAuthenticatedProvider = Provider<bool>((ref) {
  final authState = ref.watch(authProvider).value;
  return authState is AuthAuthenticated;
});
