import 'dart:async';
import 'package:flutter_v2ray_plus/flutter_v2ray.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class VpnEngineDatasource {
  FlutterV2ray? _v2ray;
  VlessStatus? _lastStatus;
  StreamSubscription<VlessStatus>? _statusSubscription;
  bool _initialized = false;

  FlutterV2ray get v2ray {
    _v2ray ??= FlutterV2ray();
    return _v2ray!;
  }

  Future<void> initialize({
    required String providerBundleIdentifier,
    required String groupIdentifier,
    String notificationIconResourceType = 'mipmap',
    String notificationIconResourceName = 'ic_launcher',
  }) async {
    if (_initialized) return;
    _initialized = true;

    v2ray.initializeVless(
      notificationIconResourceType: notificationIconResourceType,
      notificationIconResourceName: notificationIconResourceName,
      providerBundleIdentifier: providerBundleIdentifier,
      groupIdentifier: groupIdentifier,
    );
    // Subscribe to status updates (store subscription to avoid leak)
    _statusSubscription = v2ray.onStatusChanged.listen((status) {
      _lastStatus = status;
    });
    AppLogger.info('V2Ray engine initialized');
  }

  Future<void> connect(String config, {String? remark, List<String>? blockedApps}) async {
    final v2rayConfig = FlutterV2ray.parseFromURL(config);
    await v2ray.startVless(
      remark: remark ?? 'CyberVPN',
      config: v2rayConfig.getFullConfiguration(),
      blockedApps: blockedApps ?? [],
      bypassSubnets: [],
      proxyOnly: false,
    );
    AppLogger.info('V2Ray connected');
  }

  Future<void> disconnect() async {
    await v2ray.stopVless();
    AppLogger.info('V2Ray disconnected');
  }

  bool get isConnected {
    return _lastStatus?.state == 'CONNECTED';
  }

  Stream<VlessStatus> get statusStream => v2ray.onStatusChanged;

  Future<int> getServerDelay(String config) async {
    return v2ray.getServerDelay(config: config);
  }

  Future<int> getConnectedServerDelay() async {
    return v2ray.getConnectedServerDelay();
  }

  Future<bool> requestPermission() async {
    return v2ray.requestPermission();
  }

  Future<String> getCoreVersion() async {
    return v2ray.getCoreVersion();
  }

  void dispose() {
    _statusSubscription?.cancel();
    _statusSubscription = null;
    _v2ray = null;
    _lastStatus = null;
    _initialized = false;
  }
}
