import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';

class VpnStatisticsCapabilities {
  const VpnStatisticsCapabilities({
    required this.supportsSessionStartTime,
    required this.supportsAggregateTraffic,
    required this.supportsProxyTrafficSplit,
    required this.supportsDirectTrafficSplit,
  });

  final bool supportsSessionStartTime;
  final bool supportsAggregateTraffic;
  final bool supportsProxyTrafficSplit;
  final bool supportsDirectTrafficSplit;
}

class VpnStatisticsOverview {
  const VpnStatisticsOverview({
    required this.capabilities,
    this.stats,
  });

  final ConnectionStatsEntity? stats;
  final VpnStatisticsCapabilities capabilities;
}

final vpnStatisticsOverviewProvider = Provider<VpnStatisticsOverview>((ref) {
  final stats = ref.watch(vpnStatsProvider);
  return VpnStatisticsOverview(
    stats: stats,
    capabilities: const VpnStatisticsCapabilities(
      supportsSessionStartTime: true,
      supportsAggregateTraffic: true,
      supportsProxyTrafficSplit: false,
      supportsDirectTrafficSplit: false,
    ),
  );
});

final logFilesProvider = FutureProvider.autoDispose<List<PersistentLogFile>>((
  ref,
) async {
  return ref.watch(logFileStoreProvider).listFiles();
});

final logFileContentsProvider = FutureProvider.autoDispose.family<String, String>(
  (ref, path) async {
    return ref.watch(logFileStoreProvider).readFile(path);
  },
);
