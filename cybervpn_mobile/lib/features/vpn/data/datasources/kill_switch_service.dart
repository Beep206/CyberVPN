import 'dart:async';
import 'dart:io' show Platform;

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_android.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_ios.dart';

/// Platform-agnostic kill switch interface with periodic health checks.
///
/// Delegates to [KillSwitchAndroid] or [KillSwitchIos] based on the current
/// platform. On unsupported platforms the calls are silently no-ops.
///
/// When the VPN is connected, periodic health checks verify the kill switch
/// remains active and re-enable it if it was unexpectedly disabled.
class KillSwitchService {
  KillSwitchService()
      : _android = Platform.isAndroid ? KillSwitchAndroid() : null,
        _ios = Platform.isIOS ? KillSwitchIos() : null;

  final KillSwitchAndroid? _android;
  final KillSwitchIos? _ios;

  Timer? _healthCheckTimer;

  /// Interval between kill switch health checks.
  static const Duration healthCheckInterval = Duration(minutes: 2);

  Future<void> enable() async {
    try {
      if (_android != null) {
        await _android.enable();
      } else if (_ios != null) {
        await _ios.enable();
      } else {
        AppLogger.warning('Kill switch not supported on this platform');
      }
    } catch (e, st) {
      AppLogger.error('Failed to enable kill switch', error: e, stackTrace: st);
    }
  }

  Future<void> disable() async {
    try {
      if (_android != null) {
        await _android.disable();
      } else if (_ios != null) {
        await _ios.disable();
      } else {
        AppLogger.warning('Kill switch not supported on this platform');
      }
    } catch (e, st) {
      AppLogger.error(
        'Failed to disable kill switch',
        error: e,
        stackTrace: st,
      );
    }
  }

  Future<bool> isEnabled() async {
    try {
      if (_android != null) return await _android.isEnabled();
      if (_ios != null) return await _ios.isEnabled();
      return false;
    } catch (e) {
      AppLogger.warning('Kill switch status check failed', error: e, category: 'vpn');
      return false;
    }
  }

  /// Starts periodic health checks that verify the kill switch is still active.
  ///
  /// If the kill switch is found to be disabled during a connected VPN session,
  /// it will be automatically re-enabled and a warning logged.
  void startHealthChecks() {
    stopHealthChecks();
    _healthCheckTimer = Timer.periodic(healthCheckInterval, (_) async {
      try {
        final enabled = await isEnabled();
        if (!enabled) {
          AppLogger.warning(
            'Kill switch was unexpectedly disabled, re-enabling',
            category: 'vpn.killswitch',
          );
          await enable();
        }
      } catch (e) {
        AppLogger.error(
          'Kill switch health check failed',
          error: e,
          category: 'vpn.killswitch',
        );
      }
    });
    AppLogger.info('Kill switch health checks started', category: 'vpn.killswitch');
  }

  /// Stops periodic health checks.
  void stopHealthChecks() {
    _healthCheckTimer?.cancel();
    _healthCheckTimer = null;
  }

  /// Disposes the service and stops health checks.
  void dispose() {
    stopHealthChecks();
  }
}
