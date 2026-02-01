import 'dart:io' show Platform;

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_android.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_ios.dart';

/// Platform-agnostic kill switch interface.
///
/// Delegates to [KillSwitchAndroid] or [KillSwitchIos] based on the current
/// platform. On unsupported platforms the calls are silently no-ops.
class KillSwitchService {
  KillSwitchService()
      : _android = Platform.isAndroid ? KillSwitchAndroid() : null,
        _ios = Platform.isIOS ? KillSwitchIos() : null;

  final KillSwitchAndroid? _android;
  final KillSwitchIos? _ios;

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
    } catch (_) {
      return false;
    }
  }
}
