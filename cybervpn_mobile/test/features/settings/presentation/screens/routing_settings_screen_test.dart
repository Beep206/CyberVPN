import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/routing_settings_screen.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;

  @override
  Future<void> updateRoutingEnabled(bool enabled) async {
    _settings = _settings.copyWith(routingEnabled: enabled);
    state = AsyncData(_settings);
  }

  @override
  Future<void> upsertRoutingProfile(RoutingProfile profile) async {
    final updatedProfiles = [
      for (final existing in _settings.routingProfiles)
        if (existing.id != profile.id) existing,
      profile,
    ];
    _settings = _settings.copyWith(routingProfiles: updatedProfiles);
    state = AsyncData(_settings);
  }

  @override
  Future<void> removeRoutingProfile(String profileId) async {
    _settings = _settings.copyWith(
      routingProfiles: _settings.routingProfiles
          .where((profile) => profile.id != profileId)
          .toList(),
    );
    state = AsyncData(_settings);
  }

  @override
  Future<void> setActiveRoutingProfile(String? profileId) async {
    _settings = _settings.copyWith(activeRoutingProfileId: profileId);
    state = AsyncData(_settings);
  }
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
  required _FakeSettingsNotifier notifier,
  required VpnSettingsSupportMatrix supportMatrix,
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => notifier),
      vpnSettingsSupportMatrixProvider.overrideWithValue(supportMatrix),
    ],
    child: const MaterialApp(home: RoutingSettingsScreen()),
  );
}

void main() {
  group('RoutingSettingsScreen', () {
    testWidgets('toggles routing enabled state', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('toggle_routing_enabled')));
      await tester.pumpAndSettle();

      expect(notifier._settings.routingEnabled, isTrue);
    });

    testWidgets('creates a routing profile through dialog', (tester) async {
      final notifier = _FakeSettingsNotifier(
        const AppSettings(routingEnabled: true),
      );

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _androidSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('button_add_routing_profile')));
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('input_routing_profile_name')),
        'Streaming',
      );
      await tester.enterText(
        find.byKey(const Key('input_routing_rule_value_0')),
        'netflix.com',
      );
      await tester.tap(find.byKey(const Key('button_save_routing_profile')));
      await tester.pumpAndSettle();

      expect(notifier._settings.routingProfiles, hasLength(1));
      expect(notifier._settings.routingProfiles.first.name, 'Streaming');
      expect(notifier._settings.activeRoutingProfileId, isNotNull);
      expect(find.text('Streaming'), findsOneWidget);
    });

    testWidgets('shows excluded routes notice on iOS matrix', (tester) async {
      final notifier = _FakeSettingsNotifier();

      await tester.pumpWidget(
        _buildTestWidget(
          notifier: notifier,
          supportMatrix: _iosSupportMatrix(),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('routing_excluded_routes_notice')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('nav_routing_excluded_routes')),
        findsNothing,
      );
    });
  });
}
