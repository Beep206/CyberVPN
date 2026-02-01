import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// Stats card widget displaying an icon, label, and value with optional progress.
///
/// A card component that shows a statistic with:
/// - Icon in a colored background container
/// - Label text (small, muted)
/// - Value text (large, bold)
/// - Optional progress bar at the bottom
///
/// This widget is theme-aware and adapts to both light and dark cyberpunk themes.
class StatsCard extends StatelessWidget {
  /// Icon to display in the card.
  final IconData icon;

  /// Label text describing the stat (e.g., "Current Plan", "Traffic").
  final String label;

  /// Main value to display (e.g., "Active", "5.2 / 10 GB").
  final String value;

  /// Optional progress value between 0.0 and 1.0.
  /// When provided, displays a linear progress indicator.
  final double? progress;

  /// Optional accent color for icon and progress bar.
  /// Defaults to theme's primary color.
  final Color? accentColor;

  const StatsCard({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
    this.progress,
    this.accentColor,
  });

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
            // Icon row
            Container(
              padding: const EdgeInsets.all(Spacing.sm),
              decoration: BoxDecoration(
                color: accent.withAlpha(25),
                borderRadius: BorderRadius.circular(Radii.sm),
              ),
              child: Icon(icon, size: 20, color: accent),
            ),
            const SizedBox(height: Spacing.sm),

            // Label
            Text(
              label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.xs),

            // Value
            Text(
              value,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),

            // Optional progress bar
            if (progress != null) ...[
              const SizedBox(height: Spacing.sm),
              ClipRRect(
                borderRadius: BorderRadius.circular(Radii.sm),
                child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 4,
                  backgroundColor: colorScheme.surfaceContainerHighest,
                  valueColor: AlwaysStoppedAnimation<Color>(accent),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
