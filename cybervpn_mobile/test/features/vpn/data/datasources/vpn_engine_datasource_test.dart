import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_engine_datasource.dart';

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
}
