import 'dart:async';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_remote_ds.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';

/// Result of silent session restoration on app launch.
sealed class SessionRestorationResult {
  const SessionRestorationResult();
}

/// User is authenticated with valid session.
final class SessionRestored extends SessionRestorationResult {
  /// The authenticated user (from cache, possibly stale).
  final UserEntity user;

  /// Whether a background token refresh is in progress.
  ///
  /// If true, the caller should listen to [SessionRestorationService.refreshResultStream]
  /// for the final result.
  final bool backgroundRefreshPending;

  const SessionRestored({
    required this.user,
    this.backgroundRefreshPending = false,
  });
}

/// No valid session exists - user must authenticate.
final class SessionNotFound extends SessionRestorationResult {
  const SessionNotFound();
}

/// Session was found but token refresh failed - user must re-authenticate.
final class SessionExpired extends SessionRestorationResult {
  /// Error message explaining why the session expired.
  final String reason;

  const SessionExpired({required this.reason});
}

/// Result of background token refresh.
sealed class TokenRefreshResult {
  const TokenRefreshResult();
}

/// Token refresh succeeded.
final class TokenRefreshSuccess extends TokenRefreshResult {
  /// Updated user entity (if profile was refreshed).
  final UserEntity? updatedUser;

  const TokenRefreshSuccess({this.updatedUser});
}

/// Token refresh failed - session should be invalidated.
final class TokenRefreshFailure extends TokenRefreshResult {
  /// Error reason for logging/display.
  final String reason;

  const TokenRefreshFailure({required this.reason});
}

/// Service for silent session restoration on app launch.
///
/// Implements a fast-path strategy:
/// 1. Check for cached refresh token (< 50ms)
/// 2. Return cached user immediately for instant UI display
/// 3. Trigger background token refresh
/// 4. Emit result on [refreshResultStream]
///
/// ## Usage
/// ```dart
/// final service = SessionRestorationService(...);
/// final result = await service.restoreSession();
///
/// switch (result) {
///   case SessionRestored(:final user, :final backgroundRefreshPending):
///     // Show home screen with cached user
///     if (backgroundRefreshPending) {
///       // Listen for refresh result
///       service.refreshResultStream.listen((refreshResult) {
///         if (refreshResult is TokenRefreshFailure) {
///           // Session expired - redirect to login
///         }
///       });
///     }
///   case SessionNotFound():
///     // Show login screen
///   case SessionExpired(:final reason):
///     // Show login screen with "Session expired" message
/// }
/// ```
class SessionRestorationService {
  final AuthLocalDataSource _localDataSource;
  final AuthRemoteDataSource _remoteDataSource;

  final StreamController<TokenRefreshResult> _refreshResultController =
      StreamController<TokenRefreshResult>.broadcast();

  /// Stream of background token refresh results.
  ///
  /// Listen to this after [restoreSession] returns [SessionRestored]
  /// with [backgroundRefreshPending] = true.
  Stream<TokenRefreshResult> get refreshResultStream =>
      _refreshResultController.stream;

  SessionRestorationService({
    required AuthLocalDataSource localDataSource,
    required AuthRemoteDataSource remoteDataSource,
  })  : _localDataSource = localDataSource,
        _remoteDataSource = remoteDataSource;

  /// Attempts to restore the user session from cached tokens.
  ///
  /// Returns quickly with cached user data, then refreshes tokens in background.
  /// Target latency: < 200ms for initial result.
  ///
  /// Returns:
  /// - [SessionRestored] if valid tokens and cached user exist
  /// - [SessionNotFound] if no tokens are cached
  /// - [SessionExpired] if tokens exist but are invalid
  Future<SessionRestorationResult> restoreSession() async {
    final stopwatch = Stopwatch()..start();

    try {
      // Step 1: Check for cached token (fast path)
      final cachedToken = await _localDataSource.getCachedToken();

      if (cachedToken == null) {
        AppLogger.debug(
          'Session restoration: no cached token (${stopwatch.elapsedMilliseconds}ms)',
          category: 'auth.session',
        );
        return const SessionNotFound();
      }

      // Step 2: Get cached user for instant display
      final cachedUser = await _localDataSource.getCachedUser();

      if (cachedUser == null) {
        // Token exists but no cached user - try to fetch from network
        AppLogger.debug(
          'Session restoration: token found but no cached user, '
          'attempting network fetch (${stopwatch.elapsedMilliseconds}ms)',
          category: 'auth.session',
        );
        return _fetchUserAndValidateSession(cachedToken.refreshToken);
      }

      final userEntity = cachedUser.toEntity();

      AppLogger.info(
        'Session restoration: cached user found in ${stopwatch.elapsedMilliseconds}ms',
        category: 'auth.session',
      );

      // Step 3: Trigger background token refresh
      _backgroundRefresh(cachedToken.refreshToken);

      return SessionRestored(
        user: userEntity,
        backgroundRefreshPending: true,
      );
    } catch (e, st) {
      AppLogger.error(
        'Session restoration failed (${stopwatch.elapsedMilliseconds}ms)',
        error: e,
        stackTrace: st,
        category: 'auth.session',
      );
      return SessionExpired(reason: e.toString());
    }
  }

  /// Fetches user from network when cached user is missing.
  Future<SessionRestorationResult> _fetchUserAndValidateSession(
    String refreshToken,
  ) async {
    try {
      // Refresh token first to ensure we have a valid access token
      final newTokens = await _remoteDataSource.refreshToken(refreshToken);
      await _localDataSource.cacheToken(newTokens);

      // Fetch user profile
      final userModel = await _remoteDataSource.getCurrentUser();
      await _localDataSource.cacheUser(userModel);

      return SessionRestored(
        user: userModel.toEntity(),
        backgroundRefreshPending: false,
      );
    } catch (e) {
      AppLogger.warning(
        'Session validation failed: $e',
        category: 'auth.session',
      );
      // Clear invalid tokens
      await _localDataSource.clearAuth();
      return const SessionExpired(reason: 'Your session has expired. Please log in again.');
    }
  }

  /// Performs background token refresh.
  void _backgroundRefresh(String refreshToken) {
    Future(() async {
      try {
        AppLogger.debug(
          'Background token refresh started',
          category: 'auth.session',
        );

        final newTokens = await _remoteDataSource.refreshToken(refreshToken);
        await _localDataSource.cacheToken(newTokens);

        // Optionally refresh user profile
        try {
          final userModel = await _remoteDataSource.getCurrentUser();
          await _localDataSource.cacheUser(userModel);
          _refreshResultController.add(TokenRefreshSuccess(
            updatedUser: userModel.toEntity(),
          ));
        } catch (e) {
          // User fetch failed but token refresh succeeded
          _refreshResultController.add(const TokenRefreshSuccess());
        }

        AppLogger.info(
          'Background token refresh completed',
          category: 'auth.session',
        );
      } catch (e, st) {
        AppLogger.warning(
          'Background token refresh failed',
          error: e,
          stackTrace: st,
          category: 'auth.session',
        );

        // Notify listeners that the session is invalid
        _refreshResultController.add(const TokenRefreshFailure(
          reason: 'Your session has expired. Please log in again.',
        ));
      }
    });
  }

  /// Disposes the service and cleans up resources.
  Future<void> dispose() async {
    await _refreshResultController.close();
  }
}
