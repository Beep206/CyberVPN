import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
  });

  /// The ID of the server to display.
  final String serverId;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Color _latencyColor(int? latency) {
    if (latency == null) return Colors.grey;
    if (latency < 100) return Colors.green;
    if (latency < 200) return Colors.orange;
    return Colors.red;
  }

  Color _loadColor(double load) {
    if (load < 0.5) return Colors.green;
    if (load < 0.7) return Colors.orange;
    return Colors.red;
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
      return Scaffold(
        appBar: AppBar(title: Text(l10n.serverSingle)),
        body: Center(child: Text(l10n.serverNotFound)),
      );
    }

    final load = (server.load ?? 0.0).clamp(0.0, 1.0);
    final loadPercent = (load * 100).toInt();

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
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // ----- Flag + Name Header (with Hero animation) -----
            FlagWidget(
              countryCode: server.countryCode,
              size: FlagSize.extraLarge,
              heroTag: 'server_flag_${server.id}',
            ),
            const SizedBox(height: 8),
            Text(
              server.name,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: colorScheme.onSurface,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            Text(
              '${server.city}, ${server.countryName}',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 24),

            // ----- Info Cards -----
            _InfoRow(
              icon: Icons.dns_outlined,
              label: l10n.serverDetailAddress,
              value: '${server.address}:${server.port}',
            ),
            const SizedBox(height: 12),

            // Protocol badge
            _InfoRow(
              icon: Icons.shield_outlined,
              label: l10n.serverDetailProtocol,
              trailing: _ProtocolChip(protocol: server.protocol),
            ),
            const SizedBox(height: 12),

            // Availability
            _InfoRow(
              icon: Icons.circle,
              iconColor: server.isAvailable ? Colors.green : Colors.red,
              iconSize: 12,
              label: l10n.serverDetailStatus,
              value: server.isAvailable ? l10n.serverDetailOnline : l10n.serverDetailOffline,
            ),
            const SizedBox(height: 12),

            // Premium
            if (server.isPremium)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
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
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                PingIndicator(latencyMs: server.ping),
                const SizedBox(width: 12),
                Text(
                  server.ping != null ? l10n.serverPingMs(server.ping!) : l10n.serverDetailNotTested,
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: _latencyColor(server.ping),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // ----- Load -----
            _SectionTitle(title: l10n.serverDetailServerLoad),
            const SizedBox(height: 8),
            Text(
              '$loadPercent%',
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: _loadColor(load),
              ),
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: load,
                minHeight: 10,
                backgroundColor: colorScheme.onSurface.withValues(alpha: 0.12),
                valueColor: AlwaysStoppedAnimation<Color>(_loadColor(load)),
              ),
            ),
            const SizedBox(height: 24),

            // ----- Uptime (estimated) -----
            _SectionTitle(title: l10n.serverDetailUptime),
            const SizedBox(height: 8),
            Text(
              server.isAvailable ? l10n.serverDetailUptimeValue : l10n.serverDetailUptimeNA,
              style: theme.textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: server.isAvailable
                    ? Colors.green
                    : colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 40),

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
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
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
        const SizedBox(width: 12),
        Text(
          label,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const Spacer(),
        if (trailing != null) trailing!,
        if (value != null)
          Text(
            value!,
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: colorScheme.onSurface,
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
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: colorScheme.tertiaryContainer,
        borderRadius: BorderRadius.circular(8),
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
