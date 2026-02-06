import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/auth/token_refresh_scheduler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/domain/services/offline_session_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart'
    show networkInfoProvider;

/// Result of a sync operation.
enum SyncResult {
  /// Sync completed successfully.
  success,

  /// No sync needed (already online or no cached session).
  notNeeded,

  /// Sync failed but can retry.
  failed,

  /// Session expired, user needs to re-authenticate.
  sessionExpired,
}

/// Service that automatically syncs data when network connectivity is restored.
///
/// This service:
/// - Listens for connectivity state changes
/// - Triggers token refresh when reconnecting
/// - Fetches fresh user profile data
/// - Updates cached data
class SyncOnReconnectService {
  final NetworkInfo _networkInfo;
  final OfflineSessionService _offlineSessionService;
  final TokenRefreshScheduler _tokenRefreshScheduler;
  final AuthRepository _authRepository;
  final Ref _ref;

  StreamSubscription<bool>? _connectivitySubscription;
  bool _wasOffline = false;
  bool _isSyncing = false;

  final _syncResultController = StreamController<SyncResult>.broadcast();

  SyncOnReconnectService({
    required NetworkInfo networkInfo,
    required OfflineSessionService offlineSessionService,
    required TokenRefreshScheduler tokenRefreshScheduler,
    required AuthRepository authRepository,
    required Ref ref,
  })  : _networkInfo = networkInfo,
        _offlineSessionService = offlineSessionService,
        _tokenRefreshScheduler = tokenRefreshScheduler,
        _authRepository = authRepository,
        _ref = ref {
    _startListening();
  }

  /// Stream of sync results.
  Stream<SyncResult> get onSyncResult => _syncResultController.stream;

  /// Whether a sync is currently in progress.
  bool get isSyncing => _isSyncing;

  void _startListening() {
    _connectivitySubscription = _networkInfo.onConnectivityChanged.listen(
      _onConnectivityChanged,
    );

    // Check initial state
    unawaited(Future(() async {
      final isOnline = await _networkInfo.isConnected;
      _wasOffline = !isOnline;
    }));
  }

  Future<void> _onConnectivityChanged(bool isOnline) async {
    if (isOnline && _wasOffline) {
      AppLogger.info(
        'Connectivity restored, triggering sync',
        category: 'auth.sync',
      );
      await _syncOnReconnect();
    }
    _wasOffline = !isOnline;
  }

  /// Manually trigger a sync operation.
  Future<SyncResult> syncNow() async {
    if (_isSyncing) {
      AppLogger.info('Sync already in progress', category: 'auth.sync');
      return SyncResult.notNeeded;
    }
    return _syncOnReconnect();
  }

  Future<SyncResult> _syncOnReconnect() async {
    _isSyncing = true;

    try {
      // Check if we have a valid session
      final sessionStatus = await _offlineSessionService.validateSession();

      if (sessionStatus == OfflineSessionStatus.offlineNoSession) {
        AppLogger.info(
          'No session to sync',
          category: 'auth.sync',
        );
        _isSyncing = false;
        final result = SyncResult.notNeeded;
        _syncResultController.add(result);
        return result;
      }

      if (sessionStatus == OfflineSessionStatus.offlineWithExpiredSession) {
        AppLogger.info(
          'Session expired, user needs to re-authenticate',
          category: 'auth.sync',
        );
        _isSyncing = false;
        final result = SyncResult.sessionExpired;
        _syncResultController.add(result);
        return result;
      }

      // Schedule token refresh (will trigger immediately if expired)
      AppLogger.info('Scheduling token refresh...', category: 'auth.sync');
      try {
        await _tokenRefreshScheduler.scheduleRefresh();
        AppLogger.info('Token refresh scheduled', category: 'auth.sync');
      } catch (e) {
        AppLogger.warning(
          'Token refresh scheduling failed: $e',
          category: 'auth.sync',
        );
        // Non-fatal - continue with sync
      }

      // Fetch fresh user profile
      AppLogger.info('Fetching fresh user profile...', category: 'auth.sync');
      try {
        final userResult = await _authRepository.getCurrentUser();
        final user = userResult.dataOrNull;
        if (user != null) {
          AppLogger.info(
            'User profile synced: ${user.email}',
            category: 'auth.sync',
          );
        }
      } catch (e) {
        AppLogger.warning(
          'Failed to fetch user profile: $e',
          category: 'auth.sync',
        );
        // Non-fatal - continue
      }

      // Trigger auth state refresh
      unawaited(_ref.read(authProvider.notifier).checkAuthStatus());

      _isSyncing = false;
      AppLogger.info('Sync completed successfully', category: 'auth.sync');
      final result = SyncResult.success;
      _syncResultController.add(result);
      return result;
    } catch (e, st) {
      AppLogger.error(
        'Sync failed',
        error: e,
        stackTrace: st,
        category: 'auth.sync',
      );
      _isSyncing = false;
      final result = SyncResult.failed;
      _syncResultController.add(result);
      return result;
    }
  }

  /// Stops listening for connectivity changes.
  void dispose() {
    unawaited(_connectivitySubscription?.cancel());
    unawaited(_syncResultController.close());
  }
}

// ---------------------------------------------------------------------------
// Riverpod Providers
// ---------------------------------------------------------------------------

/// Provider for [SyncOnReconnectService].
final syncOnReconnectServiceProvider = Provider<SyncOnReconnectService>((ref) {
  final networkInfo = ref.watch(networkInfoProvider);
  final offlineSessionService = ref.watch(offlineSessionServiceProvider);
  final tokenRefreshScheduler = ref.watch(tokenRefreshSchedulerProvider);
  final authRepository = ref.watch(authRepositoryProvider);

  final service = SyncOnReconnectService(
    networkInfo: networkInfo,
    offlineSessionService: offlineSessionService,
    tokenRefreshScheduler: tokenRefreshScheduler,
    authRepository: authRepository,
    ref: ref,
  );

  ref.onDispose(service.dispose);

  return service;
});

/// Provider that streams sync results.
final syncResultProvider = StreamProvider<SyncResult>((ref) {
  final service = ref.watch(syncOnReconnectServiceProvider);
  return service.onSyncResult;
});

/// Provider that indicates if sync is in progress.
final isSyncingProvider = Provider<bool>((ref) {
  final service = ref.watch(syncOnReconnectServiceProvider);
  return service.isSyncing;
});
