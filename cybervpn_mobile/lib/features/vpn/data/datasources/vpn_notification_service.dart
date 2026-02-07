import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_notification_android.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_notification_ios.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';

/// Cross-platform VPN notification service.
///
/// Manages persistent notifications for VPN connections:
/// - Android: Foreground service notification with speed stats and actions
/// - iOS: Optional local notifications for connect/disconnect events
///
/// Automatically listens to VPN connection state and stats updates to
/// keep the notification synchronized with the current VPN status.
class VpnNotificationService {
  VpnNotificationService({
    required Ref ref,
  }) : _ref = ref {
    _initialize();
  }

  final Ref _ref;
  final VpnNotificationAndroid _androidNotification = VpnNotificationAndroid();
  final VpnNotificationIos _iosNotification = VpnNotificationIos();

  ProviderSubscription<AsyncValue<VpnConnectionState>>? _connectionSubscription;
  ProviderSubscription<ConnectionStatsEntity?>? _statsSubscription;

  bool _isAndroid = false;
  bool _isIOS = false;

  // -- Initialization ---------------------------------------------------------

  void _initialize() {
    try {
      _isAndroid = Platform.isAndroid;
      _isIOS = Platform.isIOS;
    } catch (e) {
      // Platform check may fail in test environment
      _isAndroid = false;
      _isIOS = false;
    }

    if (!_isAndroid && !_isIOS) {
      AppLogger.debug('VPN notification service: unsupported platform');
      return;
    }

    _listenToConnectionState();
    _listenToStats();
    _listenToSettings();

    AppLogger.info('VPN notification service initialized');
  }

  // -- Listeners --------------------------------------------------------------

  /// Listens to VPN connection state changes to show/hide notifications.
  void _listenToConnectionState() {
    _connectionSubscription = _ref.listen<AsyncValue<VpnConnectionState>>(
      vpnConnectionProvider,
      (previous, next) {
        final state = next.value;
        if (state == null) return;

        _handleConnectionStateChange(state);
      },
      fireImmediately: true,
    );
  }

  /// Listens to VPN stats updates to refresh notification content.
  void _listenToStats() {
    if (!_isAndroid) return; // Stats only shown on Android

    _statsSubscription = _ref.listen<ConnectionStatsEntity?>(
      vpnStatsProvider,
      (previous, next) {
        if (next == null) return;

        _handleStatsUpdate(next);
      },
      fireImmediately: false,
    );
  }

  /// Listens to notification settings changes to update visibility.
  void _listenToSettings() {
    if (!_isAndroid) return; // Speed toggle only on Android

    _ref.listen(settingsProvider, (previous, next) {
      final settings = next.value;
      if (settings == null) return;

      unawaited(_androidNotification.updateSpeedVisibility(settings.notificationVpnSpeed));
    });
  }

  // -- State handlers ---------------------------------------------------------

  void _handleConnectionStateChange(VpnConnectionState state) {
    switch (state) {
      case VpnConnected(:final server, :final protocol):
        unawaited(_onConnected(server.name, protocol.name));
      case VpnDisconnected():
        unawaited(_onDisconnected());
      case VpnDisconnecting():
        unawaited(_onDisconnecting());
      default:
        // No notification changes for connecting/reconnecting states
        break;
    }
  }

  void _handleStatsUpdate(ConnectionStatsEntity stats) {
    if (!_isAndroid) return;

    unawaited(_androidNotification.updateNotification(
      downloadSpeed: stats.downloadSpeed,
      uploadSpeed: stats.uploadSpeed,
      duration: stats.connectionDuration,
    ));
  }

  // -- Connection event handlers ----------------------------------------------

  Future<void> _onConnected(String serverName, String protocol) async {
    if (_isAndroid) {
      final settings = _ref.read(settingsProvider).value;
      final showSpeed = settings?.notificationVpnSpeed ?? false;

      await _androidNotification.showConnectedNotification(
        serverName: serverName,
        protocol: protocol,
        showSpeed: showSpeed,
      );
    }

    if (_isIOS) {
      // Check if connection notifications are enabled in settings
      final settings = _ref.read(settingsProvider).value;
      final notificationsEnabled = settings?.notificationConnection ?? true;

      if (notificationsEnabled) {
        await _iosNotification.showConnectedNotification(
          serverName: serverName,
          protocol: protocol,
        );
      }

      _iosNotification.logConnectionStatus(
        isConnected: true,
        serverName: serverName,
      );
    }
  }

  Future<void> _onDisconnecting() async {
    if (_isAndroid) {
      // Keep notification visible during disconnection
      // Will be removed in _onDisconnected
    }
  }

  Future<void> _onDisconnected() async {
    if (_isAndroid) {
      await _androidNotification.showDisconnectedNotification();
      // Dismiss after a brief delay
      Future.delayed(const Duration(seconds: 3), _androidNotification.dismiss);
    }

    if (_isIOS) {
      // Check if connection notifications are enabled in settings
      final settings = _ref.read(settingsProvider).value;
      final notificationsEnabled = settings?.notificationConnection ?? true;

      if (notificationsEnabled) {
        await _iosNotification.showDisconnectedNotification();
      }

      _iosNotification.logConnectionStatus(
        isConnected: false,
        serverName: null,
      );
    }
  }

  // -- Cleanup ----------------------------------------------------------------

  void dispose() {
    _connectionSubscription?.cancel();
    _statsSubscription?.cancel();
    _androidNotification.dispose();

    AppLogger.debug('VPN notification service disposed');
  }
}

// -- Provider ----------------------------------------------------------------

final vpnNotificationServiceProvider = Provider<VpnNotificationService>((ref) {
  final service = VpnNotificationService(ref: ref);
  ref.onDispose(service.dispose);
  return service;
});
