import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/advanced_vpn_settings_screen.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;

  @override
  Future<void> updateFragmentation(bool enabled) async {
    _settings = _settings.copyWith(fragmentationEnabled: enabled);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateMux(bool enabled) async {
    _settings = _settings.copyWith(muxEnabled: enabled);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updatePreferredIpType(PreferredIpType ipType) async {
    _settings = _settings.copyWith(preferredIpType: ipType);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateSniffing(bool enabled) async {
    _settings = _settings.copyWith(sniffingEnabled: enabled);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateVpnRunMode(VpnRunMode mode) async {
    _settings = _settings.copyWith(vpnRunMode: mode);
    state = AsyncData(_settings);
  }
}

VpnSettingsSupportMatrix _androidSupportMatrix() {
  return VpnSettingsSupportMatrix.fromCapabilities(
    platform: VpnSettingsPlatform.android,
    supportsPerAppProxy: true,
    supportsExcludedRoutes: true,
    supportsServerResolve: true,
    supportsSniffing: true,
    supportsProxyOnlyMode: true,
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
    supportsServerResolve: true,
    supportsSniffing: true,
    supportsProxyOnlyMode: false,
    supportsFragmentation: true,
    supportsMux: true,
    supportsPreferredIpType: true,
    supportsManualMtu: false,
  );
}

Widget _buildTestWidget({
  required _FakeSettingsNotifier notifier,
  required VpnSettingsSupportMatrix supportMatrix,
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => notifier),
      vpnSettingsSupportMatrixProvider.overrideWithValue(supportMatrix),
    ],
    child: const MaterialApp(home: AdvancedVpnSettingsScreen()),
  );
}

void _setLargeSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
}

void main() {
  group('AdvancedVpnSettingsScreen', () {
    testWidgets('renders advanced transport controls', (tester) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(
        find.byKey(const Key('radio_vpn_run_mode_proxy_only')),
      );
      await tester.scrollUntilVisible(
        find.byKey(const Key('radio_ip_type_ipv6')),
        300,
      );

      expect(find.byKey(const Key('toggle_fragmentation')), findsOneWidget);
      expect(find.byKey(const Key('toggle_mux')), findsOneWidget);
      expect(find.byKey(const Key('radio_ip_type_ipv6')), findsOneWidget);
      expect(find.byKey(const Key('toggle_sniffing')), findsOneWidget);
      expect(
        find.byKey(const Key('radio_vpn_run_mode_proxy_only')),
        findsOneWidget,
      );
    });

    testWidgets('updates toggles and preferred ip type', (tester) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('toggle_fragmentation')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('toggle_mux')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.byKey(const Key('toggle_sniffing')));
      await tester.tap(find.byKey(const Key('toggle_sniffing')));
      await tester.pumpAndSettle();
      await tester.ensureVisible(
        find.byKey(const Key('radio_vpn_run_mode_proxy_only')),
      );
      await tester.tap(find.byKey(const Key('radio_vpn_run_mode_proxy_only')));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.byKey(const Key('radio_ip_type_ipv6')),
        300,
      );
      await tester.ensureVisible(find.byKey(const Key('radio_ip_type_ipv6')));
      await tester.tap(find.byKey(const Key('radio_ip_type_ipv6')));
      await tester.pumpAndSettle();

      expect(notifier._settings.fragmentationEnabled, isTrue);
      expect(notifier._settings.muxEnabled, isTrue);
      expect(notifier._settings.sniffingEnabled, isTrue);
      expect(notifier._settings.vpnRunMode, VpnRunMode.proxyOnly);
      expect(notifier._settings.preferredIpType, PreferredIpType.ipv6);
    });

    testWidgets('shows reduced semantics notice on iOS', (tester) async {
      _setLargeSurface(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _iosSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('advanced_settings_notice')), findsOneWidget);
      expect(find.textContaining('Android-only'), findsOneWidget);
    });
  });
}
