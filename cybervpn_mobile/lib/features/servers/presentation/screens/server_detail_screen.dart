import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/ping_indicator.dart';
import 'package:cybervpn_mobile/shared/widgets/flag_widget.dart';

/// Full-screen detail view for a single VPN server.
///
/// Shows:
/// - Country flag + server name header
/// - City + provider info
/// - Supported protocol badge
/// - Current load with LinearProgressIndicator
/// - Uptime percentage (estimated)
/// - Average latency with color
/// - Large "Connect" button
class ServerDetailScreen extends ConsumerWidget {
  const ServerDetailScreen({
    super.key,
    required this.serverId,
    this.embedded = false,
  });

  /// The ID of the server to display.
  final String serverId;

  /// When `true`, renders without a Scaffold/AppBar so it can be embedded
  /// in a master-detail layout.
  final bool embedded;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Color _latencyColor(int? latency, ColorScheme colorScheme) {
    if (latency == null) return colorScheme.outline;
    if (latency < 100) return colorScheme.tertiary;
    if (latency < 200) return Colors.orange;
    return colorScheme.error;
  }

  Color _loadColor(double load, ColorScheme colorScheme) {
    if (load < 0.5) return colorScheme.tertiary;
    if (load < 0.7) return Colors.orange;
    return colorScheme.error;
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final server = ref.watch(serverByIdProvider(serverId));
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final l10n = AppLocalizations.of(context);

    if (server == null) {
      if (embedded) {
        return Center(child: Text(l10n.serverNotFound));
      }
      return Scaffold(
        appBar: AppBar(title: Text(l10n.serverSingle)),
        body: Center(child: Text(l10n.serverNotFound)),
      );
    }

    final load = (server.load ?? 0.0).clamp(0.0, 1.0);
    final loadPercent = (load * 100).toInt();

    final body = SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: Spacing.lg, vertical: Spacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // ----- Flag + Name Header (with Hero animation) -----
            FlagWidget(
              countryCode: server.countryCode,
              size: FlagSize.extraLarge,
              heroTag: 'server_flag_${server.id}',
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              server.name,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: Spacing.xs),
            Text(
              '${server.city}, ${server.countryName}',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: Spacing.lg),

            // ----- Info Cards -----
            _InfoRow(
              icon: Icons.dns_outlined,
              label: l10n.serverDetailAddress,
              value: '${server.address}:${server.port}',
            ),
            const SizedBox(height: Spacing.sm),

            // Protocol badge
            _InfoRow(
              icon: Icons.shield_outlined,
              label: l10n.serverDetailProtocol,
              trailing: _ProtocolChip(protocol: server.protocol),
            ),
            const SizedBox(height: Spacing.sm),

            // Availability
            _InfoRow(
              icon: Icons.circle,
              iconColor: server.isAvailable ? colorScheme.tertiary : colorScheme.error,
              iconSize: 12,
              label: l10n.serverDetailStatus,
              value: server.isAvailable ? l10n.serverDetailOnline : l10n.serverDetailOffline,
            ),
            const SizedBox(height: Spacing.sm),

            // Premium
            if (server.isPremium)
              Padding(
                padding: const EdgeInsets.only(bottom: Spacing.sm),
                child: _InfoRow(
                  icon: Icons.workspace_premium,
                  iconColor: Colors.amber.shade600,
                  label: l10n.serverDetailTier,
                  value: l10n.serverDetailPremium,
                ),
              ),

            const Divider(height: 32),

            // ----- Latency -----
            _SectionTitle(title: l10n.serverDetailLatency),
            const SizedBox(height: Spacing.sm),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                PingIndicator(latencyMs: server.ping),
                const SizedBox(width: Spacing.sm),
                Text(
                  server.ping != null ? l10n.serverPingMs(server.ping!) : l10n.serverDetailNotTested,
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: _latencyColor(server.ping, colorScheme),
                  ),
                ),
              ],
            ),
            const SizedBox(height: Spacing.lg),

            // ----- Load -----
            _SectionTitle(title: l10n.serverDetailServerLoad),
            const SizedBox(height: Spacing.sm),
            Text(
              '$loadPercent%',
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: _loadColor(load, colorScheme),
              ),
            ),
            const SizedBox(height: Spacing.sm),
            ClipRRect(
              borderRadius: BorderRadius.circular(Radii.xs),
              child: LinearProgressIndicator(
                value: load,
                minHeight: 10,
                backgroundColor: colorScheme.onSurface.withValues(alpha: 0.12),
                valueColor: AlwaysStoppedAnimation<Color>(_loadColor(load, colorScheme)),
              ),
            ),
            const SizedBox(height: Spacing.lg),

            // ----- Uptime (estimated) -----
            _SectionTitle(title: l10n.serverDetailUptime),
            const SizedBox(height: Spacing.sm),
            Text(
              server.isAvailable ? l10n.serverDetailUptimeValue : l10n.serverDetailUptimeNA,
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: server.isAvailable
                    ? colorScheme.tertiary
                    : colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.xl + Spacing.sm),

            // ----- Connect Button -----
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton.icon(
                onPressed: server.isAvailable
                    ? () {
                        // Navigate back with server ID to signal connection.
                        Navigator.of(context).pop(server.id);
                      }
                    : null,
                icon: const Icon(Icons.power_settings_new, size: 24),
                label: Text(
                  server.isAvailable ? l10n.connect : l10n.serverDetailUnavailable,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: colorScheme.primary,
                  foregroundColor: colorScheme.onPrimary,
                  disabledBackgroundColor:
                      colorScheme.onSurface.withValues(alpha: 0.12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(Radii.lg),
                  ),
                ),
              ),
            ),
            const SizedBox(height: Spacing.xl),
          ],
        ),
      );

    if (embedded) return body;


    return Scaffold(
      appBar: AppBar(
        title: Text(server.name),
        actions: [
          IconButton(
            icon: Icon(
              server.isFavorite ? Icons.star : Icons.star_border,
              color: server.isFavorite ? Colors.amber : null,
            ),
            onPressed: () {
              unawaited(ref.read(serverListProvider.notifier).toggleFavorite(server.id));
            },
          ),
        ],
      ),
      body: body,
    );
  }
}

// ---------------------------------------------------------------------------
// Private helper widgets
// ---------------------------------------------------------------------------

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: AlignmentDirectional.centerStart,
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.label,
    this.value,
    this.trailing,
    this.iconColor,
    this.iconSize,
  });

  final IconData icon;
  final String label;
  final String? value;
  final Widget? trailing;
  final Color? iconColor;
  final double? iconSize;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Row(
      children: [
        Icon(icon,
            size: iconSize ?? 20,
            color: iconColor ?? colorScheme.onSurfaceVariant),
        const SizedBox(width: Spacing.sm),
        Text(
          label,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const Spacer(),
        if (trailing != null) trailing!,
        if (value != null)
          Flexible(
            child: Text(
              value!,
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
                color: colorScheme.onSurface,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
      ],
    );
  }
}

class _ProtocolChip extends StatelessWidget {
  const _ProtocolChip({required this.protocol});
  final String protocol;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.sm + 2, vertical: Spacing.xs),
      decoration: BoxDecoration(
        color: colorScheme.tertiaryContainer,
        borderRadius: BorderRadius.circular(Radii.sm),
      ),
      child: Text(
        protocol.toUpperCase(),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: colorScheme.onTertiaryContainer,
        ),
      ),
    );
  }
}
