import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// Platform channel name for Quick Settings tile communication.
const _kTileToggleChannel = 'com.cybervpn.quicksettings/tile';

/// Method channel for broadcasting state updates to Android.
const _kStateUpdateMethod = 'com.cybervpn.cybervpn_mobile/vpn_state_broadcast';

/// Provider for [QuickSettingsChannel].
final quickSettingsChannelProvider = Provider<QuickSettingsChannel>((ref) {
  final channel = QuickSettingsChannel(ref: ref);

  // Listen to VPN state changes and broadcast to tile
  ref.listen<AsyncValue<VpnConnectionState>>(
    vpnConnectionProvider,
    (previous, next) {
      next.whenData((state) {
        channel.broadcastVpnState(state);
      });
    },
  );

  return channel;
});

/// Handles platform channel communication with Android Quick Settings tile.
///
/// Responsibilities:
/// - Handle VPN toggle requests from the Quick Settings tile
/// - Broadcast VPN state changes to the tile for UI updates via Android Intent
/// - Maintain bidirectional communication between Flutter and native Android
class QuickSettingsChannel {
  final Ref ref;
  final MethodChannel _methodChannel;
  final MethodChannel _stateUpdateChannel;

  QuickSettingsChannel({
    required this.ref,
  })  : _methodChannel = const MethodChannel(_kTileToggleChannel),
        _stateUpdateChannel = const MethodChannel(_kStateUpdateMethod) {
    _initialize();
  }

  /// Initializes platform channels and sets up handlers.
  void _initialize() {
    // Set up method channel handler for tile -> Flutter communication
    _methodChannel.setMethodCallHandler(_handleMethodCall);

    AppLogger.info('QuickSettingsChannel: Initialized');
  }

  /// Handles incoming method calls from the Quick Settings tile.
  Future<dynamic> _handleMethodCall(MethodCall call) async {
    AppLogger.info('QuickSettingsChannel: Received method call: ${call.method}');

    switch (call.method) {
      case 'toggleVpn':
        return await _handleToggleVpn();
      default:
        throw PlatformException(
          code: 'UNIMPLEMENTED',
          message: 'Method ${call.method} not implemented',
        );
    }
  }

  /// Handles VPN toggle action from Quick Settings tile.
  ///
  /// Toggle logic:
  /// - If connected or connecting: disconnect
  /// - If disconnected: connect (requires last server to be available)
  Future<bool> _handleToggleVpn() async {
    try {
      final asyncState = ref.read(vpnConnectionProvider);
      final connectionState = asyncState.value;

      if (connectionState == null) {
        AppLogger.warning('QuickSettingsChannel: Connection state not available');
        return false;
      }

      final notifier = ref.read(vpnConnectionProvider.notifier);

      if (connectionState.isConnected || connectionState.isConnecting) {
        // Disconnect VPN
        AppLogger.info('QuickSettingsChannel: Disconnecting VPN from tile');
        await notifier.disconnect();
        return true;
      } else if (connectionState.isDisconnecting) {
        // Already disconnecting, ignore
        AppLogger.info('QuickSettingsChannel: Already disconnecting');
        return true;
      } else {
        // Disconnected or error state
        // Note: Connect logic from disconnected state pending implementation.
        // This requires storing and retrieving the last connected server.
        // For now, log and return false
        AppLogger.info(
          'QuickSettingsChannel: Cannot connect from tile - last server unknown',
        );
        return false;
      }
    } catch (e, st) {
      AppLogger.error(
        'QuickSettingsChannel: Failed to toggle VPN',
        error: e,
        stackTrace: st,
      );
      return false;
    }
  }

  /// Broadcasts VPN connection state to the Quick Settings tile via Android Intent.
  ///
  /// Maps [VpnConnectionState] to string values that the Android tile expects:
  /// - disconnected
  /// - connecting
  /// - connected
  /// - disconnecting
  /// - error
  void broadcastVpnState(VpnConnectionState state) {
    final stateString = _mapStateToString(state);

    AppLogger.debug('QuickSettingsChannel: Broadcasting state: $stateString');

    try {
      unawaited(_stateUpdateChannel.invokeMethod('updateTileState', {
        'state': stateString,
      }));
    } catch (e) {
      AppLogger.error('QuickSettingsChannel: Failed to broadcast state', error: e);
    }
  }

  /// Maps Flutter [VpnConnectionState] to string for native Android.
  String _mapStateToString(VpnConnectionState state) {
    if (state.isDisconnected) {
      return 'disconnected';
    } else if (state.isConnecting) {
      return 'connecting';
    } else if (state.isConnected) {
      return 'connected';
    } else if (state.isDisconnecting) {
      return 'disconnecting';
    } else if (state.isError) {
      return 'error';
    } else if (state.isReconnecting) {
      return 'connecting'; // Treat reconnecting as connecting
    }
    return 'disconnected'; // Default
  }

  /// Disposes resources.
  void dispose() {
    AppLogger.info('QuickSettingsChannel: Disposed');
  }
}
