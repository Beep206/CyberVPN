import 'dart:async';

import 'package:quick_actions/quick_actions.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Service for managing app quick actions (long-press shortcuts on home screen).
///
/// Handles registration and dynamic updates of quick action shortcuts for:
/// - Quick Connect / Disconnect (dynamic based on VPN state)
/// - Scan QR Code
/// - Servers List
class QuickActionsService {
  QuickActionsService._();

  static final QuickActionsService instance = QuickActionsService._();

  final QuickActions _quickActions = const QuickActions();
  StreamController<String>? _actionController;

  /// Action types
  static const String actionQuickConnect = 'quick_connect';
  static const String actionDisconnect = 'disconnect';
  static const String actionScanQr = 'scan_qr';
  static const String actionServers = 'servers';

  /// Initialize quick actions with default (disconnected) state.
  ///
  /// Should be called in main.dart before runApp.
  Future<void> initialize() async {
    try {
      await _setDisconnectedActions();
      AppLogger.info('Quick actions initialized', category: 'quick_actions');
    } catch (e, st) {
      AppLogger.error(
        'Failed to initialize quick actions',
        error: e,
        stackTrace: st,
        category: 'quick_actions',
      );
    }
  }

  /// Set quick actions for disconnected state (Quick Connect).
  Future<void> _setDisconnectedActions() async {
    await _quickActions.setShortcutItems([
      const ShortcutItem(
        type: actionQuickConnect,
        localizedTitle: 'Quick Connect',
        icon: 'ic_quick_connect',
      ),
      const ShortcutItem(
        type: actionScanQr,
        localizedTitle: 'Scan QR Code',
        icon: 'ic_scan_qr',
      ),
      const ShortcutItem(
        type: actionServers,
        localizedTitle: 'Servers',
        icon: 'ic_servers',
      ),
    ]);
  }

  /// Set quick actions for connected state (Disconnect).
  Future<void> _setConnectedActions() async {
    await _quickActions.setShortcutItems([
      const ShortcutItem(
        type: actionDisconnect,
        localizedTitle: 'Disconnect',
        icon: 'ic_disconnect',
      ),
      const ShortcutItem(
        type: actionScanQr,
        localizedTitle: 'Scan QR Code',
        icon: 'ic_scan_qr',
      ),
      const ShortcutItem(
        type: actionServers,
        localizedTitle: 'Servers',
        icon: 'ic_servers',
      ),
    ]);
  }

  /// Update quick actions based on VPN connection state.
  ///
  /// Call this when VPN state changes from connected <-> disconnected.
  Future<void> updateForConnectionState(bool isConnected) async {
    try {
      if (isConnected) {
        await _setConnectedActions();
        AppLogger.info(
          'Quick actions updated to connected state',
          category: 'quick_actions',
        );
      } else {
        await _setDisconnectedActions();
        AppLogger.info(
          'Quick actions updated to disconnected state',
          category: 'quick_actions',
        );
      }
    } catch (e, st) {
      AppLogger.error(
        'Failed to update quick actions',
        error: e,
        stackTrace: st,
        category: 'quick_actions',
      );
    }
  }

  /// Set up the handler for quick action taps.
  ///
  /// Returns a stream of action types that can be listened to.
  Stream<String> get actionStream {
    // Create a stream controller to convert the callback-based API to a stream
    _actionController ??= StreamController<String>.broadcast();

    _quickActions.initialize((type) {
      _actionController?.add(type);
    });

    return _actionController!.stream;
  }

  /// Dispose resources when no longer needed.
  void dispose() {
    _actionController?.close();
    _actionController = null;
  }
}
