import 'dart:async';
import 'package:flutter_v2ray_plus/flutter_v2ray.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class VpnEngineDatasource {
  FlutterV2ray? _v2ray;

  FlutterV2ray get v2ray {
    _v2ray ??= FlutterV2ray();
    return _v2ray!;
  }

  Future<void> initialize() async {
    await v2ray.initializeV2Ray();
    AppLogger.info('V2Ray engine initialized');
  }

  Future<void> connect(String config, {String? remark}) async {
    final v2rayConfig = FlutterV2ray.parseFromURL(config);
    await v2ray.startV2Ray(remark: remark ?? 'CyberVPN', config: v2rayConfig);
    AppLogger.info('V2Ray connected');
  }

  Future<void> disconnect() async {
    await v2ray.stopV2Ray();
    AppLogger.info('V2Ray disconnected');
  }

  Future<bool> get isConnected async {
    return v2ray.status.state == 'CONNECTED';
  }

  Stream<VlessStatus> get statusStream => v2ray.onStatusChanged;

  Future<int> getConnectedServerDelay(String config) async {
    return v2ray.getConnectedServerDelay(url: config);
  }

  void dispose() {
    _v2ray = null;
  }
}
