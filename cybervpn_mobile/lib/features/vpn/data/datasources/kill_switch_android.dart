import 'package:flutter/services.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class KillSwitchAndroid {
  static const MethodChannel _channel = MethodChannel('com.cybervpn/kill_switch');

  Future<void> enable() async {
    try {
      await _channel.invokeMethod('enableKillSwitch');
      AppLogger.info('Kill switch enabled on Android');
    } on PlatformException catch (e) {
      AppLogger.error('Failed to enable kill switch', error: e);
      rethrow;
    }
  }

  Future<void> disable() async {
    try {
      await _channel.invokeMethod('disableKillSwitch');
      AppLogger.info('Kill switch disabled on Android');
    } on PlatformException catch (e) {
      AppLogger.error('Failed to disable kill switch', error: e);
      rethrow;
    }
  }

  Future<bool> isEnabled() async {
    try {
      final result = await _channel.invokeMethod<bool>('isKillSwitchEnabled');
      return result ?? false;
    } on PlatformException {
      return false;
    }
  }
}
