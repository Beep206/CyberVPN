import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/data/datasources/per_app_proxy_platform_service.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/installed_app.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const channel = MethodChannel('com.cybervpn.cybervpn_mobile/per_app_proxy');
  const service = MethodChannelPerAppProxyPlatformService();

  setUp(() {
    MethodChannelPerAppProxyPlatformService.debugIsSupportedOverride = true;
  });

  tearDown(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
    MethodChannelPerAppProxyPlatformService.debugIsSupportedOverride = null;
  });

  group('MethodChannelPerAppProxyPlatformService', () {
    test('maps installed apps from the platform channel', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async {
            if (call.method == 'getInstalledApps') {
              return [
                {
                  'packageName': 'com.example.beta',
                  'displayName': 'Beta',
                  'isSystemApp': true,
                },
                {
                  'packageName': 'com.example.alpha',
                  'displayName': 'Alpha',
                  'isSystemApp': false,
                },
              ];
            }
            return null;
          });

      final apps = await service.getInstalledApps();

      expect(
        apps,
        equals(const [
          InstalledApp(
            packageName: 'com.example.alpha',
            displayName: 'Alpha',
            isSystemApp: false,
          ),
          InstalledApp(
            packageName: 'com.example.beta',
            displayName: 'Beta',
            isSystemApp: true,
          ),
        ]),
      );
    });

    test('returns current package name from the platform channel', () async {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(channel, (call) async {
            if (call.method == 'getCurrentPackageName') {
              return 'com.cybervpn.cybervpn_mobile';
            }
            return null;
          });

      final packageName = await service.getCurrentPackageName();

      expect(packageName, 'com.cybervpn.cybervpn_mobile');
    });

    test('returns empty result on unsupported platforms', () async {
      MethodChannelPerAppProxyPlatformService.debugIsSupportedOverride = false;

      expect(await service.getInstalledApps(), isEmpty);
      expect(await service.getCurrentPackageName(), isNull);
    });
  });
}
