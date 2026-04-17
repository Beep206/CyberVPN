import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/data/datasources/per_app_proxy_platform_service.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/installed_app.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/per_app_proxy_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/per_app_proxy_screen.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;

  @override
  Future<void> updatePerAppProxyMode(PerAppProxyMode mode) async {
    _settings = _settings.copyWith(perAppProxyMode: mode);
    state = AsyncData(_settings);
  }

  @override
  Future<void> togglePerAppProxyApp(String appId) async {
    final appIds = [..._settings.perAppProxyAppIds];
    if (appIds.contains(appId)) {
      appIds.remove(appId);
    } else {
      appIds.add(appId);
    }
    _settings = _settings.copyWith(perAppProxyAppIds: appIds);
    state = AsyncData(_settings);
  }
}

class _FakePerAppProxyPlatformService implements PerAppProxyPlatformService {
  const _FakePerAppProxyPlatformService({
    required this.isSupported,
    this.apps = const <InstalledApp>[],
  });

  @override
  final bool isSupported;

  final List<InstalledApp> apps;

  @override
  Future<List<InstalledApp>> getInstalledApps() async => apps;

  @override
  Future<String?> getCurrentPackageName() async => null;
}

Widget _buildTestWidget({
  required _FakeSettingsNotifier notifier,
  required _FakePerAppProxyPlatformService platformService,
  VpnSettingsSupportMatrix? supportMatrix,
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => notifier),
      perAppProxyPlatformServiceProvider.overrideWithValue(platformService),
      if (supportMatrix != null)
        vpnSettingsSupportMatrixProvider.overrideWithValue(supportMatrix),
    ],
    child: const MaterialApp(home: PerAppProxyScreen()),
  );
}

VpnSettingsSupportMatrix _androidSupportMatrix() {
  return VpnSettingsSupportMatrix.fromCapabilities(
    platform: VpnSettingsPlatform.android,
    supportsPerAppProxy: true,
    supportsExcludedRoutes: true,
    supportsFragmentation: true,
    supportsMux: true,
    supportsPreferredIpType: true,
    supportsManualMtu: true,
  );
}

VpnSettingsSupportMatrix _iosSupportMatrix() {
  return VpnSettingsSupportMatrix.fromCapabilities(
    platform: VpnSettingsPlatform.ios,
    supportsPerAppProxy: false,
    supportsExcludedRoutes: false,
    supportsFragmentation: true,
    supportsMux: true,
    supportsPreferredIpType: true,
    supportsManualMtu: false,
  );
}

void main() {
  group('PerAppProxyScreen', () {
    testWidgets('shows unsupported notice when platform is not supported', (
      tester,
    ) async {
      final notifier = _FakeSettingsNotifier();
      const platformService = _FakePerAppProxyPlatformService(
        isSupported: false,
      );

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          platformService: platformService,
          supportMatrix: _iosSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('per_app_proxy_unsupported_notice')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('per_app_proxy_status_tile')),
        findsOneWidget,
      );
      expect(find.byKey(const Key('radio_per_app_mode_off')), findsNothing);
      expect(find.textContaining('Android-only'), findsOneWidget);
    });

    testWidgets('renders installed apps and toggles app selection', (
      tester,
    ) async {
      final notifier = _FakeSettingsNotifier(
        const AppSettings(perAppProxyMode: PerAppProxyMode.proxySelected),
      );
      const platformService = _FakePerAppProxyPlatformService(
        isSupported: true,
        apps: [
          InstalledApp(packageName: 'com.example.alpha', displayName: 'Alpha'),
          InstalledApp(packageName: 'com.example.beta', displayName: 'Beta'),
        ],
      );

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          platformService: platformService,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Alpha'), findsOneWidget);
      expect(find.text('Beta'), findsOneWidget);

      await tester.tap(find.byKey(const Key('checkbox_app_com.example.alpha')));
      await tester.pumpAndSettle();

      expect(notifier._settings.perAppProxyAppIds, ['com.example.alpha']);
    });
  });
}
