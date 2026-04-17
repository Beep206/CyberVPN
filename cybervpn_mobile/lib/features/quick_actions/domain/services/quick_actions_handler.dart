import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_service.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// Provider that handles quick action taps.
///
/// Listens to the quick actions stream and executes the appropriate action
/// (navigation or VPN operation) when a user taps a quick action shortcut.
final quickActionsHandlerProvider = Provider<QuickActionsHandler>((ref) {
  final handler = QuickActionsHandler(ref);
  ref.onDispose(handler.dispose);
  return handler;
});

/// Global key to access navigation context from anywhere in the app.
///
/// Set in app_router.dart and used by QuickActionsHandler for navigation.
final rootNavigatorKey = GlobalKey<NavigatorState>();

class QuickActionsHandler with WidgetsBindingObserver {
  QuickActionsHandler(this._ref) {
    _initialize();
    WidgetsBinding.instance.addObserver(this);
  }

  final Ref _ref;
  StreamSubscription<String>? _actionSubscription;

  /// Queued action type to execute when navigator context becomes available.
  String? _pendingAction;

  void _initialize() {
    // Listen to quick action taps
    _actionSubscription = QuickActionsService.instance.actionStream.listen(
      (actionType) {
        AppLogger.info(
          'Quick action tapped: $actionType',
          category: 'quick_actions',
        );
        _handleAction(actionType);
      },
      onError: (Object e, StackTrace st) {
        AppLogger.error(
          'Quick actions handler error',
          error: e,
          stackTrace: st,
          category: 'quick_actions',
        );
      },
    );
  }

  void _handleAction(String actionType) {
    switch (actionType) {
      case QuickActionsService.actionQuickConnect:
        unawaited(_handleQuickConnect());
      case QuickActionsService.actionDisconnect:
        unawaited(_handleDisconnect());
      case QuickActionsService.actionScanQr:
        _handleScanQr();
      case QuickActionsService.actionServers:
        _handleServers();
      default:
        AppLogger.warning(
          'Unknown quick action type: $actionType',
          category: 'quick_actions',
        );
    }
  }

  /// Handle Quick Connect action.
  ///
  /// Resolves the target using the stored subscription connect strategy.
  Future<void> _handleQuickConnect() async {
    try {
      final connectionNotifier = _ref.read(vpnConnectionProvider.notifier);
      final currentState = _ref.read(vpnConnectionProvider).value;

      // If already connected, do nothing
      if (currentState?.isConnected ?? false) {
        AppLogger.info(
          'Quick connect: already connected, ignoring',
          category: 'quick_actions',
        );
        return;
      }

      await connectionNotifier.connectBySubscriptionPolicy(
        trigger: 'quick_action',
      );
    } catch (e, st) {
      AppLogger.error(
        'Quick connect failed',
        error: e,
        stackTrace: st,
        category: 'quick_actions',
      );
    }
  }

  /// Handle Disconnect action.
  Future<void> _handleDisconnect() async {
    try {
      final connectionNotifier = _ref.read(vpnConnectionProvider.notifier);
      await connectionNotifier.disconnect();
      AppLogger.info('Quick action: disconnected', category: 'quick_actions');
    } catch (e, st) {
      AppLogger.error(
        'Quick disconnect failed',
        error: e,
        stackTrace: st,
        category: 'quick_actions',
      );
    }
  }

  /// Handle Scan QR Code action.
  ///
  /// Navigates to the QR scanner screen. If the navigator context is
  /// unavailable (app in background), the action is queued and retried
  /// when the app resumes.
  void _handleScanQr() {
    _navigateOrQueue(
      QuickActionsService.actionScanQr,
      () {
        final context = rootNavigatorKey.currentContext!;
        unawaited(context.pushNamed('config-import-qr-scanner'));
        AppLogger.info(
          'Quick action: navigated to QR scanner',
          category: 'quick_actions',
        );
      },
    );
  }

  /// Handle Servers action.
  ///
  /// Navigates to the servers list screen. If the navigator context is
  /// unavailable, the action is queued and retried on foreground.
  void _handleServers() {
    _navigateOrQueue(
      QuickActionsService.actionServers,
      () {
        final context = rootNavigatorKey.currentContext!;
        context.goNamed('servers');
        AppLogger.info(
          'Quick action: navigated to servers',
          category: 'quick_actions',
        );
      },
    );
  }

  /// Executes [navigate] if the root navigator context is available,
  /// otherwise queues [actionType] for retry on app resume.
  void _navigateOrQueue(String actionType, VoidCallback navigate) {
    try {
      final context = rootNavigatorKey.currentContext;
      if (context == null) {
        _pendingAction = actionType;
        AppLogger.info(
          'Quick action queued (no context): $actionType',
          category: 'quick_actions',
        );
        return;
      }
      navigate();
    } catch (e, st) {
      AppLogger.error(
        'Quick action navigation failed: $actionType',
        error: e,
        stackTrace: st,
        category: 'quick_actions',
      );
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _pendingAction != null) {
      final action = _pendingAction!;
      _pendingAction = null;
      AppLogger.info(
        'Replaying queued quick action: $action',
        category: 'quick_actions',
      );
      _handleAction(action);
    }
  }

  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    unawaited(_actionSubscription?.cancel());
  }
}
