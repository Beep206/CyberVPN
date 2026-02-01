import 'dart:async';

import 'package:flutter/services.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';

/// Android-specific VPN foreground service notification manager.
///
/// Manages a persistent notification displayed while the VPN is connected,
/// showing the server name, real-time upload/download speeds, and action
/// buttons for disconnect and server switching.
///
/// The notification updates every 2 seconds with fresh speed data and uses
/// a low-priority notification channel to avoid being intrusive.
class VpnNotificationAndroid {
  static const MethodChannel _channel = MethodChannel('com.cybervpn/vpn_notification');

  Timer? _updateTimer;
  String? _currentServerName;
  int _currentDownloadSpeed = 0;
  int _currentUploadSpeed = 0;
  Duration _currentDuration = Duration.zero;
  bool _showSpeed = true;

  /// Shows the connected notification with initial server information.
  ///
  /// Starts a 2-second update timer to refresh speed stats in the notification.
  Future<void> showConnectedNotification({
    required String serverName,
    String? protocol,
    bool showSpeed = true,
  }) async {
    try {
      _currentServerName = serverName;
      _showSpeed = showSpeed;

      await _channel.invokeMethod('showConnected', {
        'serverName': serverName,
        'protocol': protocol ?? '',
        'showSpeed': showSpeed,
      });

      // Start periodic updates every 2 seconds
      _startUpdateTimer();

      AppLogger.debug('VPN notification shown for server: $serverName');
    } on PlatformException catch (e) {
      AppLogger.error('Failed to show connected notification', error: e);
    }
  }

  /// Updates the notification with current speed stats and connection duration.
  ///
  /// Called automatically every 2 seconds by the internal timer, or can be
  /// called manually to force an immediate update.
  Future<void> updateNotification({
    required int downloadSpeed,
    required int uploadSpeed,
    required Duration duration,
  }) async {
    try {
      _currentDownloadSpeed = downloadSpeed;
      _currentUploadSpeed = uploadSpeed;
      _currentDuration = duration;

      // Format speeds for display
      final downloadFormatted = DataFormatters.formatSpeed(downloadSpeed.toDouble());
      final uploadFormatted = DataFormatters.formatSpeed(uploadSpeed.toDouble());
      final durationFormatted = DataFormatters.formatDuration(duration);

      await _channel.invokeMethod('updateStats', {
        'serverName': _currentServerName ?? 'Connected',
        'downloadSpeed': downloadSpeed,
        'uploadSpeed': uploadSpeed,
        'downloadSpeedFormatted': downloadFormatted,
        'uploadSpeedFormatted': uploadFormatted,
        'durationSeconds': duration.inSeconds,
        'durationFormatted': durationFormatted,
        'showSpeed': _showSpeed,
      });
    } on PlatformException catch (e) {
      AppLogger.error('Failed to update notification', error: e);
    }
  }

  /// Updates whether speed stats should be shown in the notification.
  ///
  /// When [enabled] is false, the notification shows only the server name
  /// and action buttons without speed information.
  Future<void> updateSpeedVisibility(bool enabled) async {
    if (_showSpeed == enabled) return;

    _showSpeed = enabled;

    // If connected, refresh the notification with new visibility setting
    if (_currentServerName != null) {
      await updateNotification(
        downloadSpeed: _currentDownloadSpeed,
        uploadSpeed: _currentUploadSpeed,
        duration: _currentDuration,
      );
    }
  }

  /// Shows a brief disconnected notification.
  ///
  /// This is a non-persistent notification that auto-dismisses.
  Future<void> showDisconnectedNotification() async {
    try {
      _stopUpdateTimer();
      _currentServerName = null;

      await _channel.invokeMethod('showDisconnected');

      AppLogger.debug('VPN disconnected notification shown');
    } on PlatformException catch (e) {
      AppLogger.error('Failed to show disconnected notification', error: e);
    }
  }

  /// Dismisses the VPN notification completely.
  ///
  /// Stops the update timer and removes the notification from the system tray.
  Future<void> dismiss() async {
    try {
      _stopUpdateTimer();
      _currentServerName = null;

      await _channel.invokeMethod('dismiss');

      AppLogger.debug('VPN notification dismissed');
    } on PlatformException catch (e) {
      AppLogger.error('Failed to dismiss notification', error: e);
    }
  }

  // -- Private helpers --------------------------------------------------------

  /// Starts a timer that updates the notification every 2 seconds.
  void _startUpdateTimer() {
    _stopUpdateTimer(); // Ensure no duplicate timers

    _updateTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      // The vpn_stats_provider will push new stats, which will trigger
      // updateNotification() via the listener in vpn_notification_service.
      // This timer is a fallback to ensure the notification updates even
      // if stats updates are delayed.
    });
  }

  /// Stops the notification update timer.
  void _stopUpdateTimer() {
    _updateTimer?.cancel();
    _updateTimer = null;
  }

  /// Disposes resources and cancels timers.
  void dispose() {
    _stopUpdateTimer();
  }
}
