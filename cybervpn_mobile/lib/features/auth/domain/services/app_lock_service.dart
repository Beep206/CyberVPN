import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart'
    show secureStorageProvider;

/// Service for managing app lock functionality.
///
/// When enabled, the app requires biometric authentication after
/// being in the background for more than [lockTimeoutSeconds].
class AppLockService with WidgetsBindingObserver {
  final SecureStorageWrapper _storage;
  final BiometricService _biometricService;

  /// Time in seconds after which the app should lock when resumed.
  static const int lockTimeoutSeconds = 30;

  DateTime? _pausedAt;
  bool _isLocked = false;
  int _failedAttempts = 0;

  /// Maximum biometric attempts before showing password fallback.
  static const int maxBiometricAttempts = 3;

  final _lockStateController = StreamController<bool>.broadcast();

  AppLockService({
    required SecureStorageWrapper storage,
    required BiometricService biometricService,
  })  : _storage = storage,
        _biometricService = biometricService {
    WidgetsBinding.instance.addObserver(this);
  }

  /// Stream of lock state changes.
  Stream<bool> get onLockStateChanged => _lockStateController.stream;

  /// Whether the app is currently locked.
  bool get isLocked => _isLocked;

  /// Number of failed biometric attempts.
  int get failedAttempts => _failedAttempts;

  /// Whether the user has exceeded max biometric attempts.
  bool get shouldShowPasswordFallback => _failedAttempts >= maxBiometricAttempts;

  /// Disposes the service and removes the lifecycle observer.
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _lockStateController.close();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.paused:
      case AppLifecycleState.inactive:
        _onAppPaused();
      case AppLifecycleState.resumed:
        _onAppResumed();
      case AppLifecycleState.detached:
      case AppLifecycleState.hidden:
        // Do nothing
        break;
    }
  }

  void _onAppPaused() {
    _pausedAt = DateTime.now();
    AppLogger.info(
      'App paused at $_pausedAt',
      category: 'auth.applock',
    );
  }

  Future<void> _onAppResumed() async {
    if (_pausedAt == null) return;

    final pauseDuration = DateTime.now().difference(_pausedAt!);
    _pausedAt = null;

    AppLogger.info(
      'App resumed after ${pauseDuration.inSeconds}s',
      category: 'auth.applock',
    );

    // Check if app lock is enabled
    final isEnabled = await _storage.isAppLockEnabled();
    if (!isEnabled) {
      AppLogger.info(
        'App lock not enabled, skipping lock check',
        category: 'auth.applock',
      );
      return;
    }

    // Check if pause duration exceeds threshold
    if (pauseDuration.inSeconds >= lockTimeoutSeconds) {
      AppLogger.info(
        'Lock threshold exceeded, locking app',
        category: 'auth.applock',
      );
      _lock();
    }
  }

  void _lock() {
    if (_isLocked) return;
    _isLocked = true;
    _failedAttempts = 0;
    _lockStateController.add(true);
    AppLogger.info('App locked', category: 'auth.applock');
  }

  /// Unlocks the app after successful authentication.
  void unlock() {
    if (!_isLocked) return;
    _isLocked = false;
    _failedAttempts = 0;
    _lockStateController.add(false);
    AppLogger.info('App unlocked', category: 'auth.applock');
  }

  /// Attempts to unlock the app using biometric authentication.
  ///
  /// Returns `true` if unlock was successful, `false` otherwise.
  Future<bool> attemptBiometricUnlock() async {
    try {
      final authenticated = await _biometricService.authenticate(
        reason: 'Unlock CyberVPN',
      );

      if (authenticated) {
        unlock();
        return true;
      }

      _failedAttempts++;
      AppLogger.info(
        'Biometric unlock failed, attempt $_failedAttempts/$maxBiometricAttempts',
        category: 'auth.applock',
      );
      return false;
    } catch (e, st) {
      AppLogger.error(
        'Biometric unlock error',
        error: e,
        stackTrace: st,
        category: 'auth.applock',
      );
      _failedAttempts++;
      return false;
    }
  }

  /// Resets failed attempts counter.
  void resetAttempts() {
    _failedAttempts = 0;
  }

  // ── Settings Management ────────────────────────────────────────────────────

  /// Checks if app lock is enabled.
  Future<bool> isAppLockEnabled() async {
    return _storage.isAppLockEnabled();
  }

  /// Sets whether app lock is enabled.
  Future<void> setAppLockEnabled(bool enabled) async {
    await _storage.setAppLockEnabled(enabled);
    AppLogger.info(
      'App lock ${enabled ? 'enabled' : 'disabled'}',
      category: 'auth.applock',
    );
  }

  /// Checks if app lock can be enabled (biometric must be available).
  Future<bool> canEnableAppLock() async {
    return _biometricService.isBiometricAvailable();
  }
}

// ---------------------------------------------------------------------------
// Riverpod Providers
// ---------------------------------------------------------------------------

/// Provider for [AppLockService].
///
/// This is a singleton service that tracks app lifecycle and manages lock state.
final appLockServiceProvider = Provider<AppLockService>((ref) {
  final storage = ref.watch(secureStorageProvider);
  final biometricService = ref.watch(biometricServiceProvider);

  final service = AppLockService(
    storage: storage,
    biometricService: biometricService,
  );

  ref.onDispose(service.dispose);

  return service;
});

/// Provider that streams the app lock state.
///
/// Returns `true` when the app is locked, `false` when unlocked.
final isAppLockedProvider = StreamProvider<bool>((ref) {
  final service = ref.watch(appLockServiceProvider);
  // Start with current state, then stream changes
  return Stream.value(service.isLocked)
      .asyncExpand((_) => service.onLockStateChanged);
});

/// Provider that checks if app lock is enabled in settings.
final isAppLockEnabledProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(appLockServiceProvider);
  return service.isAppLockEnabled();
});

/// Provider that checks if app lock can be enabled.
final canEnableAppLockProvider = FutureProvider<bool>((ref) async {
  final service = ref.watch(appLockServiceProvider);
  return service.canEnableAppLock();
});
