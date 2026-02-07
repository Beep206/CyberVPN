import 'dart:async';

import 'package:flutter/widgets.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Observes app lifecycle events and triggers VPN state reconciliation
/// when the app resumes from background.
///
/// iOS aggressively kills background VPN tunnels, so the UI may show
/// "Connected" when the tunnel is dead.
class VpnLifecycleReconciler extends WidgetsBindingObserver {
  final Future<void> Function() onResumed;

  VpnLifecycleReconciler({required this.onResumed});

  void register() {
    WidgetsBinding.instance.addObserver(this);
  }

  void unregister() {
    WidgetsBinding.instance.removeObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      AppLogger.debug(
        'App resumed from background, reconciling VPN state',
        category: 'vpn.lifecycle',
      );
      unawaited(onResumed());
    }
  }
}
