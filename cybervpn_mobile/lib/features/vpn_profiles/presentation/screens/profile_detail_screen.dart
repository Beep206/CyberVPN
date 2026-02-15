import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_badge.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_card.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_progress_bar.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';

/// Detail view for a single VPN profile.
///
/// Shows:
/// - Subscription info card (traffic progress, expiry, update interval)
/// - Server list section
/// - Action buttons: Set Active, Update Now, Test URL, Delete
///
/// Currently renders with mock data until notifiers (UI-5) are wired.
class ProfileDetailScreen extends ConsumerWidget {
  const ProfileDetailScreen({
    super.key,
    required this.profileId,
  });

  final String profileId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    // TODO(ui-5): Replace with actual provider lookup
    final profile = _mockProfile();

    if (profile == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.profiles)),
        body: Center(child: Text(l10n.errorOccurred)),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: GlitchText(
          text: profile.name,
          style: theme.appBarTheme.titleTextStyle,
        ),
        actions: [
          if (profile is RemoteVpnProfile && profile.testUrl != null)
            IconButton(
              icon: const Icon(Icons.speed),
              tooltip: l10n.profileTestUrl,
              onPressed: () {
                // TODO(ui-5): Trigger URL test
              },
            ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.md,
          vertical: Spacing.sm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // --- Subscription info card ---
            if (profile is RemoteVpnProfile)
              _SubscriptionInfoCard(profile: profile),

            // --- Status section ---
            const SizedBox(height: Spacing.md),
            _StatusSection(profile: profile),

            // --- Server list ---
            const SizedBox(height: Spacing.md),
            _ServerListSection(servers: profile.servers),

            // --- Actions ---
            const SizedBox(height: Spacing.lg),
            _ActionButtons(profile: profile),

            SizedBox(height: Spacing.navBarClearance(context)),
          ],
        ),
      ),
    );
  }
}

/// Card showing subscription details: traffic, expiry, update interval.
class _SubscriptionInfoCard extends StatelessWidget {
  const _SubscriptionInfoCard({required this.profile});

  final RemoteVpnProfile profile;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    final usedBytes = profile.uploadBytes + profile.downloadBytes;
    final totalBytes = profile.totalBytes;
    final hasTrafficLimit = totalBytes > 0;
    final ratio = hasTrafficLimit
        ? (usedBytes / totalBytes).clamp(0.0, 1.0)
        : 0.0;

    final barColor = ratio > 0.9
        ? CyberColors.neonPink
        : ratio > 0.7
            ? Colors.amber
            : CyberColors.neonCyan;

    final isExpired = profile.expiresAt != null &&
        profile.expiresAt!.isBefore(DateTime.now());

    return CyberCard(
      color: isExpired ? CyberColors.neonPink : CyberColors.neonCyan,
      isAnimated: !isExpired,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Icon(
                Icons.cloud_outlined,
                size: 20,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: Spacing.sm),
              Text(
                l10n.profileRemote,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontFamily: 'Orbitron',
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              if (isExpired)
                CyberBadge(
                  label: l10n.profileExpired,
                  color: CyberColors.neonPink,
                  icon: Icons.error_outline,
                )
              else if (profile.isActive)
                CyberBadge(
                  label: l10n.profileActive,
                  color: CyberColors.matrixGreen,
                  icon: Icons.check_circle,
                ),
            ],
          ),

          // Traffic usage
          if (hasTrafficLimit) ...[
            const SizedBox(height: Spacing.md),
            CyberProgressBar(
              value: ratio,
              color: barColor,
              height: 4.0,
            ),
            const SizedBox(height: Spacing.xs),
            Text(
              l10n.profileTrafficUsed(
                DataFormatters.formatBytes(usedBytes),
                DataFormatters.formatBytes(totalBytes),
              ),
              style: theme.textTheme.bodySmall?.copyWith(
                fontFamily: 'JetBrains Mono',
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],

          // Expiry
          if (profile.expiresAt != null) ...[
            const SizedBox(height: Spacing.sm),
            Row(
              children: [
                Icon(
                  Icons.timer_outlined,
                  size: 16,
                  color: isExpired
                      ? CyberColors.neonPink
                      : theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: Spacing.xs),
                Text(
                  isExpired
                      ? l10n.profileExpiredOn(
                          DataFormatters.formatDate(profile.expiresAt!))
                      : l10n.profileExpiresIn(
                          profile.expiresAt!
                              .difference(DateTime.now())
                              .inDays),
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontFamily: 'JetBrains Mono',
                    color: isExpired
                        ? CyberColors.neonPink
                        : theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ],

          // Update interval
          const SizedBox(height: Spacing.xs),
          Text(
            l10n.profileUpdateInterval(
              profile.updateIntervalMinutes ~/ 60,
            ),
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),

          // Last updated
          if (profile.lastUpdatedAt != null) ...[
            const SizedBox(height: Spacing.xs),
            Text(
              l10n.profileLastUpdated(
                DataFormatters.formatDate(profile.lastUpdatedAt!),
              ),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Status section showing active state and profile type.
class _StatusSection extends StatelessWidget {
  const _StatusSection({required this.profile});

  final VpnProfile profile;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Row(
      children: [
        CyberBadge(
          label: profile is RemoteVpnProfile
              ? l10n.profileRemote
              : l10n.profileLocal,
          color: profile is RemoteVpnProfile
              ? CyberColors.neonCyan
              : CyberColors.neonPink,
          icon: profile is RemoteVpnProfile ? Icons.sync : Icons.storage,
        ),
        const SizedBox(width: Spacing.sm),
        Text(
          l10n.profileServers(profile.servers.length),
          style: theme.textTheme.bodyMedium?.copyWith(
            fontFamily: 'JetBrains Mono',
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

/// Section listing servers in this profile.
class _ServerListSection extends StatelessWidget {
  const _ServerListSection({required this.servers});

  final List<ProfileServer> servers;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    if (servers.isEmpty) {
      return CyberCard(
        color: CyberColors.neonCyan,
        isAnimated: false,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(Spacing.lg),
            child: Text(
              l10n.profileNoServers,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.servers,
          style: theme.textTheme.titleSmall?.copyWith(
            fontFamily: 'Orbitron',
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        ...servers.map((server) => _ServerTile(server: server)),
      ],
    );
  }
}

/// Individual server tile within the profile detail.
class _ServerTile extends StatelessWidget {
  const _ServerTile({required this.server});

  final ProfileServer server;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: Spacing.xs),
      child: CyberCard(
        color: CyberColors.neonCyan,
        isAnimated: false,
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.md,
          vertical: Spacing.sm,
        ),
        child: Row(
          children: [
            Icon(
              Icons.dns_outlined,
              size: 18,
              color: theme.colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: Spacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    server.name,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '${server.serverAddress}:${server.port}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontFamily: 'JetBrains Mono',
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            CyberBadge(
              label: server.protocol.name.toUpperCase(),
              color: CyberColors.neonCyan,
            ),
            if (server.latencyMs != null) ...[
              const SizedBox(width: Spacing.sm),
              Text(
                '${server.latencyMs}ms',
                style: theme.textTheme.bodySmall?.copyWith(
                  fontFamily: 'JetBrains Mono',
                  color: _latencyColor(server.latencyMs!, theme.colorScheme),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _latencyColor(int latency, ColorScheme colorScheme) {
    if (latency < 100) return CyberColors.matrixGreen;
    if (latency < 200) return Colors.amber;
    return CyberColors.neonPink;
  }
}

/// Action buttons at the bottom of the detail screen.
class _ActionButtons extends StatelessWidget {
  const _ActionButtons({required this.profile});

  final VpnProfile profile;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Set as Active
        if (!profile.isActive)
          FilledButton.icon(
            onPressed: () {
              // TODO(ui-5): Set profile as active via notifier
            },
            icon: const Icon(Icons.check_circle_outline),
            label: Text(l10n.profileSetActive),
          ),

        // Update Now (remote only)
        if (profile is RemoteVpnProfile) ...[
          const SizedBox(height: Spacing.sm),
          OutlinedButton.icon(
            onPressed: () {
              // TODO(ui-7): Trigger manual update
            },
            icon: const Icon(Icons.sync),
            label: Text(l10n.profileUpdateNow),
          ),
        ],

        // Delete
        const SizedBox(height: Spacing.md),
        TextButton.icon(
          onPressed: () => _showDeleteConfirmation(context),
          icon: Icon(Icons.delete_outline, color: theme.colorScheme.error),
          label: Text(
            l10n.profileDelete,
            style: TextStyle(color: theme.colorScheme.error),
          ),
        ),
      ],
    );
  }

  void _showDeleteConfirmation(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    unawaited(showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.profileDelete),
        content: Text(l10n.profileDeleteConfirm(profile.name)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(context).pop();
              // TODO(ui-5): Delete profile via notifier, then pop screen
            },
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: Text(l10n.confirm),
          ),
        ],
      ),
    ));
  }
}

// ---------------------------------------------------------------------------
// Mock data — will be removed once providers are wired (UI-5)
// ---------------------------------------------------------------------------

VpnProfile? _mockProfile() {
  final now = DateTime.now();
  return VpnProfile.remote(
    id: 'mock-1',
    name: 'CyberVPN Premium',
    subscriptionUrl: 'https://example.com/sub/abc123',
    isActive: true,
    sortOrder: 0,
    createdAt: now.subtract(const Duration(days: 30)),
    lastUpdatedAt: now.subtract(const Duration(hours: 2)),
    uploadBytes: 1024 * 1024 * 512,
    downloadBytes: 1024 * 1024 * 1024 * 3,
    totalBytes: 1024 * 1024 * 1024 * 50,
    expiresAt: now.add(const Duration(days: 25)),
    testUrl: 'https://example.com/test',
    servers: [],
  );
}
