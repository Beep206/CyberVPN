import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/subscription_settings_screen.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/providers/profile_update_notifier.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

class _FakeProfileUpdateNotifier extends ProfileUpdateNotifier {
  _FakeProfileUpdateNotifier();

  @override
  ProfileUpdateState build() => const ProfileUpdateState();

  @override
  Future<Result<void>> updateSingle(String profileId) async {
    return const Success(null);
  }

  @override
  Future<Result<int>> refreshProfilesNow(Iterable<String> profileIds) async {
    return Success(profileIds.length);
  }
}

Future<void> _scrollDown(WidgetTester tester, [double offset = 700]) async {
  final listFinder = find.byType(ListView);
  expect(listFinder, findsOneWidget);
  await tester.drag(listFinder, Offset(0, -offset));
  await tester.pumpAndSettle();
}

Widget _buildTestWidget({
  List<ImportedConfig> importedConfigs = const <ImportedConfig>[],
  List<SubscriptionUrlMetadata> subscriptionMetadata =
      const <SubscriptionUrlMetadata>[],
  List<VpnProfile> profiles = const <VpnProfile>[],
  AppSettings settings = const AppSettings(),
}) {
  return ProviderScope(
    overrides: [
      importedConfigsProvider.overrideWithValue(importedConfigs),
      subscriptionUrlMetadataProvider.overrideWithValue(subscriptionMetadata),
      profileListProvider.overrideWith((ref) => Stream.value(profiles)),
      profileUpdateNotifierProvider.overrideWith(
        _FakeProfileUpdateNotifier.new,
      ),
      settingsProvider.overrideWith(() => _FakeSettingsNotifier(settings)),
    ],
    child: const MaterialApp(home: SubscriptionSettingsScreen()),
  );
}

void main() {
  group('SubscriptionSettingsScreen', () {
    testWidgets('renders subscription policy hub and billing entry points', (
      tester,
    ) async {
      await tester.pumpWidget(
        _buildTestWidget(
          settings: const AppSettings(
            subscriptionUserAgentMode: SubscriptionUserAgentMode.custom,
            subscriptionUserAgentValue: 'CyberVPN-Test/8.0',
            subscriptionSortMode: SubscriptionSortMode.alphabetical,
            collapseSubscriptions: false,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('summary_effective_user_agent')), findsOneWidget);
      expect(find.text('CyberVPN-Test/8.0'), findsOneWidget);
      expect(
        find.byKey(const Key('toggle_subscription_auto_update')),
        findsOneWidget,
      );
      await _scrollDown(tester);
      expect(
        find.byKey(const Key('dropdown_subscription_connect_strategy')),
        findsOneWidget,
      );
      await _scrollDown(tester);
      expect(
        find.byKey(const Key('dropdown_subscription_user_agent_mode')),
        findsOneWidget,
      );
      await _scrollDown(tester);
      await _scrollDown(tester);
      expect(find.byKey(const Key('nav_subscription_plans')), findsOneWidget);
      expect(
        find.byKey(const Key('nav_subscription_payment_history')),
        findsOneWidget,
      );
    });

    testWidgets('shows custom user-agent editor when custom mode is enabled', (
      tester,
    ) async {
      await tester.pumpWidget(
        _buildTestWidget(
          settings: const AppSettings(
            subscriptionUserAgentMode: SubscriptionUserAgentMode.custom,
            subscriptionUserAgentValue: 'CyberVPN-Test/8.0',
          ),
        ),
      );
      await tester.pumpAndSettle();
      await _scrollDown(tester);
      await _scrollDown(tester);

      expect(
        find.byKey(const Key('field_subscription_user_agent')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('button_save_subscription_user_agent')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('button_reset_subscription_user_agent')),
        findsOneWidget,
      );
    });

    testWidgets('renders provider profile cards with actions', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(
          profiles: [
            VpnProfile.remote(
              id: 'remote-1',
              name: 'Cyber Provider',
              subscriptionUrl: 'encrypted',
              isActive: true,
              sortOrder: 0,
              createdAt: DateTime(2026, 4, 16, 10),
              lastUpdatedAt: DateTime(2026, 4, 16, 12, 30),
              updateIntervalMinutes: 180,
              supportUrl: 'https://support.example.com',
              testUrl: 'https://provider.example.com',
              servers: const [],
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();
      await _scrollDown(tester, 1400);
      await tester.tap(find.byKey(const Key('toggle_provider_profiles_section')));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('provider_profile_remote-1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('button_refresh_profile_remote-1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('button_support_profile_remote-1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('button_provider_page_remote-1')),
        findsOneWidget,
      );
      expect(find.textContaining('stored encrypted at rest'), findsOneWidget);
    });

    testWidgets('renders provider metadata when subscription urls exist', (
      tester,
    ) async {
      await tester.pumpWidget(
        _buildTestWidget(
          importedConfigs: [
            ImportedConfig(
              id: 'cfg-1',
              name: 'Example',
              rawUri: 'vless://example',
              protocol: 'vless',
              serverAddress: 'example.com',
              port: 443,
              source: ImportSource.subscriptionUrl,
              subscriptionUrl: 'https://provider.example/sub',
              importedAt: DateTime(2026, 4, 16, 12, 30),
            ),
          ],
          subscriptionMetadata: [
            SubscriptionUrlMetadata(
              url: 'https://provider.example/sub',
              serverCount: 1,
              lastUpdated: DateTime(2026, 4, 16, 12, 30),
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();
      await _scrollDown(tester, 1800);
      await tester.tap(
        find.byKey(const Key('toggle_subscription_snapshots_section')),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(
          const Key('subscription_source_https://provider.example/sub'),
        ),
        findsOneWidget,
      );
      expect(find.textContaining('updated 2026-04-16 12:30'), findsOneWidget);
    });
  });
}
