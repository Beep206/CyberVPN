import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/services/fcm_token_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';

// ---------------------------------------------------------------------------
// Repository provider
// ---------------------------------------------------------------------------

/// Provides the [AuthRepository] implementation.
///
/// Override this in tests to inject a mock repository.
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  // These concrete datasource / network-info instances are placeholders.
  // In production they would be supplied through their own providers.
  throw UnimplementedError(
    'authRepositoryProvider must be overridden with a concrete '
    'AuthRepository (e.g. via ProviderScope overrides).',
  );
});

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

  @override
  FutureOr<AuthState> build() async {
    // Attempt auto-login from cached tokens.
    return _checkCachedAuth();
  }

  /// Checks whether a cached session exists and returns the appropriate state.
  Future<AuthState> _checkCachedAuth() async {
    try {
      final isAuthed = await _repo.isAuthenticated();
      if (!isAuthed) return const AuthUnauthenticated();

      final user = await _repo.getCurrentUser();
      if (user != null) {
        _setSentryUser(user);
        return AuthAuthenticated(user);
      }
      return const AuthUnauthenticated();
    } catch (e) {
      return AuthError(e.toString());
    }
  }

  /// Authenticate with [email] and [password].
  Future<void> login(String email, String password) async {
    state = const AsyncValue.data(AuthLoading());
    try {
      final (user, _) = await _repo.login(email: email, password: password);
      _setSentryUser(user);
      state = AsyncValue.data(AuthAuthenticated(user));

      // Register FCM token after successful login (non-blocking)
      _registerFcmToken();
    } catch (e, st) {
      state = AsyncValue.data(AuthError(e.toString()));
    }
  }

  /// Register a new account with [email], [password], and optional [username].
  ///
  /// The [username] is reserved for future use; the underlying repository
  /// currently accepts an optional referral code in that position.
  Future<void> register(String email, String password, String? username) async {
    state = const AsyncValue.data(AuthLoading());
    try {
      final (user, _) = await _repo.register(
        email: email,
        password: password,
        referralCode: username, // mapped to referralCode in the repo
      );
      _setSentryUser(user);
      state = AsyncValue.data(AuthAuthenticated(user));

      // Register FCM token after successful registration (non-blocking)
      _registerFcmToken();
    } catch (e, st) {
      state = AsyncValue.data(AuthError(e.toString()));
    }
  }

  /// Sign out and clear cached tokens.
  Future<void> logout() async {
    state = const AsyncValue.data(AuthLoading());
    try {
      await _repo.logout();
      _clearSentryUser();
      // Invalidate the notifier so all dependent providers reset.
      ref.invalidateSelf();
      state = const AsyncValue.data(AuthUnauthenticated());
    } catch (e, st) {
      state = AsyncValue.data(AuthError(e.toString()));
    }
  }

  /// Re-check authentication status (e.g. after token refresh).
  Future<void> checkAuthStatus() async {
    state = const AsyncValue.data(AuthLoading());
    final result = await _checkCachedAuth();
    state = AsyncValue.data(result);
  }

  // ── Sentry user context ─────────────────────────────────────────────

  /// Associates the authenticated [user] with Sentry so crash reports
  /// include the user's identity.
  void _setSentryUser(UserEntity user) {
    if (EnvironmentConfig.sentryDsn.isEmpty) return;
    Sentry.configureScope((scope) {
      scope.setUser(SentryUser(
        id: user.id,
        email: user.email,
        username: user.username,
      ));
    });
  }

  /// Removes the Sentry user context on logout.
  void _clearSentryUser() {
    if (EnvironmentConfig.sentryDsn.isEmpty) return;
    Sentry.configureScope((scope) {
      scope.setUser(null);
    });
  }

  // ── FCM token registration ──────────────────────────────────────────

  /// Registers the FCM device token with the backend after successful login.
  ///
  /// Runs asynchronously without blocking the auth flow. Errors are logged
  /// but do not affect the authentication state.
  void _registerFcmToken() {
    // Run in a fire-and-forget manner
    Future(() async {
      try {
        final fcmService = ref.read(fcmTokenServiceProvider);
        await fcmService.registerToken();
      } catch (e, st) {
        // Log but don't throw - FCM registration failure should not
        // block the user from proceeding with the app
        AppLogger.error(
          'Failed to register FCM token after login',
          error: e,
          stackTrace: st,
          category: 'auth',
        );

        // Also report to Sentry if configured
        if (EnvironmentConfig.sentryDsn.isNotEmpty) {
          Sentry.captureException(e, stackTrace: st);
        }
      }
    });
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
  final authState = ref.watch(authProvider).value;
  if (authState is AuthAuthenticated) {
    return authState.user;
  }
  return null;
});

/// Derived provider that yields `true` when the user is authenticated.
final isAuthenticatedProvider = Provider<bool>((ref) {
  final authState = ref.watch(authProvider).value;
  return authState is AuthAuthenticated;
});
