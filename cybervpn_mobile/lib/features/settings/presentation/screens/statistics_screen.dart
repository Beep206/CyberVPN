import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

class StatisticsScreen extends ConsumerWidget {
  const StatisticsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overview = ref.watch(vpnStatisticsOverviewProvider);
    final content = ListView(
      children: [
        SettingsSection(
          title: 'Session',
          children: [
            SettingsTile.info(
              key: const Key('stats_server_name'),
              title: 'Server',
              subtitle: overview.stats?.serverName ?? 'No active server',
              leading: const Icon(Icons.dns_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_protocol'),
              title: 'Protocol',
              subtitle: overview.stats?.protocol ?? 'Unavailable',
              leading: const Icon(Icons.shield_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_endpoint'),
              title: 'Endpoint',
              subtitle: overview.stats?.ipAddress ?? 'Unavailable',
              leading: const Icon(Icons.language_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_started_at'),
              title: 'Server Session Start',
              subtitle: _formatSessionStart(overview),
              leading: const Icon(Icons.schedule_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_duration'),
              title: 'VPN Connection Duration',
              subtitle: DataFormatters.formatDuration(
                overview.stats?.connectionDuration ?? Duration.zero,
              ),
              leading: const Icon(Icons.timer_outlined),
            ),
          ],
        ),
        SettingsSection(
          title: 'Aggregate Runtime Counters',
          children: [
            SettingsTile.info(
              key: const Key('stats_aggregate_download_speed'),
              title: 'Incoming Speed',
              subtitle: _formatSpeed(overview.stats?.downloadSpeed ?? 0),
              leading: const Icon(Icons.south_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_aggregate_upload_speed'),
              title: 'Outgoing Speed',
              subtitle: _formatSpeed(overview.stats?.uploadSpeed ?? 0),
              leading: const Icon(Icons.north_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_aggregate_download_traffic'),
              title: 'Incoming Traffic',
              subtitle: DataFormatters.formatBytes(
                overview.stats?.totalDownload ?? 0,
              ),
              leading: const Icon(Icons.download_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_aggregate_upload_traffic'),
              title: 'Outgoing Traffic',
              subtitle: DataFormatters.formatBytes(
                overview.stats?.totalUpload ?? 0,
              ),
              leading: const Icon(Icons.upload_outlined),
            ),
          ],
        ),
        SettingsSection(
          title: 'Happ Split Metrics',
          children: [
            SettingsTile.info(
              key: const Key('stats_proxy_split_support'),
              title: 'Proxy Traffic Split',
              subtitle: overview.capabilities.supportsProxyTrafficSplit
                  ? 'Supported'
                  : 'Unsupported: current mobile runtime exposes aggregate counters only.',
              leading: const Icon(Icons.compare_arrows_outlined),
            ),
            SettingsTile.info(
              key: const Key('stats_direct_split_support'),
              title: 'Direct Traffic Split',
              subtitle: overview.capabilities.supportsDirectTrafficSplit
                  ? 'Supported'
                  : 'Unsupported: current mobile runtime does not report direct in/out traffic separately.',
              leading: const Icon(Icons.alt_route_outlined),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Spacing.md,
            Spacing.sm,
            Spacing.md,
            Spacing.lg,
          ),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(Radii.lg),
            ),
            child: const Padding(
              padding: EdgeInsets.all(Spacing.md),
              child: Text(
                'Current Android/iOS runtime reports aggregate Xray counters. '
                'Phase 12 surfaces those counters directly and marks proxy/direct split metrics as unsupported instead of inferring them.',
              ),
            ),
          ),
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );

    if (embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Statistics')),
      body: content,
    );
  }

  String _formatSessionStart(VpnStatisticsOverview overview) {
    final startedAt = overview.stats?.sessionStartedAt;
    if (startedAt == null) {
      return overview.capabilities.supportsSessionStartTime
          ? 'No active session'
          : 'Unsupported';
    }

    return DataFormatters.formatDate(startedAt.toLocal());
  }

  String _formatSpeed(int bytesPerSecond) {
    return DataFormatters.formatSpeed(bytesPerSecond.toDouble());
  }
}
