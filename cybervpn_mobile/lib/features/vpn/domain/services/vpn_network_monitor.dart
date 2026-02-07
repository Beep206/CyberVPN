import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show networkInfoProvider;

/// Monitors network connectivity changes and notifies VPN layer.
class VpnNetworkMonitor {
  final NetworkInfo _networkInfo;
  StreamSubscription<bool>? _subscription;

  VpnNetworkMonitor({required NetworkInfo networkInfo})
      : _networkInfo = networkInfo;

  void start(void Function(bool isOnline) onNetworkChange) {
    _subscription?.cancel();
    _subscription = _networkInfo.onConnectivityChanged.listen(
      onNetworkChange,
      onError: (Object e) {
        AppLogger.error('Network monitor stream error', error: e);
      },
    );
  }

  void stop() {
    _subscription?.cancel();
    _subscription = null;
  }

  Future<bool> get isConnected => _networkInfo.isConnected;

  void dispose() {
    stop();
  }
}

final vpnNetworkMonitorProvider = Provider<VpnNetworkMonitor>((ref) {
  final monitor = VpnNetworkMonitor(networkInfo: ref.watch(networkInfoProvider));
  ref.onDispose(monitor.dispose);
  return monitor;
});
