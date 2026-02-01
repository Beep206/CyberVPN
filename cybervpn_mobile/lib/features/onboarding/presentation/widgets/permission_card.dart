import 'package:flutter/material.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A card displaying a permission request explanation.
///
/// Shows an icon, title, description, and visual indicator for the
/// permission grant status (pending, granted, or processing).
class PermissionCard extends StatelessWidget {
  const PermissionCard({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
    this.isGranted = false,
    this.isProcessing = false,
  });

  /// Icon representing the permission type.
  final IconData icon;

  /// Title of the permission (e.g., 'VPN Connection').
  final String title;

  /// Explanation of why this permission is needed.
  final String description;

  /// Whether the permission has been granted.
  final bool isGranted;

  /// Whether a permission request is currently in progress.
  final bool isProcessing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainer,
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: isGranted
              ? colorScheme.primary
              : colorScheme.outline.withAlpha(80),
          width: isGranted ? 2 : 1,
        ),
      ),
      child: Row(
        children: [
          // Icon container
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isGranted
                  ? colorScheme.primary.withAlpha(30)
                  : colorScheme.surfaceContainerHighest,
            ),
            child: Icon(
              icon,
              size: 28,
              color: isGranted ? colorScheme.primary : colorScheme.onSurface,
            ),
          ),
          const SizedBox(width: Spacing.md),

          // Text content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: Spacing.xs),
                Text(
                  description,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: Spacing.sm),

          // Status indicator
          if (isProcessing)
            SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: colorScheme.primary,
              ),
            )
          else if (isGranted)
            Icon(
              Icons.check_circle,
              color: colorScheme.primary,
              size: 24,
            )
          else
            Icon(
              Icons.circle_outlined,
              color: colorScheme.outline,
              size: 24,
            ),
        ],
      ),
    );
  }
}
