import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// Circular progress ring widget showing usage with center text.
///
/// Displays a circular progress indicator with:
/// - Circular progress ring showing usage ratio
/// - Center text displaying current/total or custom text
/// - Optional subtitle text
/// - Theme-aware colors with customizable accent
///
/// Useful for displaying traffic usage, storage usage, or any ratio-based metric.
class UsageRing extends StatelessWidget {
  /// Current usage value (e.g., bytes used, items consumed).
  final double usedValue;

  /// Total/limit value (e.g., total bytes, max items).
  final double totalValue;

  /// Optional custom center text override.
  /// If null, displays "usedValue / totalValue".
  final String? centerText;

  /// Optional subtitle text below the main center text.
  final String? subtitle;

  /// Optional accent color for the progress ring.
  /// Defaults to theme's primary color.
  final Color? accentColor;

  /// Size of the ring (diameter). Defaults to 160.
  final double size;

  /// Stroke width of the progress ring. Defaults to 12.
  final double strokeWidth;

  const UsageRing({
    super.key,
    required this.usedValue,
    required this.totalValue,
    this.centerText,
    this.subtitle,
    this.accentColor,
    this.size = 160,
    this.strokeWidth = 12,
  });

  /// Calculate usage ratio, clamped between 0.0 and 1.0.
  double get _ratio {
    if (totalValue <= 0) return 0.0;
    return (usedValue / totalValue).clamp(0.0, 1.0);
  }

  /// Get default center text if none provided.
  String get _defaultCenterText {
    return '${usedValue.toStringAsFixed(1)} / ${totalValue.toStringAsFixed(0)}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final accent = accentColor ?? colorScheme.primary;

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Background ring
          SizedBox(
            width: size,
            height: size,
            child: CircularProgressIndicator(
              value: 1.0,
              strokeWidth: strokeWidth,
              backgroundColor: Colors.transparent,
              valueColor: AlwaysStoppedAnimation<Color>(
                colorScheme.surfaceContainerHighest,
              ),
            ),
          ),

          // Progress ring
          SizedBox(
            width: size,
            height: size,
            child: Transform.rotate(
              angle: -math.pi / 2, // Start from top
              child: CircularProgressIndicator(
                value: _ratio,
                strokeWidth: strokeWidth,
                backgroundColor: Colors.transparent,
                valueColor: AlwaysStoppedAnimation<Color>(accent),
              ),
            ),
          ),

          // Center content
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Main text
              Text(
                centerText ?? _defaultCenterText,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),

              // Subtitle
              if (subtitle != null) ...[
                const SizedBox(height: Spacing.xs),
                Text(
                  subtitle!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
