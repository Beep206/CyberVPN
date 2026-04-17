import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/vpn_settings_screen.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
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

Widget _buildTestWidget({
  AppSettings settings = const AppSettings(),
  VpnSettingsSupportMatrix? supportMatrix,
  List<SubscriptionUrlMetadata> subscriptionMetadata =
      const <SubscriptionUrlMetadata>[],
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => _FakeSettingsNotifier(settings)),
      importedConfigsProvider.overrideWithValue(const []),
      subscriptionUrlMetadataProvider.overrideWithValue(subscriptionMetadata),
      if (supportMatrix != null)
        vpnSettingsSupportMatrixProvider.overrideWithValue(supportMatrix),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: VpnSettingsScreen(),
    ),
  );
}

void main() {
  group('VpnSettingsScreen hub', () {
    testWidgets('renders modular VPN settings entries', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(supportMatrix: _androidSupportMatrix()),
      );
      await tester.pumpAndSettle();

      expect(find.text('Connection'), findsOneWidget);
      expect(find.text('Operations'), findsOneWidget);
      expect(find.byKey(const Key('nav_vpn_general_settings')), findsOneWidget);
      expect(find.byKey(const Key('nav_vpn_routing_settings')), findsOneWidget);
      expect(
        find.byKey(const Key('nav_vpn_per_app_proxy_settings')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('nav_vpn_advanced_settings')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('nav_vpn_subscription_settings')),
        findsOneWidget,
      );
      expect(find.byKey(const Key('nav_vpn_ping_settings')), findsOneWidget);
    });

    testWidgets('hides per-app proxy entry in standard iOS flow', (
      tester,
    ) async {
      await tester.pumpWidget(
        _buildTestWidget(supportMatrix: _iosSupportMatrix()),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('nav_vpn_per_app_proxy_settings')),
        findsNothing,
      );
      expect(find.byKey(const Key('nav_vpn_routing_settings')), findsOneWidget);
    });

    testWidgets('renders subscription summary from imported metadata', (
      tester,
    ) async {
      await tester.pumpWidget(
        _buildTestWidget(
          supportMatrix: _androidSupportMatrix(),
          subscriptionMetadata: [
            SubscriptionUrlMetadata(
              url: 'https://provider.example/sub',
              serverCount: 3,
              lastUpdated: DateTime(2026, 4, 16, 12),
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('1 subscription source(s)'), findsOneWidget);
    });
  });
}
