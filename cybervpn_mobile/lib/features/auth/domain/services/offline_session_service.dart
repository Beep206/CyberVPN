import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/auth/jwt_parser.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show networkInfoProvider, secureStorageProvider;

/// Offline session validation result.
enum OfflineSessionStatus {
  /// Device is online - normal operation.
  online,

  /// Device is offline but has a valid cached session.
  offlineWithValidSession,

  /// Device is offline and session is expired.
  offlineWithExpiredSession,

  /// Device is offline and no session is cached.
  offlineNoSession,
}

/// Service for validating sessions when offline.
///
/// Allows the app to function in a limited capacity when the device is offline
/// by validating cached tokens locally.
class OfflineSessionService {
  final NetworkInfo _networkInfo;
  final SecureStorageWrapper _storage;

  /// Grace period for token expiry validation (minutes).
  /// Cached tokens are considered valid if they haven't expired
  /// plus this grace period.
  static const int _offlineGracePeriodMinutes = 60;

  OfflineSessionService({
    required NetworkInfo networkInfo,
    required SecureStorageWrapper storage,
  })  : _networkInfo = networkInfo,
        _storage = storage;

  /// Checks the current network connectivity.
  Future<bool> isOnline() async {
    return _networkInfo.isConnected;
  }

  /// Stream of connectivity changes.
  Stream<bool> get onConnectivityChanged => _networkInfo.onConnectivityChanged;

  /// Validates the offline session status.
  ///
  /// Returns the appropriate [OfflineSessionStatus] based on:
  /// - Current network connectivity
  /// - Presence of cached tokens
  /// - Token expiry time (with grace period for offline use)
  Future<OfflineSessionStatus> validateSession() async {
    // Check if online first
    if (await isOnline()) {
      return OfflineSessionStatus.online;
    }

    // Offline - check for cached session
    final accessToken = await _storage.getAccessToken();
    if (accessToken == null || accessToken.isEmpty) {
      AppLogger.info(
        'Offline with no cached session',
        category: 'auth.offline',
      );
      return OfflineSessionStatus.offlineNoSession;
    }

    // Parse token to check expiry
    final payload = JwtParser.parse(accessToken);
    if (payload == null) {
      AppLogger.warning(
        'Offline - failed to parse cached token',
        category: 'auth.offline',
      );
      return OfflineSessionStatus.offlineWithExpiredSession;
    }

    // Check if token is expired (with grace period)
    final now = DateTime.now();
    final expiryWithGrace = payload.expiresAt.add(
      const Duration(minutes: _offlineGracePeriodMinutes),
    );

    if (now.isAfter(expiryWithGrace)) {
      AppLogger.info(
        'Offline - session expired (expired: ${payload.expiresAt})',
        category: 'auth.offline',
      );
      return OfflineSessionStatus.offlineWithExpiredSession;
    }

    AppLogger.info(
      'Offline - valid session (expires: ${payload.expiresAt})',
      category: 'auth.offline',
    );
    return OfflineSessionStatus.offlineWithValidSession;
  }

  /// Returns `true` if the app should allow access in offline mode.
  ///
  /// Access is allowed when:
  /// - Device is online, OR
  /// - Device is offline but has a valid cached session
  Future<bool> shouldAllowAccess() async {
    final status = await validateSession();
    return status == OfflineSessionStatus.online ||
        status == OfflineSessionStatus.offlineWithValidSession;
  }
}

// ---------------------------------------------------------------------------
// Riverpod Providers
// ---------------------------------------------------------------------------

/// Provider for [OfflineSessionService].
final offlineSessionServiceProvider = Provider<OfflineSessionService>((ref) {
  final networkInfo = ref.watch(networkInfoProvider);
  final storage = ref.watch(secureStorageProvider);
  return OfflineSessionService(networkInfo: networkInfo, storage: storage);
});

/// Provider that streams the current network connectivity status.
///
/// Returns `true` when the device is online, `false` when offline.
final isOnlineProvider = StreamProvider<bool>((ref) {
  final service = ref.watch(offlineSessionServiceProvider);
  return service.onConnectivityChanged;
});

/// Provider that checks initial connectivity status.
final isOnlineNowProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(offlineSessionServiceProvider);
  return service.isOnline();
});

/// Provider for the current offline session status.
final offlineSessionStatusProvider =
    FutureProvider<OfflineSessionStatus>((ref) async {
  final service = ref.watch(offlineSessionServiceProvider);
  return service.validateSession();
});

/// Provider that returns `true` if app access should be allowed.
///
/// Use this to guard features that require authentication.
final shouldAllowAccessProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(offlineSessionServiceProvider);
  return service.shouldAllowAccess();
});
