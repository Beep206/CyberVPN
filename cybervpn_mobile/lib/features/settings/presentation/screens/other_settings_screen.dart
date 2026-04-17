import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/other_settings_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

class OtherSettingsScreen extends ConsumerWidget {
  const OtherSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overview = ref.watch(vpnStatisticsOverviewProvider);
    final logFilesAsync = ref.watch(logFilesProvider);
    final settings = ref.watch(settingsProvider).value ?? const AppSettings();

    final content = ListView(
      children: [
        SettingsSection(
          title: 'Operations',
          children: [
            SettingsTile.navigation(
              key: const Key('nav_other_statistics'),
              title: 'Statistics',
              subtitle: _statisticsSummary(overview),
              leading: const Icon(Icons.query_stats_outlined),
              onTap: () => context.push('/settings/other/statistics'),
            ),
            SettingsTile.navigation(
              key: const Key('nav_other_logs'),
              title: 'Logs',
              subtitle: _logsSummary(logFilesAsync, settings.logLevel.name),
              leading: const Icon(Icons.receipt_long_outlined),
              onTap: () => context.push('/settings/other/logs'),
            ),
            SettingsTile.navigation(
              key: const Key('nav_other_reset'),
              title: 'Reset',
              subtitle:
                  'Reset settings or wipe local app data with explicit confirmation.',
              leading: const Icon(Icons.restart_alt_outlined),
              onTap: () => context.push('/settings/other/reset'),
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
                'Phase 12 introduces an operational Other Settings hub. '
                'Statistics exposes supported runtime counters honestly, and Logs combines the live ring buffer with persistent files.',
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
      appBar: AppBar(title: const Text('Other Settings')),
      body: content,
    );
  }

  String _statisticsSummary(VpnStatisticsOverview overview) {
    final stats = overview.stats;
    if (stats == null) {
      return 'No active VPN session';
    }

    return '${stats.serverName ?? 'Connected'} • '
        '${DataFormatters.formatDuration(stats.connectionDuration)}';
  }

  String _logsSummary(AsyncValue<List<PersistentLogFile>> files, String level) {
    return files.when(
      data: (items) => '$level • ${items.length} persistent file(s)',
      loading: () => '$level • scanning files',
      error: (_, _) => '$level • file scan unavailable',
    );
  }
}
