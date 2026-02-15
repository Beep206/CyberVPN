import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/utils/data_formatters.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_badge.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_card.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_progress_bar.dart';

/// A card displaying a VPN profile summary in the profile list.
///
/// Shows the profile name, type badge (Remote/Local), server count,
/// traffic usage bar, active/expired status, and last-updated time.
/// Tapping the card navigates to the profile detail screen.
class ProfileCard extends StatelessWidget {
  const ProfileCard({
    super.key,
    required this.profile,
    this.onTap,
    this.onLongPress,
  });

  final VpnProfile profile;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final isActive = profile.isActive;
    final isExpired = _isExpired(profile);

    final glowColor = isActive
        ? CyberColors.matrixGreen
        : isExpired
            ? CyberColors.neonPink
            : CyberColors.neonCyan;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.xs,
      ),
      child: GestureDetector(
        onTap: onTap,
        onLongPress: onLongPress,
        child: CyberCard(
          color: glowColor,
          isAnimated: isActive,
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // --- Header row: name + badges ---
              Row(
                children: [
                  // Type icon
                  Icon(
                    _isRemote(profile) ? Icons.cloud_outlined : Icons.folder_outlined,
                    size: 20,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: Spacing.sm),

                  // Profile name
                  Expanded(
                    child: Text(
                      profile.name,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontFamily: 'Orbitron',
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: Spacing.sm),

                  // Type badge
                  CyberBadge(
                    label: _isRemote(profile) ? l10n.profileRemote : l10n.profileLocal,
                    color: _isRemote(profile) ? CyberColors.neonCyan : CyberColors.neonPink,
                    icon: _isRemote(profile) ? Icons.sync : Icons.storage,
                  ),
                ],
              ),

              const SizedBox(height: Spacing.sm),

              // --- Status row: active/expired + server count ---
              Row(
                children: [
                  if (isActive) ...[
                    _StatusChip(
                      label: l10n.profileActive,
                      color: CyberColors.matrixGreen,
                      icon: Icons.check_circle,
                    ),
                    const SizedBox(width: Spacing.sm),
                  ],
                  if (isExpired) ...[
                    _StatusChip(
                      label: l10n.profileExpired,
                      color: CyberColors.neonPink,
                      icon: Icons.error_outline,
                    ),
                    const SizedBox(width: Spacing.sm),
                  ],
                  Text(
                    l10n.profileServers(profile.servers.length),
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontFamily: 'JetBrains Mono',
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const Spacer(),
                  // Last updated
                  if (profile.lastUpdatedAt != null)
                    Text(
                      l10n.profileLastUpdated(
                        _formatRelativeTime(profile.lastUpdatedAt!),
                      ),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),

              // --- Traffic bar (remote profiles only) ---
              if (profile is RemoteVpnProfile) ...[
                const SizedBox(height: Spacing.sm),
                _TrafficSection(profile: profile as RemoteVpnProfile, l10n: l10n),
              ],

              // --- Expiry info ---
              if (_expiryText(profile, l10n) != null) ...[
                const SizedBox(height: Spacing.xs),
                Text(
                  _expiryText(profile, l10n)!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    fontFamily: 'JetBrains Mono',
                    color: isExpired
                        ? CyberColors.neonPink
                        : theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  bool _isRemote(VpnProfile profile) => profile is RemoteVpnProfile;

  bool _isExpired(VpnProfile profile) {
    if (profile is RemoteVpnProfile) {
      final expiresAt = profile.expiresAt;
      return expiresAt != null && expiresAt.isBefore(DateTime.now());
    }
    return false;
  }

  String? _expiryText(VpnProfile profile, AppLocalizations l10n) {
    if (profile is! RemoteVpnProfile) return null;
    final expiresAt = profile.expiresAt;
    if (expiresAt == null) return null;

    if (expiresAt.isBefore(DateTime.now())) {
      return l10n.profileExpiredOn(DataFormatters.formatDate(expiresAt));
    }
    final days = expiresAt.difference(DateTime.now()).inDays;
    if (days <= 30) {
      return l10n.profileExpiresIn(days);
    }
    return null;
  }

  static String _formatRelativeTime(DateTime dateTime) {
    final diff = DateTime.now().difference(dateTime);
    if (diff.inMinutes < 1) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

/// Traffic usage section with progress bar and text.
class _TrafficSection extends StatelessWidget {
  const _TrafficSection({
    required this.profile,
    required this.l10n,
  });

  final RemoteVpnProfile profile;
  final AppLocalizations l10n;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final totalBytes = profile.totalBytes;
    if (totalBytes <= 0) return const SizedBox.shrink();

    final usedBytes = profile.uploadBytes + profile.downloadBytes;
    final ratio = totalBytes > 0
        ? (usedBytes / totalBytes).clamp(0.0, 1.0)
        : 0.0;

    final barColor = ratio > 0.9
        ? CyberColors.neonPink
        : ratio > 0.7
            ? Colors.amber
            : CyberColors.neonCyan;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CyberProgressBar(
          value: ratio,
          color: barColor,
          height: 3.0,
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
    );
  }
}

/// Small inline status chip for Active/Expired indicators.
class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.color,
    required this.icon,
  });

  final String label;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(Radii.xs),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 3),
          Text(
            label,
            style: TextStyle(
              fontFamily: 'JetBrains Mono',
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: color,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}
