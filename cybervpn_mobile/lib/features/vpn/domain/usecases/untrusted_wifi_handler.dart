import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/network/wifi_monitor_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

// ---------------------------------------------------------------------------
// Untrusted WiFi Handler
// ---------------------------------------------------------------------------

/// Service that monitors WiFi changes and auto-connects VPN when joining
/// untrusted networks.
///
/// This service:
/// 1. Monitors WiFi connection changes via [WifiMonitorService]
/// 2. Checks if the connected network SSID is in the trusted list
/// 3. If not trusted and `autoConnectUntrustedWifi` is enabled, connects VPN
///
/// The handler respects:
/// - User's auto-connect preference from settings
/// - Trusted WiFi list (networks that won't trigger auto-connect)
/// - Current VPN state (doesn't connect if already connected)
/// - Permission status (gracefully handles missing location permission)
///
/// Usage:
/// ```dart
/// // Start monitoring when app initializes
/// ref.read(untrustedWifiHandlerProvider).start();
///
/// // Stop when cleaning up
/// ref.read(untrustedWifiHandlerProvider).stop();
/// ```
class UntrustedWifiHandler {
  UntrustedWifiHandler({
    required this.ref,
  });

  final Ref ref;

  StreamSubscription<WifiInfo>? _wifiSubscription;
  bool _isProcessing = false;
  DateTime? _lastAutoConnectAttempt;

  // Debounce duration to prevent rapid reconnection attempts
  static const _debounceInterval = Duration(seconds: 5);

  /// Whether the handler is currently monitoring WiFi changes.
  bool get isMonitoring => _wifiSubscription != null;

  /// Start monitoring WiFi changes for auto-connect.
  ///
  /// Call this when the app initializes or when the user enables
  /// auto-connect on untrusted WiFi.
  void start() {
    if (isMonitoring) {
      AppLogger.debug(
        'Untrusted WiFi handler already monitoring',
        category: 'vpn.wifi',
      );
      return;
    }

    final wifiService = ref.read(wifiMonitorServiceProvider);

    // Start the WiFi monitoring service
    wifiService.startMonitoring();

    // Subscribe to WiFi changes
    _wifiSubscription = wifiService.onWifiChanged.listen(
      _onWifiChanged,
      onError: (Object e) {
        AppLogger.error(
          'Error in WiFi monitoring stream',
          error: e,
          category: 'vpn.wifi',
        );
      },
    );

    AppLogger.info(
      'Untrusted WiFi handler started',
      category: 'vpn.wifi',
    );

    // Check current WiFi state immediately
    _checkCurrentWifi();
  }

  /// Stop monitoring WiFi changes.
  ///
  /// Call this when cleaning up or when the user disables auto-connect.
  void stop() {
    _wifiSubscription?.cancel();
    _wifiSubscription = null;

    // Also stop the underlying WiFi service if we were the only user
    ref.read(wifiMonitorServiceProvider).stopMonitoring();

    AppLogger.info(
      'Untrusted WiFi handler stopped',
      category: 'vpn.wifi',
    );
  }

  /// Check current WiFi and auto-connect if needed.
  Future<void> _checkCurrentWifi() async {
    final wifiService = ref.read(wifiMonitorServiceProvider);
    final wifiInfo = await wifiService.getCurrentWifiInfo();
    await _onWifiChanged(wifiInfo);
  }

  /// Handle WiFi changes and trigger auto-connect when appropriate.
  Future<void> _onWifiChanged(WifiInfo wifiInfo) async {
    // Prevent concurrent processing
    if (_isProcessing) return;
    _isProcessing = true;

    try {
      await _processWifiChange(wifiInfo);
    } finally {
      _isProcessing = false;
    }
  }

  Future<void> _processWifiChange(WifiInfo wifiInfo) async {
    // Not connected to WiFi - nothing to do
    if (!wifiInfo.isConnectedToWifi) {
      AppLogger.debug(
        'Not connected to WiFi, skipping auto-connect check',
        category: 'vpn.wifi',
      );
      return;
    }

    // Check if auto-connect on untrusted WiFi is enabled
    final vpnSettings = ref.read(vpnSettingsProvider);
    if (!vpnSettings.autoConnectUntrustedWifi) {
      AppLogger.debug(
        'Auto-connect on untrusted WiFi disabled, skipping',
        category: 'vpn.wifi',
      );
      return;
    }

    // Check if we have valid SSID info
    if (!wifiInfo.hasValidSsid) {
      AppLogger.debug(
        'SSID unavailable (permission denied?), skipping auto-connect',
        category: 'vpn.wifi',
      );
      return;
    }

    final ssid = wifiInfo.cleanSsid!;

    // Check if this network is trusted
    if (vpnSettings.isTrusted(ssid)) {
      AppLogger.debug(
        'Connected to trusted network "$ssid", skipping auto-connect',
        category: 'vpn.wifi',
      );
      return;
    }

    // Check if VPN is already connected
    final vpnState = ref.read(vpnConnectionProvider).value;
    if (vpnState?.isConnected == true || vpnState?.isConnecting == true) {
      AppLogger.debug(
        'VPN already connected/connecting, skipping auto-connect',
        category: 'vpn.wifi',
      );
      return;
    }

    // Debounce check - don't auto-connect too frequently
    final now = DateTime.now();
    if (_lastAutoConnectAttempt != null &&
        now.difference(_lastAutoConnectAttempt!) < _debounceInterval) {
      AppLogger.debug(
        'Auto-connect debounced, skipping',
        category: 'vpn.wifi',
      );
      return;
    }

    // All checks passed - trigger auto-connect
    _lastAutoConnectAttempt = now;

    AppLogger.info(
      'Detected untrusted WiFi "$ssid", triggering auto-connect',
      category: 'vpn.wifi',
    );

    try {
      // Connect to the last used server or the recommended server
      await ref.read(vpnConnectionProvider.notifier).connectToLastOrRecommended();

      AppLogger.info(
        'Auto-connected VPN due to untrusted WiFi "$ssid"',
        category: 'vpn.wifi',
      );
    } catch (e) {
      AppLogger.error(
        'Failed to auto-connect VPN on untrusted WiFi',
        error: e,
        category: 'vpn.wifi',
      );
    }
  }

  /// Dispose resources.
  void dispose() {
    stop();
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provides the [UntrustedWifiHandler] instance.
///
/// The handler auto-starts/stops based on the autoConnectUntrustedWifi setting.
final untrustedWifiHandlerProvider = Provider<UntrustedWifiHandler>((ref) {
  final handler = UntrustedWifiHandler(ref: ref);

  // Watch the auto-connect setting and start/stop monitoring accordingly
  final shouldMonitor = ref.watch(
    settingsProvider.select(
      (state) => state.value?.autoConnectUntrustedWifi ?? false,
    ),
  );

  if (shouldMonitor) {
    handler.start();
  } else {
    handler.stop();
  }

  ref.onDispose(handler.dispose);

  return handler;
});

/// State for untrusted WiFi auto-connect.
class UntrustedWifiState {
  const UntrustedWifiState({
    this.isAutoConnecting = false,
    this.triggeringSsid,
  });

  /// Whether we're currently auto-connecting due to untrusted WiFi.
  final bool isAutoConnecting;

  /// The SSID that triggered the auto-connect.
  final String? triggeringSsid;

  UntrustedWifiState copyWith({
    bool? isAutoConnecting,
    String? triggeringSsid,
  }) {
    return UntrustedWifiState(
      isAutoConnecting: isAutoConnecting ?? this.isAutoConnecting,
      triggeringSsid: triggeringSsid ?? this.triggeringSsid,
    );
  }
}

/// Notifier for tracking untrusted WiFi auto-connect status.
///
/// Can be used to show UI indicators when auto-connecting.
class UntrustedWifiStateNotifier extends Notifier<UntrustedWifiState> {
  @override
  UntrustedWifiState build() => const UntrustedWifiState();

  void setAutoConnecting(String ssid) {
    state = UntrustedWifiState(
      isAutoConnecting: true,
      triggeringSsid: ssid,
    );
  }

  void clearAutoConnecting() {
    state = const UntrustedWifiState();
  }
}

final untrustedWifiStateProvider =
    NotifierProvider<UntrustedWifiStateNotifier, UntrustedWifiState>(
  UntrustedWifiStateNotifier.new,
);
