import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';

// ---------------------------------------------------------------------------
// PartnerStatsCard
// ---------------------------------------------------------------------------

/// Displays a 2x3 grid of partner statistics cards.
///
/// Shows: tier, client count, total earnings, available balance,
/// commission rate, and partner since date.
class PartnerStatsCard extends StatelessWidget {
  const PartnerStatsCard({
    super.key,
    required this.info,
  });

  final PartnerInfo info;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    final cards = <_StatItem>[
      _StatItem(
        key: const Key('stat_tier'),
        icon: Icons.military_tech_outlined,
        label: l10n.partnerTier,
        value: _tierLabel(info.tier),
        accentColor: _tierColor(info.tier),
      ),
      _StatItem(
        key: const Key('stat_clients'),
        icon: Icons.group_outlined,
        label: l10n.partnerClients,
        value: '${info.clientCount}',
        accentColor: CyberColors.neonCyan,
      ),
      _StatItem(
        key: const Key('stat_total_earnings'),
        icon: Icons.account_balance_wallet_outlined,
        label: l10n.partnerTotalEarnings,
        value: '\$${info.totalEarnings.toStringAsFixed(2)}',
        accentColor: CyberColors.matrixGreen,
      ),
      _StatItem(
        key: const Key('stat_available_balance'),
        icon: Icons.payments_outlined,
        label: l10n.partnerAvailableBalance,
        value: '\$${info.availableBalance.toStringAsFixed(2)}',
        accentColor: CyberColors.neonPink,
      ),
      _StatItem(
        key: const Key('stat_commission_rate'),
        icon: Icons.percent_outlined,
        label: l10n.partnerCommissionRate,
        value: '${info.commissionRate.toStringAsFixed(1)}%',
        accentColor: const Color(0xFFFFAB40),
      ),
      _StatItem(
        key: const Key('stat_partner_since'),
        icon: Icons.calendar_today_outlined,
        label: l10n.partnerSince,
        value: _formatDate(info.partnerSince),
        accentColor: const Color(0xFF7E57C2),
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

  String _tierLabel(PartnerTier tier) {
    return switch (tier) {
      PartnerTier.bronze => 'Bronze',
      PartnerTier.silver => 'Silver',
      PartnerTier.gold => 'Gold',
    };
  }

  Color _tierColor(PartnerTier tier) {
    return switch (tier) {
      PartnerTier.bronze => const Color(0xFFCD7F32),
      PartnerTier.silver => const Color(0xFFC0C0C0),
      PartnerTier.gold => const Color(0xFFFFD700),
    };
  }

  String _formatDate(DateTime date) {
    return '${date.month}/${date.year}';
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
