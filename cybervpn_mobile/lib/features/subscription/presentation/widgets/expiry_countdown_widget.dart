import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';

/// Compact card showing days remaining until subscription expires.
///
/// Color coding:
/// - Green: > 30 days remaining
/// - Yellow: 7-30 days remaining
/// - Red: < 7 days remaining
///
/// Hidden when there is no active subscription or when the subscription
/// has no expiry (e.g. lifetime plans).
class ExpiryCountdownWidget extends ConsumerWidget {
  const ExpiryCountdownWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSub = ref.watch(subscriptionProvider);
    final subState = asyncSub.value;

    // Don't show if no subscription data or not active.
    if (subState == null || !subState.isActive) {
      return const SizedBox.shrink();
    }

    final days = subState.daysRemaining;

    // Hide for very long subscriptions (lifetime/unlimited).
    if (days > 365) return const SizedBox.shrink();

    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final color = _colorForDays(days);

    return Card(
      color: color.withValues(alpha: 0.15),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            // Colored dot indicator
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 12),

            // Days remaining text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    l10n.subscriptionDaysRemaining(days),
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: color,
                    ),
                  ),
                  if (days < 7)
                    Text(
                      l10n.subscriptionExpiringSoon,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),
            ),

            // Renew CTA when near expiry
            if (days < 30)
              FilledButton.tonal(
                onPressed: () => Navigator.of(context).pushNamed('/plans'),
                style: FilledButton.styleFrom(
                  backgroundColor: color.withValues(alpha: 0.2),
                  foregroundColor: color,
                ),
                child: Text(l10n.subscriptionRenewNow),
              ),
          ],
        ),
      ),
    );
  }

  Color _colorForDays(int days) {
    if (days > 30) return Colors.green;
    if (days >= 7) return Colors.orange;
    return Colors.red;
  }
}
