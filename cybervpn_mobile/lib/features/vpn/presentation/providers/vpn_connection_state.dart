import 'package:flutter/widgets.dart';

import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart'
    show VpnProtocol;
export 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart'
    show VpnProtocol;

// ---------------------------------------------------------------------------
// VPN Connection State -- Sealed class hierarchy
// ---------------------------------------------------------------------------

/// Sealed base class representing all possible VPN connection states.
@immutable
sealed class VpnConnectionState {
  const VpnConnectionState();

  /// Convenience getters common across all states.
  bool get isConnected => this is VpnConnected;
  bool get isDisconnected => this is VpnDisconnected;
  bool get isConnecting => this is VpnConnecting;
  bool get isDisconnecting => this is VpnDisconnecting;
  bool get isReconnecting => this is VpnReconnecting;
  bool get isError => this is VpnError;

  /// Returns the server if the state carries one, otherwise null.
  ServerEntity? get server {
    return switch (this) {
      final VpnConnecting s => s.server,
      final VpnConnected s => s.server,
      final VpnReconnecting s => s.server,
      _ => null,
    };
  }
}

class VpnDisconnected extends VpnConnectionState {
  const VpnDisconnected();
}

class VpnConnecting extends VpnConnectionState {
  @override
  final ServerEntity? server;
  const VpnConnecting({this.server});
}

class VpnConnected extends VpnConnectionState {
  @override
  final ServerEntity server;
  final VpnProtocol protocol;
  const VpnConnected({required this.server, required this.protocol});
}

class VpnDisconnecting extends VpnConnectionState {
  const VpnDisconnecting();
}

class VpnReconnecting extends VpnConnectionState {
  final int attempt;
  @override
  final ServerEntity? server;
  const VpnReconnecting({required this.attempt, this.server});
}

class VpnError extends VpnConnectionState {
  final String message;
  const VpnError({required this.message});
}

/// The server forced this client to disconnect (e.g. session limit,
/// account suspended). The UI should show a prominent dialog.
class VpnForceDisconnected extends VpnConnectionState {
  final String reason;
  const VpnForceDisconnected({required this.reason});
}
