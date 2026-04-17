import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_v2ray_plus/flutter_v2ray.dart';

import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_engine_datasource.dart';

class _FakeFlutterV2ray extends FlutterV2ray {
  String? startRemark;
  String? startConfig;
  List<String>? startBlockedApps;
  List<String>? startBypassSubnets;
  List<String>? startDnsServers;
  int? startMtu;
  bool startProxyOnly = false;
  bool startAllowLanConnections = false;
  String? delayConfig;
  String? delayUrl;
  String? delayHttpMethod;
  int startCallCount = 0;

  @override
  Future<void> startVless({
    required String remark,
    required String config,
    List<String>? blockedApps,
    List<String>? bypassSubnets,
    List<String>? dnsServers,
    int? mtu,
    bool proxyOnly = false,
    bool allowLanConnections = false,
    String notificationDisconnectButtonName = 'DISCONNECT',
    bool showNotificationDisconnectButton = true,
    AutoDisconnect? autoDisconnect,
  }) async {
    startCallCount++;
    startRemark = remark;
    startConfig = config;
    startBlockedApps = blockedApps;
    startBypassSubnets = bypassSubnets;
    startDnsServers = dnsServers;
    startMtu = mtu;
    startProxyOnly = proxyOnly;
    startAllowLanConnections = allowLanConnections;
  }

  @override
  Future<int> getServerDelay({
    required String config,
    String url = 'https://google.com/generate_204',
    String httpMethod = 'HEAD',
  }) async {
    delayConfig = config;
    delayUrl = url;
    delayHttpMethod = httpMethod;
    return 42;
  }

  @override
  Future<void> stopVless() async {}
}

class _TestableVpnEngineDatasource extends VpnEngineDatasource {
  _TestableVpnEngineDatasource(this._fake);

  final _FakeFlutterV2ray _fake;

  @override
  FlutterV2ray get v2ray => _fake;
}

void main() {
  late VpnEngineDatasource datasource;

  setUp(() {
    VpnEngineDatasource.debugSupportedPlatformOverride = false;
    datasource = VpnEngineDatasource();
  });

  tearDown(() {
    datasource.dispose();
    VpnEngineDatasource.debugSupportedPlatformOverride = null;
  });

  group('VpnEngineDatasource on unsupported platforms', () {
    test('initialize is a no-op', () async {
      await datasource.initialize(
        providerBundleIdentifier: 'com.cybervpn.vpnextension',
        groupIdentifier: 'group.com.cybervpn',
      );
    });

    test('status stream is empty', () async {
      await expectLater(datasource.statusStream.isEmpty, completion(isTrue));
    });

    test('reports disconnected state without touching the plugin', () {
      expect(datasource.isConnected, isFalse);
      expect(datasource.engineState, VlessEngineState.disconnected);
      expect(datasource.isReconnecting, isFalse);
    });

    test('connect throws UnsupportedError', () async {
      await expectLater(
        datasource.connect('vless://config'),
        throwsA(isA<UnsupportedError>()),
      );
    });

    test('disconnect throws UnsupportedError', () async {
      await expectLater(
        datasource.disconnect(),
        throwsA(isA<UnsupportedError>()),
      );
    });

    test('requestPermission throws UnsupportedError', () async {
      await expectLater(
        datasource.requestPermission(),
        throwsA(isA<UnsupportedError>()),
      );
    });
  });

  group('VpnEngineDatasource runtime config normalization', () {
    late _FakeFlutterV2ray fakeV2ray;

    setUp(() {
      VpnEngineDatasource.debugSupportedPlatformOverride = true;
      fakeV2ray = _FakeFlutterV2ray();
      datasource = _TestableVpnEngineDatasource(fakeV2ray);
    });

    test('connect normalizes raw URIs to JSON and forwards DNS/MTU', () async {
      await datasource.connect(
        'vless://uuid@example.com:443?security=tls&type=tcp#TestServer',
        remark: 'Test Server',
        blockedApps: const ['com.blocked.app'],
        bypassSubnets: const ['10.0.0.0/8'],
        dnsServers: const ['1.1.1.1'],
        mtu: 1400,
        proxyOnly: true,
        allowLanConnections: true,
      );

      expect(fakeV2ray.startRemark, 'Test Server');
      expect(fakeV2ray.startBlockedApps, const ['com.blocked.app']);
      expect(fakeV2ray.startBypassSubnets, const ['10.0.0.0/8']);
      expect(fakeV2ray.startDnsServers, const ['1.1.1.1']);
      expect(fakeV2ray.startMtu, 1400);
      expect(fakeV2ray.startProxyOnly, isTrue);
      expect(fakeV2ray.startAllowLanConnections, isTrue);

      final json = jsonDecode(fakeV2ray.startConfig!) as Map<String, dynamic>;
      expect(json['outbounds'], isA<List<dynamic>>());
    });

    test('getServerDelay normalizes raw URIs before measuring', () async {
      final delay = await datasource.getServerDelay(
        'vless://uuid@example.com:443?security=tls&type=tcp#TestServer',
        url: 'https://example.com/generate_204',
        httpMethod: 'GET',
      );

      expect(delay, 42);
      final json = jsonDecode(fakeV2ray.delayConfig!) as Map<String, dynamic>;
      expect(json['outbounds'], isA<List<dynamic>>());
      expect(fakeV2ray.delayUrl, 'https://example.com/generate_204');
      expect(fakeV2ray.delayHttpMethod, 'GET');
    });

    test('reconnect reuses the last DNS and MTU values', () async {
      await datasource.connect(
        'vless://uuid@example.com:443?security=tls&type=tcp#TestServer',
        dnsServers: const ['9.9.9.9'],
        mtu: 1350,
        proxyOnly: true,
      );

      await datasource.reconnect();

      expect(fakeV2ray.startCallCount, 2);
      expect(fakeV2ray.startDnsServers, const ['9.9.9.9']);
      expect(fakeV2ray.startMtu, 1350);
      expect(fakeV2ray.startProxyOnly, isTrue);
    });
  });
}
