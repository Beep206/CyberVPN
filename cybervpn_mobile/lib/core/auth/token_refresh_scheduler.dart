import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/auth/jwt_parser.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show authRepositoryProvider, secureStorageProvider;

/// How many minutes before expiry to trigger proactive refresh.
const int _refreshBufferMinutes = 5;

/// Minimum time to wait before scheduling a refresh (to avoid tight loops).
const int _minRefreshDelaySeconds = 30;

/// Schedules proactive token refresh before the access token expires.
///
/// This service:
/// - Parses the JWT access token to extract expiry time
/// - Schedules a refresh 5 minutes before expiry
/// - Handles refresh in the background without interrupting the user
/// - Atomically replaces tokens in SecureStorage on success
/// - Gracefully handles refresh failures (falls back to reactive refresh)
class TokenRefreshScheduler {
  final Ref _ref;
  Timer? _refreshTimer;
  bool _isRefreshing = false;

  TokenRefreshScheduler(this._ref);

  /// Schedules proactive token refresh based on the current access token.
  ///
  /// Call this after login/register or when restoring a session.
  Future<void> scheduleRefresh() async {
    // Cancel any existing timer
    cancel();

    try {
      final storage = _ref.read(secureStorageProvider);
      final accessToken = await storage.getAccessToken();

      if (accessToken == null || accessToken.isEmpty) {
        AppLogger.debug('No access token found, skipping refresh scheduling');
        return;
      }

      final payload = JwtParser.parse(accessToken);
      if (payload == null) {
        AppLogger.warning('Failed to parse JWT, skipping refresh scheduling');
        return;
      }

      if (payload.isExpired) {
        AppLogger.info('Access token already expired, triggering immediate refresh');
        unawaited(_triggerRefresh());
        return;
      }

      // Calculate when to refresh (5 minutes before expiry)
      final refreshAt = payload.expiresAt.subtract(
        const Duration(minutes: _refreshBufferMinutes),
      );
      var delay = refreshAt.difference(DateTime.now());

      // Ensure minimum delay to avoid tight refresh loops
      if (delay.inSeconds < _minRefreshDelaySeconds) {
        delay = const Duration(seconds: _minRefreshDelaySeconds);
      }

      AppLogger.info(
        'Token expires at ${payload.expiresAt}, scheduling refresh in ${delay.inMinutes}m ${delay.inSeconds % 60}s',
        category: 'auth.refresh',
      );

      _refreshTimer = Timer(delay, _triggerRefresh);
    } catch (e, st) {
      AppLogger.error(
        'Failed to schedule token refresh',
        error: e,
        stackTrace: st,
        category: 'auth.refresh',
      );
    }
  }

  /// Cancels any scheduled refresh.
  ///
  /// Call this on logout to prevent refreshing after sign-out.
  void cancel() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
    AppLogger.debug('Token refresh timer cancelled', category: 'auth.refresh');
  }

  /// Triggers the actual token refresh.
  Future<void> _triggerRefresh() async {
    if (_isRefreshing) {
      AppLogger.debug('Refresh already in progress, skipping');
      return;
    }

    _isRefreshing = true;
    try {
      final storage = _ref.read(secureStorageProvider);
      final deviceService = _ref.read(deviceServiceProvider);
      final repo = _ref.read(authRepositoryProvider);

      final refreshToken = await storage.getRefreshToken();
      final deviceId = await deviceService.getDeviceId();

      if (refreshToken == null || refreshToken.isEmpty) {
        AppLogger.warning('No refresh token available for proactive refresh');
        return;
      }

      AppLogger.info('Executing proactive token refresh', category: 'auth.refresh');

      // Perform the refresh
      await repo.refreshToken(
        refreshToken: refreshToken,
        deviceId: deviceId,
      );

      AppLogger.info('Proactive token refresh successful', category: 'auth.refresh');

      // Schedule the next refresh based on the new token
      await scheduleRefresh();
    } catch (e, st) {
      AppLogger.warning(
        'Proactive token refresh failed, will retry on next request',
        error: e,
        stackTrace: st,
        category: 'auth.refresh',
      );
      // Don't throw - the AuthInterceptor will handle 401s reactively
    } finally {
      _isRefreshing = false;
    }
  }

  /// Returns true if a refresh is currently scheduled.
  bool get isScheduled => _refreshTimer?.isActive ?? false;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provider for the [TokenRefreshScheduler].
///
/// Use this to schedule/cancel token refresh from the auth flow.
final tokenRefreshSchedulerProvider = Provider<TokenRefreshScheduler>((ref) {
  final scheduler = TokenRefreshScheduler(ref);

  // Cancel timer when provider is disposed
  ref.onDispose(scheduler.cancel);

  return scheduler;
});
