import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:async';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_service.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// Provider that listens to VPN connection state changes and updates
/// quick actions accordingly.
///
/// This provider should be watched somewhere in the app (e.g., in the root
/// widget or main shell) to ensure it stays alive and listens to state changes.
final quickActionsListenerProvider = Provider<QuickActionsListener>((ref) {
  final listener = QuickActionsListener(ref);
  listener._initialize();
  return listener;
});

class QuickActionsListener {
  QuickActionsListener(this._ref);

  final Ref _ref;
  bool? _lastIsConnectedState;

  void _initialize() {
    // Listen to VPN connection state changes
    _ref.listen<AsyncValue<VpnConnectionState>>(
      vpnConnectionProvider,
      (previous, next) {
        final isConnected = next.value?.isConnected ?? false;

        // Only update if the connection state actually changed
        if (_lastIsConnectedState != isConnected) {
          _lastIsConnectedState = isConnected;
          unawaited(QuickActionsService.instance.updateForConnectionState(isConnected));

          AppLogger.info(
            'Quick actions listener detected state change: isConnected=$isConnected',
            category: 'quick_actions',
          );
        }
      },
    );
  }
}
