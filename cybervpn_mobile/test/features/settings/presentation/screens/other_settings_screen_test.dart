import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/other_settings_screen.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
    : _settings = initial ?? const AppSettings();

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

void main() {
  Widget buildScreen() {
    return ProviderScope(
      overrides: [
        settingsProvider.overrideWith(_FakeSettingsNotifier.new),
        vpnStatisticsOverviewProvider.overrideWithValue(
          const VpnStatisticsOverview(
            stats: ConnectionStatsEntity(
              serverName: 'Primary',
              connectionDuration: Duration(minutes: 5),
            ),
            capabilities: VpnStatisticsCapabilities(
              supportsSessionStartTime: true,
              supportsAggregateTraffic: true,
              supportsProxyTrafficSplit: false,
              supportsDirectTrafficSplit: false,
            ),
          ),
        ),
        logFilesProvider.overrideWith(
          (ref) async => [
            PersistentLogFile(
              name: 'access_log.txt',
              path: '/tmp/access_log.txt',
              kind: PersistentLogFileKind.access,
              sizeBytes: 128,
              modifiedAt: DateTime(2026, 4, 17),
            ),
          ],
        ),
      ],
      child: const MaterialApp(home: OtherSettingsScreen()),
    );
  }

  testWidgets('renders Other Settings hub entries', (tester) async {
    await tester.pumpWidget(buildScreen());
    await tester.pumpAndSettle();

    expect(find.text('Operations'), findsOneWidget);
    expect(find.byKey(const Key('nav_other_statistics')), findsOneWidget);
    expect(find.byKey(const Key('nav_other_logs')), findsOneWidget);
    expect(find.byKey(const Key('nav_other_reset')), findsOneWidget);
    expect(find.textContaining('Primary'), findsOneWidget);
    expect(find.text('info • 1 persistent file(s)'), findsOneWidget);
  });
}
