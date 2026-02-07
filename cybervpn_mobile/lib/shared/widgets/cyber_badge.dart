import 'dart:async';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A cyberpunk-themed badge/chip with a pulsing neon glow.
///
/// Displays a [label] inside a rounded container with a colored border and a
/// subtle [BoxShadow] that pulses between low and high opacity, producing a
/// neon "breathing" effect. An optional [icon] is rendered before the label.
///
/// Example:
/// ```dart
/// CyberBadge(label: 'ONLINE')
/// CyberBadge(label: 'PRO', color: CyberColors.neonCyan, icon: Icons.star)
/// CyberBadge(label: 'SECURE', color: CyberColors.neonPink)
/// ```
class CyberBadge extends StatefulWidget {
  const CyberBadge({
    super.key,
    required this.label,
    this.color = CyberColors.matrixGreen,
    this.icon,
  });

  /// Text displayed inside the badge.
  final String label;

  /// The neon color used for the border, glow, and text.
  final Color color;

  /// Optional icon rendered before the label.
  final IconData? icon;

  @override
  State<CyberBadge> createState() => _CyberBadgeState();
}

class _CyberBadgeState extends State<CyberBadge>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1800),
      vsync: this,
    );
    unawaited(_controller!.repeat(reverse: true));
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    if (disableAnimations) {
      return RepaintBoundary(
        child: _BadgeContent(
          label: widget.label,
          color: widget.color,
          icon: widget.icon,
          glowOpacity: 0.5,
        ),
      );
    }

    return RepaintBoundary(
      child: _PulsingBadge(
        animation: _controller!,
        label: widget.label,
        color: widget.color,
        icon: widget.icon,
      ),
    );
  }
}

/// Rebuilds only when the animation ticks, keeping the pulse scoped to this
/// subtree and avoiding repaints of ancestor widgets.
class _PulsingBadge extends AnimatedWidget {
  const _PulsingBadge({
    required Animation<double> animation,
    required this.label,
    required this.color,
    this.icon,
  }) : super(listenable: animation);

  final String label;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final progress = (listenable as Animation<double>).value;
    // Pulse glow opacity between 0.3 and 0.7.
    final glowOpacity = 0.3 + (progress * 0.4);

    return _BadgeContent(
      label: label,
      color: color,
      icon: icon,
      glowOpacity: glowOpacity,
    );
  }
}

/// The visual content of the badge, shared by both the static and animated
/// variants.
class _BadgeContent extends StatelessWidget {
  const _BadgeContent({
    required this.label,
    required this.color,
    required this.glowOpacity,
    this.icon,
  });

  final String label;
  final Color color;
  final IconData? icon;
  final double glowOpacity;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.sm,
        vertical: Spacing.xs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(Radii.sm),
        border: Border.all(
          color: color.withValues(alpha: 0.8),
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: glowOpacity),
            blurRadius: 8.0,
            spreadRadius: 0.0,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: color),
            const SizedBox(width: Spacing.xs),
          ],
          Text(
            label,
            style: AppTypography.label(fontFamily: 'JetBrains Mono').copyWith(
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
