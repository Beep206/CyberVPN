import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/data/datasources/android_system_integration_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const channel = MethodChannel('com.cybervpn.cybervpn_mobile/android_system');
  late MethodChannelAndroidSystemIntegrationService service;
  final methodCalls = <MethodCall>[];

  setUp(() {
    MethodChannelAndroidSystemIntegrationService.debugIsSupportedOverride = true;
    service = MethodChannelAndroidSystemIntegrationService(
      wifiIpLoader: () async => '192.168.1.44',
      wifiIpv6Loader: () async => 'fe80::44',
    );
    methodCalls.clear();

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
          methodCalls.add(call);
          switch (call.method) {
            case 'getLanProxyStatus':
              return <String, Object?>{'socksPort': 10807, 'httpPort': 10808};
            case 'getAppAutoStartStatus':
              return <String, Object?>{
                'bootReceiverReady': true,
                'oemSettingsAvailable': true,
                'batteryOptimizationIgnored': false,
                'manufacturer': 'xiaomi',
                'lastBootHandledAtMs': DateTime(2026, 4, 17, 8).millisecondsSinceEpoch,
              };
            case 'setAppAutoStartEnabled':
            case 'openAppAutoStartSettings':
            case 'openBatteryOptimizationSettings':
              return true;
          }
          return null;
        });
  });

  tearDown(() async {
    MethodChannelAndroidSystemIntegrationService.debugIsSupportedOverride = null;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
  });

  test('reads LAN proxy status with ports and Wi-Fi addresses', () async {
    final status = await service.readLanProxyStatus(enabled: true);

    expect(status.isSupported, isTrue);
    expect(status.enabled, isTrue);
    expect(status.socksPort, 10807);
    expect(status.httpPort, 10808);
    expect(status.wifiIpv4, '192.168.1.44');
    expect(status.wifiIpv6, 'fe80::44');
  });

  test('reads app auto-start status from the Android channel', () async {
    final status = await service.readAppAutoStartStatus(enabled: true);

    expect(status.isSupported, isTrue);
    expect(status.bootReceiverReady, isTrue);
    expect(status.oemSettingsAvailable, isTrue);
    expect(status.manufacturer, 'xiaomi');
    expect(status.lastBootHandledAt, isNotNull);
  });

  test('syncs app auto-start preference through the Android channel', () async {
    await service.syncAppAutoStartPreference(true);

    expect(methodCalls.last.method, 'setAppAutoStartEnabled');
    expect(methodCalls.last.arguments, <String, Object?>{'enabled': true});
  });
}
