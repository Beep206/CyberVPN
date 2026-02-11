import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/partner/domain/entities/partner.dart';

// ---------------------------------------------------------------------------
// EarningsListItem
// ---------------------------------------------------------------------------

/// Displays a single earnings record in a list.
///
/// Shows the amount, period, and transaction count.
class EarningsListItem extends StatelessWidget {
  const EarningsListItem({
    super.key,
    required this.earnings,
  });

  final Earnings earnings;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      margin: const EdgeInsets.only(bottom: Spacing.sm),
      child: ListTile(
        leading: Container(
          padding: const EdgeInsets.all(Spacing.sm),
          decoration: BoxDecoration(
            color: CyberColors.matrixGreen.withAlpha(25),
            borderRadius: BorderRadius.circular(Radii.sm),
          ),
          child: const Icon(
            Icons.attach_money_outlined,
            color: CyberColors.matrixGreen,
            size: 24,
          ),
        ),
        title: Text(
          earnings.period,
          style: theme.textTheme.bodyLarge?.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
        subtitle: Text(
          l10n.partnerTransactionCount(earnings.transactionCount),
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        trailing: Text(
          '\$${earnings.amount.toStringAsFixed(2)}',
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
            color: CyberColors.matrixGreen,
          ),
        ),
      ),
    );
  }
}
