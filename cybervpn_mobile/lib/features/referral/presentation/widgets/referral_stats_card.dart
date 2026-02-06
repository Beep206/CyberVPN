import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/referral/domain/entities/referral.dart';

// ---------------------------------------------------------------------------
// ReferralStatsCard
// ---------------------------------------------------------------------------

/// Displays a 2x2 grid of referral statistics cards.
///
/// Shows: total invited, paid users, points earned, and current balance.
class ReferralStatsCard extends StatelessWidget {
  const ReferralStatsCard({
    super.key,
    required this.stats,
  });

  final ReferralStats stats;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    final cards = <_StatItem>[
      _StatItem(
        key: const Key('stat_total_invited'),
        icon: Icons.group_outlined,
        label: l10n.referralStatsTotalInvited,
        value: '${stats.totalInvited}',
        accentColor: CyberColors.neonCyan,
      ),
      _StatItem(
        key: const Key('stat_paid_users'),
        icon: Icons.verified_outlined,
        label: l10n.referralStatsPaidUsers,
        value: '${stats.paidUsers}',
        accentColor: CyberColors.matrixGreen,
      ),
      _StatItem(
        key: const Key('stat_points'),
        icon: Icons.stars_outlined,
        label: l10n.referralStatsPoints,
        value: stats.pointsEarned.toStringAsFixed(0),
        accentColor: const Color(0xFFFFAB40),
      ),
      _StatItem(
        key: const Key('stat_balance'),
        icon: Icons.account_balance_wallet_outlined,
        label: l10n.referralStatsBalance,
        value: '\$${stats.balance.toStringAsFixed(2)}',
        accentColor: CyberColors.neonPink,
      ),
    ];

    return Wrap(
      spacing: Spacing.sm,
      runSpacing: Spacing.sm,
      children: cards.map((item) {
        return SizedBox(
          width: (MediaQuery.sizeOf(context).width -
                  Spacing.md * 2 -
                  Spacing.sm) /
              2,
          child: item,
        );
      }).toList(),
    );
  }
}

// ---------------------------------------------------------------------------
// _StatItem (private)
// ---------------------------------------------------------------------------

class _StatItem extends StatelessWidget {
  const _StatItem({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
    this.accentColor,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final accent = accentColor ?? colorScheme.primary;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(Spacing.sm),
              decoration: BoxDecoration(
                color: accent.withAlpha(25),
                borderRadius: BorderRadius.circular(Radii.sm),
              ),
              child: Icon(icon, size: 20, color: accent),
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.xs),
            Text(
              value,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
