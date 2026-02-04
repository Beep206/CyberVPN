import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/security/app_attestation.dart';
import 'package:cybervpn_mobile/core/services/fcm_token_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/data/services/session_restoration_service.dart';
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

/// Provides the [SessionRestorationService] for silent session restoration.
///
/// Override this in tests to inject a mock service.
final sessionRestorationServiceProvider = Provider<SessionRestorationService>((ref) {
  throw UnimplementedError(
    'sessionRestorationServiceProvider must be overridden with a concrete '
    'SessionRestorationService (e.g. via ProviderScope overrides).',
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
  SessionRestorationService? _sessionService;
  StreamSubscription<TokenRefreshResult>? _refreshSubscription;

  @override
  FutureOr<AuthState> build() async {
    // Clean up previous subscription on rebuild
    _refreshSubscription?.cancel();

    // Attempt silent session restoration from cached tokens.
    return _restoreSession();
  }

  /// Performs silent session restoration on app launch.
  ///
  /// Uses [SessionRestorationService] for fast-path restoration:
  /// 1. Returns cached user immediately (< 200ms target)
  /// 2. Refreshes tokens in background
  /// 3. Handles refresh failure by emitting [AuthSessionExpired]
  Future<AuthState> _restoreSession() async {
    try {
      _sessionService = ref.read(sessionRestorationServiceProvider);

      final result = await _sessionService!.restoreSession();

      switch (result) {
        case SessionRestored(:final user, :final backgroundRefreshPending):
          _setSentryUser(user);

          if (backgroundRefreshPending) {
            // Listen for background refresh result
            _refreshSubscription = _sessionService!.refreshResultStream.listen(
              _handleRefreshResult,
            );
          }

          return AuthAuthenticated(user);

        case SessionNotFound():
          return const AuthUnauthenticated();

        case SessionExpired(:final reason):
          return AuthSessionExpired(message: reason);
      }
    } on UnimplementedError {
      // SessionRestorationService not configured - fall back to legacy check
      return _checkCachedAuth();
    } catch (e) {
      return AuthError(e.toString());
    }
  }

  /// Handles background token refresh result.
  void _handleRefreshResult(TokenRefreshResult result) {
    switch (result) {
      case TokenRefreshSuccess(:final updatedUser):
        // If we got an updated user, refresh the state
        if (updatedUser != null) {
          _setSentryUser(updatedUser);
          state = AsyncValue.data(AuthAuthenticated(updatedUser));
        }
        AppLogger.debug(
          'Background refresh succeeded',
          category: 'auth.session',
        );

      case TokenRefreshFailure(:final reason):
        // Session expired - user must re-authenticate
        AppLogger.warning(
          'Background refresh failed: $reason',
          category: 'auth.session',
        );
        _clearSentryUser();
        state = AsyncValue.data(AuthSessionExpired(message: reason));
    }
  }

  /// Legacy fallback for session check when SessionRestorationService is not configured.
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

      // Perform app attestation in logging mode (non-blocking)
      _performAttestation(AttestationTrigger.login);
    } catch (e) {
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
    } catch (e) {
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
    } catch (e) {
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

  // ── App attestation (logging mode) ─────────────────────────────────

  /// Performs app attestation for fraud detection (logging mode only).
  ///
  /// Runs asynchronously without blocking the auth flow. Results are logged
  /// to analytics and Sentry for monitoring. Never enforces (blocks) on
  /// failure in current logging-only mode.
  void _performAttestation(AttestationTrigger trigger) {
    // Run in a fire-and-forget manner
    Future(() async {
      try {
        final attestationService = ref.read(appAttestationServiceProvider);
        final result = await attestationService.generateToken(trigger: trigger);
        AppLogger.info(
          'Attestation completed: ${result.status.name}',
          category: 'auth.attestation',
        );
      } catch (e, st) {
        // Log but don't throw - attestation failure should not
        // block the user from proceeding with the app
        AppLogger.warning(
          'Attestation failed (non-blocking)',
          error: e,
          stackTrace: st,
          category: 'auth.attestation',
        );
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
