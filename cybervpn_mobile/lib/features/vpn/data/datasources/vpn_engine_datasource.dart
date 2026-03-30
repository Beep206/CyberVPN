import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb, visibleForTesting;
import 'package:flutter_v2ray_plus/flutter_v2ray.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Maps the raw string states from [VlessStatus.state] to typed values.
enum VlessEngineState {
  connecting,
  connected,
  disconnected,
  reconnecting,
  stopped,
  unknown;

  static VlessEngineState fromString(String raw) {
    return switch (raw.toUpperCase()) {
      'CONNECTED' => VlessEngineState.connected,
      'CONNECTING' => VlessEngineState.connecting,
      'DISCONNECTED' => VlessEngineState.disconnected,
      'RECONNECTING' => VlessEngineState.reconnecting,
      'STOPPED' => VlessEngineState.stopped,
      _ => () {
        AppLogger.warning(
          'Unknown V2Ray engine state: "$raw"',
          category: 'vpn.engine',
        );
        return VlessEngineState.unknown;
      }(),
    };
  }
}

class VpnEngineDatasource {
  @visibleForTesting
  static bool? debugSupportedPlatformOverride;

  FlutterV2ray? _v2ray;
  VlessStatus? _lastStatus;
  StreamSubscription<VlessStatus>? _statusSubscription;
  bool _initialized = false;
  bool _isReconnecting = false;

  /// Last config used for connect, stored for reconnect.
  String? _lastConfig;
  String? _lastRemark;
  List<String>? _lastBlockedApps;

  FlutterV2ray get v2ray {
    _v2ray ??= FlutterV2ray();
    return _v2ray!;
  }

  bool get _isSupportedPlatform {
    final override = debugSupportedPlatformOverride;
    if (override != null) {
      return override;
    }

    if (kIsWeb) {
      return false;
    }

    return Platform.isAndroid || Platform.isIOS;
  }

  UnsupportedError _unsupportedAction(String action) {
    final platformLabel = kIsWeb ? 'web' : Platform.operatingSystem;
    return UnsupportedError(
      'flutter_v2ray_plus does not support $platformLabel for $action.',
    );
  }

  Future<void> initialize({
    required String providerBundleIdentifier,
    required String groupIdentifier,
    String notificationIconResourceType = 'mipmap',
    String notificationIconResourceName = 'ic_launcher',
  }) async {
    if (!_isSupportedPlatform) {
      AppLogger.info(
        'Skipping V2Ray engine initialization on unsupported platform',
        category: 'vpn.engine',
      );
      return;
    }

    if (_initialized) return;
    _initialized = true;

    await v2ray.initializeVless(
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

  Future<void> connect(
    String config, {
    String? remark,
    List<String>? blockedApps,
  }) async {
    if (!_isSupportedPlatform) {
      throw _unsupportedAction('VPN connect');
    }

    _lastConfig = config;
    _lastRemark = remark;
    _lastBlockedApps = blockedApps;

    final v2rayConfig = FlutterV2ray.parseFromURL(config);
    await v2ray.startVless(
      remark: remark ?? 'CyberVPN',
      config: v2rayConfig.getFullConfiguration(),
      blockedApps: blockedApps ?? [],
      bypassSubnets: [],
      proxyOnly: false,
    );
    _isReconnecting = false;
    AppLogger.info('V2Ray connected');
  }

  Future<void> disconnect() async {
    if (!_isSupportedPlatform) {
      throw _unsupportedAction('VPN disconnect');
    }

    _isReconnecting = false;
    await v2ray.stopVless();
    AppLogger.info('V2Ray disconnected');
  }

  /// Disconnects and reconnects using the last stored config.
  ///
  /// Throws [StateError] if no previous connection config exists.
  Future<void> reconnect() async {
    if (!_isSupportedPlatform) {
      throw _unsupportedAction('VPN reconnect');
    }

    final config = _lastConfig;
    if (config == null) {
      throw StateError('Cannot reconnect: no previous connection config');
    }

    _isReconnecting = true;
    AppLogger.info('V2Ray reconnecting...', category: 'vpn.engine');

    await v2ray.stopVless();
    await connect(config, remark: _lastRemark, blockedApps: _lastBlockedApps);
  }

  /// Whether a reconnect is currently in progress.
  bool get isReconnecting => _isReconnecting;

  bool get isConnected {
    if (!_isSupportedPlatform) return false;
    if (_lastStatus == null) return false;
    return VlessEngineState.fromString(_lastStatus!.state) ==
        VlessEngineState.connected;
  }

  VlessEngineState get engineState {
    if (!_isSupportedPlatform) {
      return VlessEngineState.disconnected;
    }

    if (_lastStatus == null) return VlessEngineState.disconnected;
    return VlessEngineState.fromString(_lastStatus!.state);
  }

  Stream<VlessStatus> get statusStream => !_isSupportedPlatform
      ? const Stream<VlessStatus>.empty()
      : v2ray.onStatusChanged.distinct((a, b) => a.state == b.state);

  Future<int> getServerDelay(String config) async {
    if (!_isSupportedPlatform) {
      throw _unsupportedAction('server delay checks');
    }

    return v2ray.getServerDelay(config: config);
  }

  Future<int> getConnectedServerDelay() async {
    if (!_isSupportedPlatform) {
      throw _unsupportedAction('connected server delay checks');
    }

    return v2ray.getConnectedServerDelay();
  }

  Future<bool> requestPermission() async {
    if (!_isSupportedPlatform) {
      throw _unsupportedAction('VPN permission requests');
    }

    return v2ray.requestPermission();
  }

  Future<String> getCoreVersion() async {
    if (!_isSupportedPlatform) {
      throw _unsupportedAction('core version requests');
    }

    return v2ray.getCoreVersion();
  }

  void dispose() {
    unawaited(_statusSubscription?.cancel());
    _statusSubscription = null;
    _v2ray = null;
    _lastStatus = null;
    _lastConfig = null;
    _lastRemark = null;
    _lastBlockedApps = null;
    _isReconnecting = false;
    _initialized = false;
  }
}
