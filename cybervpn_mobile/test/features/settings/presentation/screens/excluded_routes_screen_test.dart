import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/excluded_routes_screen.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;

  @override
  Future<void> updateBypassSubnets(List<String> subnets) async {
    _settings = _settings.copyWith(bypassSubnets: subnets);
    state = AsyncData(_settings);
  }

  @override
  Future<void> updateExcludedRouteEntries(
    List<ExcludedRouteEntry> entries,
  ) async {
    _settings = _settings.copyWith(
      excludedRouteEntries: entries,
      bypassSubnets: entries
          .map((entry) => entry.normalizedValue)
          .toList(growable: false),
    );
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

Widget _buildTestWidget(
  _FakeSettingsNotifier notifier, {
  VpnSettingsSupportMatrix? supportMatrix,
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => notifier),
      if (supportMatrix != null)
        vpnSettingsSupportMatrixProvider.overrideWithValue(supportMatrix),
    ],
    child: const MaterialApp(home: ExcludedRoutesScreen()),
  );
}

void main() {
  group('ExcludedRoutesScreen', () {
    testWidgets('adds a valid IPv6 route', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(notifier, supportMatrix: _androidSupportMatrix()),
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('input_excluded_route')),
        '2001:db8::/32',
      );
      await tester.tap(find.byKey(const Key('button_add_excluded_route')));
      await tester.pumpAndSettle();

      expect(notifier._settings.bypassSubnets, ['2001:db8::/32']);
      expect(
        find.byKey(const Key('excluded_route_2001:db8::/32')),
        findsOneWidget,
      );
    });

    testWidgets('shows a snackbar for an invalid route', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(notifier, supportMatrix: _androidSupportMatrix()),
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('input_excluded_route')),
        'not-a-route',
      );
      await tester.tap(find.byKey(const Key('button_add_excluded_route')));
      await tester.pumpAndSettle();

      expect(notifier._settings.bypassSubnets, isEmpty);
      expect(
        find.textContaining('valid IPv4 or IPv6 address/CIDR'),
        findsOneWidget,
      );
    });

    testWidgets('removes an existing route', (tester) async {
      final notifier = _FakeSettingsNotifier(
        const AppSettings(
          excludedRouteEntries: [
            ExcludedRouteEntry(
              rawValue: '10.0.0.0/8',
              targetType: ExcludedRouteTargetType.ipv4Cidr,
            ),
          ],
          bypassSubnets: ['10.0.0.0/8'],
        ),
      );

      await tester.pumpWidget(
        _buildTestWidget(notifier, supportMatrix: _androidSupportMatrix()),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.delete_outline));
      await tester.pumpAndSettle();

      expect(notifier._settings.bypassSubnets, isEmpty);
      expect(find.byKey(const Key('excluded_route_10.0.0.0/8')), findsNothing);
    });

    testWidgets(
      'shows read-only iOS copy when excluded routes are unsupported',
      (tester) async {
        final notifier = _FakeSettingsNotifier(
          const AppSettings(bypassSubnets: ['10.0.0.0/8']),
        );

        await tester.pumpWidget(
          _buildTestWidget(notifier, supportMatrix: _iosSupportMatrix()),
        );
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('input_excluded_route')), findsNothing);
        expect(
          find.byKey(const Key('button_add_excluded_route')),
          findsNothing,
        );
        expect(find.byIcon(Icons.delete_outline), findsNothing);
        expect(
          find.textContaining('remain stored for Android runtime'),
          findsWidgets,
        );
        expect(
          find.textContaining(
            'not yet wired through the current iOS tunnel provider',
          ),
          findsOneWidget,
        );
      },
    );
  });
}
