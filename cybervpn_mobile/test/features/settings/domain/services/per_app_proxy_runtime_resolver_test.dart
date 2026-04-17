import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/installed_app.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/per_app_proxy_runtime_resolver.dart';

void main() {
  const resolver = PerAppProxyRuntimeResolver();

  const installedApps = [
    InstalledApp(packageName: 'com.example.alpha', displayName: 'Alpha'),
    InstalledApp(packageName: 'com.example.beta', displayName: 'Beta'),
    InstalledApp(packageName: 'com.example.gamma', displayName: 'Gamma'),
  ];

  group('PerAppProxyRuntimeResolver', () {
    test('returns empty list when mode is off', () {
      final blockedApps = resolver.resolveBlockedApps(
        mode: PerAppProxyMode.off,
        selectedAppIds: ['com.example.alpha'],
        installedApps: installedApps,
      );

      expect(blockedApps, isEmpty);
    });

    test('returns selected apps for bypassSelected mode', () {
      final blockedApps = resolver.resolveBlockedApps(
        mode: PerAppProxyMode.bypassSelected,
        selectedAppIds: const [
          'com.example.gamma',
          'com.example.alpha',
          'com.unknown.missing',
        ],
        installedApps: installedApps,
      );

      expect(blockedApps, equals(['com.example.alpha', 'com.example.gamma']));
    });

    test('returns all non-selected apps for proxySelected mode', () {
      final blockedApps = resolver.resolveBlockedApps(
        mode: PerAppProxyMode.proxySelected,
        selectedAppIds: const ['com.example.beta'],
        installedApps: installedApps,
      );

      expect(blockedApps, equals(['com.example.alpha', 'com.example.gamma']));
    });

    test('excludes current package from proxy resolution', () {
      final blockedApps = resolver.resolveBlockedApps(
        mode: PerAppProxyMode.proxySelected,
        selectedAppIds: const ['com.example.alpha'],
        installedApps: const [
          InstalledApp(packageName: 'com.example.alpha', displayName: 'Alpha'),
          InstalledApp(
            packageName: 'com.cybervpn.cybervpn_mobile',
            displayName: 'CyberVPN',
          ),
        ],
        currentPackageName: 'com.cybervpn.cybervpn_mobile',
      );

      expect(blockedApps, isEmpty);
    });
  });
}
