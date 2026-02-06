import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_state.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_notifier.dart';

export 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_state.dart';
export 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_notifier.dart';

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether the VPN is currently connected.
final isConnectedProvider = Provider<bool>((ref) {
  final asyncState = ref.watch(vpnConnectionProvider);
  return asyncState.value?.isConnected ?? false;
});

/// The server we are currently connected to (or connecting to), if any.
final currentServerProvider = Provider<ServerEntity?>((ref) {
  final asyncState = ref.watch(vpnConnectionProvider);
  return asyncState.value?.server;
});

/// The active VPN protocol while connected.
final activeProtocolProvider = Provider<VpnProtocol?>((ref) {
  final asyncState = ref.watch(vpnConnectionProvider);
  return switch (asyncState.value) {
    VpnConnected(:final protocol) => protocol,
    _ => null,
  };
});
