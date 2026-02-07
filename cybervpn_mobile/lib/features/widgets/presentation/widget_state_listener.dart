import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:async';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/widgets/data/widget_bridge_service.dart';

/// Listens to VPN connection state changes and updates native home screen widgets.
///
/// This provider watches [vpnConnectionProvider] and [vpnStatsProvider] to sync
/// VPN status, server name, and traffic stats to the widget layer.
final widgetStateListenerProvider = Provider<WidgetStateListener>((ref) {
  return WidgetStateListener(
    ref: ref,
    bridgeService: ref.watch(widgetBridgeServiceProvider),
  );
});

/// Manages synchronization between VPN state and native widgets.
class WidgetStateListener {
  final Ref ref;
  final WidgetBridgeService bridgeService;

  WidgetStateListener({
    required this.ref,
    required this.bridgeService,
  }) {
    _initialize();
  }

  void _initialize() {
    // Listen to VPN connection state changes
    ref.listen<AsyncValue<VpnConnectionState>>(
      vpnConnectionProvider,
      (AsyncValue<VpnConnectionState>? previous, AsyncValue<VpnConnectionState> next) {
        next.whenData(_updateWidgetFromConnectionState);
      },
    );

    // Listen to VPN stats changes
    ref.listen<ConnectionStatsEntity?>(
      vpnStatsProvider,
      (ConnectionStatsEntity? previous, ConnectionStatsEntity? next) {
        if (next != null) {
          _updateWidgetFromStats(next);
        }
      },
    );
  }

  /// Updates widget state based on VPN connection state.
  void _updateWidgetFromConnectionState(VpnConnectionState connectionState) {
    try {
      final vpnStatus = _mapConnectionStateToStatus(connectionState);
      final serverName = connectionState.server?.name ?? '';

      // Get current stats if available
      final statsState = ref.read(vpnStatsProvider);
      final uploadSpeed = statsState?.uploadSpeed.toDouble() ?? 0.0;
      final downloadSpeed = statsState?.downloadSpeed.toDouble() ?? 0.0;
      final sessionDuration = statsState?.connectionDuration ?? Duration.zero;

      unawaited(bridgeService.updateWidgetState(
        vpnStatus: vpnStatus,
        serverName: serverName,
        uploadSpeed: uploadSpeed,
        downloadSpeed: downloadSpeed,
        sessionDuration: sessionDuration,
      ));
    } catch (e, st) {
      AppLogger.error(
        'WidgetStateListener: Failed to update widget from connection state',
        error: e,
        stackTrace: st,
      );
    }
  }

  /// Updates widget state based on VPN stats.
  void _updateWidgetFromStats(ConnectionStatsEntity statsState) {
    try {
      // Get current connection state
      final asyncState = ref.read(vpnConnectionProvider);
      final connectionState = asyncState.value;
      if (connectionState == null) return;

      final vpnStatus = _mapConnectionStateToStatus(connectionState);
      final serverName = connectionState.server?.name ?? '';

      unawaited(bridgeService.updateWidgetState(
        vpnStatus: vpnStatus,
        serverName: serverName,
        uploadSpeed: statsState.uploadSpeed.toDouble(),
        downloadSpeed: statsState.downloadSpeed.toDouble(),
        sessionDuration: statsState.connectionDuration,
      ));
    } catch (e, st) {
      AppLogger.error(
        'WidgetStateListener: Failed to update widget from stats',
        error: e,
        stackTrace: st,
      );
    }
  }

  /// Maps [VpnConnectionState] to a string status for the widget.
  String _mapConnectionStateToStatus(VpnConnectionState connectionState) {
    return switch (connectionState) {
      VpnConnected() => 'connected',
      VpnConnecting() => 'connecting',
      VpnReconnecting() => 'connecting',
      VpnDisconnected() => 'disconnected',
      VpnDisconnecting() => 'disconnected',
      VpnError() || VpnForceDisconnected() => 'disconnected',
    };
  }
}
