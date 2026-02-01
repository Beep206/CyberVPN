import 'package:flutter_jailbreak_detection/flutter_jailbreak_detection.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Manages device integrity checks for root/jailbreak detection.
///
/// This service wraps [FlutterJailbreakDetection] functionality and provides
/// methods to:
/// - Check if the device is rooted/jailbroken
/// - Store and retrieve user's warning dismissal preference
///
/// The service is designed to be non-blocking - it only warns users about
/// rooted/jailbroken devices but does NOT prevent app usage. This is important
/// for VPN users in censored regions who may rely on rooted devices.
class DeviceIntegrityChecker {
  /// SharedPreferences key for storing the user's dismissal preference.
  static const String _dismissalKey = 'device_rooted_warning_dismissed';

  final SharedPreferences _prefs;

  DeviceIntegrityChecker(this._prefs);

  /// Checks if the current device is rooted (Android) or jailbroken (iOS).
  ///
  /// Returns `true` if the device is rooted/jailbroken, `false` otherwise.
  /// In case of platform-specific errors or unsupported platforms, returns
  /// `false` and logs the error.
  Future<bool> isDeviceRooted() async {
    try {
      final jailbroken = await FlutterJailbreakDetection.jailbroken;
      if (jailbroken) {
        AppLogger.warning(
          'Device root/jailbreak detected',
          category: 'security',
        );
      }
      return jailbroken;
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to check device integrity',
        error: e,
        stackTrace: stackTrace,
        category: 'security',
      );
      // Fail safely - assume device is not rooted if check fails
      return false;
    }
  }

  /// Checks if the user has previously dismissed the root/jailbreak warning.
  ///
  /// Returns `true` if the warning has been dismissed, `false` otherwise.
  Future<bool> hasUserDismissedWarning() async {
    try {
      return _prefs.getBool(_dismissalKey) ?? false;
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to read warning dismissal preference',
        error: e,
        stackTrace: stackTrace,
        category: 'security',
      );
      return false;
    }
  }

  /// Marks the root/jailbreak warning as dismissed by the user.
  ///
  /// Stores the dismissal preference in [SharedPreferences] so the warning
  /// won't be shown again on subsequent app launches.
  Future<void> dismissWarning() async {
    try {
      await _prefs.setBool(_dismissalKey, true);
      AppLogger.info(
        'User dismissed root/jailbreak warning',
        category: 'security',
      );
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to save warning dismissal preference',
        error: e,
        stackTrace: stackTrace,
        category: 'security',
      );
    }
  }

  /// Resets the dismissal preference (useful for testing).
  Future<void> resetDismissal() async {
    try {
      await _prefs.remove(_dismissalKey);
      AppLogger.info(
        'Reset root/jailbreak warning dismissal',
        category: 'security',
      );
    } catch (e, stackTrace) {
      AppLogger.error(
        'Failed to reset warning dismissal preference',
        error: e,
        stackTrace: stackTrace,
        category: 'security',
      );
    }
  }
}
