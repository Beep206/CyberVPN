import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// Circular progress ring widget showing usage with center text.
///
/// Displays a circular progress indicator with:
/// - Animated entrance: ring fills from 0% to actual value on first render
/// - Center text displaying current/total or custom text
/// - Optional subtitle text
/// - Theme-aware colors with customizable accent
///
/// The entrance animation plays once per widget lifetime (800ms,
/// easeOutCubic) and respects [MediaQuery.disableAnimations].
class UsageRing extends StatefulWidget {
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

  @override
  State<UsageRing> createState() => _UsageRingState();
}

class _UsageRingState extends State<UsageRing> {
  /// Whether the entrance animation has already played.
  /// Prevents re-animation on rebuilds (e.g. parent setState).
  bool _hasAnimated = false;

  /// Calculate usage ratio, clamped between 0.0 and 1.0.
  double get _ratio {
    if (widget.totalValue <= 0) return 0.0;
    return (widget.usedValue / widget.totalValue).clamp(0.0, 1.0);
  }

  /// Get default center text if none provided.
  String get _defaultCenterText {
    return '${widget.usedValue.toStringAsFixed(1)} / ${widget.totalValue.toStringAsFixed(0)}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final accent = widget.accentColor ?? colorScheme.primary;
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    // If accessibility disables animations, skip the entrance tween.
    final animateEntrance = !disableAnimations && !_hasAnimated;
    final beginValue = animateEntrance ? 0.0 : _ratio;

    return RepaintBoundary(
      child: TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: beginValue, end: _ratio),
        duration: animateEntrance
            ? const Duration(milliseconds: 800)
            : Duration.zero,
        curve: Curves.easeOutCubic,
        onEnd: () {
          if (!_hasAnimated) {
            _hasAnimated = true;
          }
        },
        builder: (context, animatedRatio, child) {
          return SizedBox(
            width: widget.size,
            height: widget.size,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Background ring
                SizedBox(
                  width: widget.size,
                  height: widget.size,
                  child: CircularProgressIndicator(
                    value: 1.0,
                    strokeWidth: widget.strokeWidth,
                    backgroundColor: Colors.transparent,
                    valueColor: AlwaysStoppedAnimation<Color>(
                      colorScheme.surfaceContainerHighest,
                    ),
                  ),
                ),

                // Animated progress ring
                SizedBox(
                  width: widget.size,
                  height: widget.size,
                  child: Transform.rotate(
                    angle: -math.pi / 2, // Start from top
                    child: CircularProgressIndicator(
                      value: animatedRatio,
                      strokeWidth: widget.strokeWidth,
                      backgroundColor: Colors.transparent,
                      valueColor: AlwaysStoppedAnimation<Color>(accent),
                    ),
                  ),
                ),

                // Center content (static, passed as child for performance)
                child!,
              ],
            ),
          );
        },
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Main text
            Text(
              widget.centerText ?? _defaultCenterText,
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),

            // Subtitle
            if (widget.subtitle != null) ...[
              const SizedBox(height: Spacing.xs),
              Text(
                widget.subtitle!,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
