import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';

// ---------------------------------------------------------------------------
// Plan card widget
// ---------------------------------------------------------------------------

/// Displays a single subscription plan as a material card.
///
/// Shows the plan name, tag chip (e.g. "Popular"), feature list, price
/// with optional discount strikethrough, duration pills, and a Subscribe
/// or "Current Plan" button.
class PlanCard extends StatelessWidget {
  const PlanCard({
    super.key,
    required this.plan,
    required this.selectedDuration,
    this.isCurrentPlan = false,
    this.onSubscribe,
    this.originalPrice,
  });

  /// The plan to display.
  final PlanEntity plan;

  /// The currently selected duration (for price display context).
  final PlanDuration selectedDuration;

  /// Whether the user is already subscribed to this plan.
  final bool isCurrentPlan;

  /// Called when the user taps the "Subscribe" button.
  final VoidCallback? onSubscribe;

  /// Original price before discount, if any. Shows as strikethrough.
  final double? originalPrice;

  // ---- Tag helpers --------------------------------------------------------

  String? get _tagLabel {
    if (plan.isPopular) return 'Popular';
    if (plan.duration == PlanDuration.yearly) return 'Best Value';
    if (plan.isTrial) return 'Free Trial';
    return null;
  }

  Color _tagColor(ColorScheme colorScheme) {
    if (plan.isPopular) return colorScheme.tertiary;
    if (plan.duration == PlanDuration.yearly) return colorScheme.secondary;
    if (plan.isTrial) return colorScheme.primary;
    return colorScheme.tertiary;
  }

  bool get _isRecommended => plan.isPopular;

  // ---- Feature list -------------------------------------------------------

  List<String> get _featureLines {
    final lines = <String>[];

    // Traffic limit.
    if (plan.trafficLimitGb > 0) {
      lines.add('${plan.trafficLimitGb} GB traffic');
    } else {
      lines.add('Unlimited traffic');
    }

    // Device count.
    lines.add('Up to ${plan.maxDevices} device${plan.maxDevices > 1 ? 's' : ''}');

    // Extra features from the entity.
    if (plan.features != null) {
      lines.addAll(plan.features!);
    }

    return lines;
  }

  // ---- Build --------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final tag = _tagLabel;

    return Card(
      elevation: _isRecommended ? 4 : 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: _isRecommended
            ? BorderSide(color: colorScheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header row: name + tag chip ──────────────────────────
            Row(
              children: [
                Expanded(
                  child: Text(
                    plan.name,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                if (tag != null)
                  Chip(
                    label: Text(
                      tag,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: colorScheme.onPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    backgroundColor: _tagColor(colorScheme),
                    padding: EdgeInsets.zero,
                    visualDensity: VisualDensity.compact,
                    side: BorderSide.none,
                  ),
              ],
            ),

            if (plan.description.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                plan.description,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],

            const SizedBox(height: 16),

            // ── Feature list ─────────────────────────────────────────
            ..._featureLines.map(
              (feature) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      size: 18,
                      color: colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        feature,
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // ── Price display ────────────────────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (originalPrice != null && originalPrice! > plan.price) ...[
                  Text(
                    '${plan.currency} ${originalPrice!.toStringAsFixed(2)}',
                    style: theme.textTheme.bodyLarge?.copyWith(
                      decoration: TextDecoration.lineThrough,
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(width: 8),
                ],
                Text(
                  '${plan.currency} ${plan.price.toStringAsFixed(2)}',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 4),
                Padding(
                  padding: const EdgeInsets.only(bottom: 2),
                  child: Text(
                    '/ ${_durationLabel(plan.duration)}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),

            // ── Duration pills ───────────────────────────────────────
            Wrap(
              spacing: 6,
              children: [
                _DurationPill(
                  label: '${plan.durationDays}d',
                  isSelected: plan.duration == selectedDuration,
                ),
              ],
            ),

            const SizedBox(height: 16),

            // ── Action button ────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: isCurrentPlan
                  ? OutlinedButton.icon(
                      onPressed: null,
                      icon: const Icon(Icons.check),
                      label: const Text('Current Plan'),
                    )
                  : FilledButton(
                      onPressed: onSubscribe,
                      child: Text(
                        plan.isTrial ? 'Start Free Trial' : 'Subscribe',
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  static String _durationLabel(PlanDuration duration) {
    switch (duration) {
      case PlanDuration.monthly:
        return 'month';
      case PlanDuration.quarterly:
        return '3 months';
      case PlanDuration.yearly:
        return 'year';
      case PlanDuration.lifetime:
        return 'lifetime';
    }
  }
}

// ---------------------------------------------------------------------------
// Duration pill chip
// ---------------------------------------------------------------------------

class _DurationPill extends StatelessWidget {
  const _DurationPill({
    required this.label,
    required this.isSelected,
  });

  final String label;
  final bool isSelected;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: isSelected
            ? colorScheme.primaryContainer
            : colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
        border: isSelected
            ? Border.all(color: colorScheme.primary, width: 1.5)
            : null,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              color: isSelected
                  ? colorScheme.onPrimaryContainer
                  : colorScheme.onSurfaceVariant,
            ),
      ),
    );
  }
}
