import 'package:flutter/services.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// iOS-specific VPN notification manager.
///
/// iOS NetworkExtension automatically manages the VPN status bar icon, so this
/// class provides optional local notifications for connection events only.
///
/// Local notifications:
/// - Connect: "Connected to [Server Name]" (auto-dismiss after 3 seconds)
/// - Disconnect: "VPN Disconnected" (auto-dismiss after 3 seconds)
///
/// These notifications respect system notification permission status and can
/// be enabled/disabled via user preferences (task 34).
class VpnNotificationIos {
  static const MethodChannel _channel = MethodChannel('com.cybervpn/vpn_notification');

  /// Shows a local notification when VPN connects.
  ///
  /// Displays: "Connected to [serverName]"
  /// Auto-dismisses after 3 seconds or on user tap.
  Future<void> showConnectedNotification({
    required String serverName,
    String? protocol,
  }) async {
    try {
      await _channel.invokeMethod('showConnectedLocal', {
        'title': 'VPN Connected',
        'body': 'Connected to $serverName',
        'serverName': serverName,
        'protocol': protocol ?? '',
      });

      AppLogger.info('iOS VPN connected notification shown: $serverName');
    } on PlatformException catch (e) {
      AppLogger.error('Failed to show iOS connected notification', error: e);
    } on MissingPluginException catch (e) {
      // Method not implemented on iOS platform channel yet
      AppLogger.warning(
        'iOS notification platform method not implemented',
        error: e,
      );
    }
  }

  /// Shows a local notification when VPN disconnects.
  ///
  /// Displays: "VPN Disconnected"
  /// Auto-dismisses after 3 seconds or on user tap.
  Future<void> showDisconnectedNotification() async {
    try {
      await _channel.invokeMethod('showDisconnectedLocal', {
        'title': 'VPN Disconnected',
        'body': 'Your VPN connection has ended',
      });

      AppLogger.info('iOS VPN disconnected notification shown');
    } on PlatformException catch (e) {
      AppLogger.error('Failed to show iOS disconnected notification', error: e);
    } on MissingPluginException catch (e) {
      // Method not implemented on iOS platform channel yet
      AppLogger.warning(
        'iOS notification platform method not implemented',
        error: e,
      );
    }
  }

  /// Logs connection status for debugging.
  ///
  /// This is a fallback when local notifications are disabled or fail.
  void logConnectionStatus({required bool isConnected, String? serverName}) {
    if (isConnected) {
      AppLogger.info(
        'iOS VPN connected: status bar indicator active. Server: $serverName',
      );
    } else {
      AppLogger.info('iOS VPN disconnected: status bar indicator removed');
    }
  }

  /// Requests notification permissions from the user.
  ///
  /// Should be called on app launch or when the user first enables VPN
  /// connection notifications in settings.
  Future<bool> requestPermissions() async {
    try {
      final result = await _channel.invokeMethod<bool>('requestNotificationPermissions');
      return result ?? false;
    } on PlatformException catch (e) {
      AppLogger.error('Failed to request iOS notification permissions', error: e);
      return false;
    } on MissingPluginException catch (e) {
      AppLogger.warning(
        'iOS notification permissions method not implemented',
        error: e,
      );
      return false;
    }
  }

  /// Checks current notification permission status.
  ///
  /// Returns true if notifications are authorized, false otherwise.
  Future<bool> checkPermissions() async {
    try {
      final result = await _channel.invokeMethod<bool>('checkNotificationPermissions');
      return result ?? false;
    } on PlatformException catch (e) {
      AppLogger.error('Failed to check iOS notification permissions', error: e);
      return false;
    } on MissingPluginException catch (e) {
      AppLogger.warning(
        'iOS notification permissions check not implemented',
        error: e,
      );
      return false;
    }
  }
}
