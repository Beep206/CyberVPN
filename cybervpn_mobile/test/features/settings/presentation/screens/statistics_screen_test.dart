import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/statistics_screen.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';

void main() {
  Widget buildScreen(VpnStatisticsOverview overview) {
    return ProviderScope(
      overrides: [vpnStatisticsOverviewProvider.overrideWithValue(overview)],
      child: const MaterialApp(home: StatisticsScreen()),
    );
  }

  testWidgets('renders aggregate statistics and unsupported split notices', (
    tester,
  ) async {
    await tester.pumpWidget(
      buildScreen(
        VpnStatisticsOverview(
          stats: ConnectionStatsEntity(
            serverName: 'Primary',
            protocol: 'vless',
            ipAddress: '1.2.3.4',
            sessionStartedAt: DateTime(2026, 4, 17, 12),
            connectionDuration: const Duration(minutes: 10),
            downloadSpeed: 2048,
            uploadSpeed: 1024,
            totalDownload: 4096,
            totalUpload: 2048,
          ),
          capabilities: const VpnStatisticsCapabilities(
            supportsSessionStartTime: true,
            supportsAggregateTraffic: true,
            supportsProxyTrafficSplit: false,
            supportsDirectTrafficSplit: false,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Session'), findsOneWidget);
    expect(find.text('Aggregate Runtime Counters'), findsOneWidget);
    expect(find.text('Primary'), findsOneWidget);
    expect(find.text('vless'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('stats_proxy_split_support')),
      300,
    );
    expect(find.byKey(const Key('stats_proxy_split_support')), findsOneWidget);
    expect(find.byKey(const Key('stats_direct_split_support')), findsOneWidget);
    expect(find.textContaining('Unsupported'), findsWidgets);
  });
}
