import 'dart:async';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A cyberpunk-themed horizontal divider with an animated neon shimmer.
///
/// The line uses a transparent-to-color-to-transparent gradient to create a
/// subtle "energy conduit" effect. An optional shimmer highlight sweeps
/// across the line for additional visual flair.
///
/// Example:
/// ```dart
/// const CyberDivider()
/// CyberDivider(color: CyberColors.neonPink, thickness: 2)
/// CyberDivider(indent: 16, endIndent: 16)
/// ```
class CyberDivider extends StatefulWidget {
  const CyberDivider({
    super.key,
    this.color = CyberColors.neonCyan,
    this.thickness = 1.0,
    this.indent = 0.0,
    this.endIndent = 0.0,
  });

  /// The neon color of the divider line.
  final Color color;

  /// Thickness of the divider in logical pixels.
  final double thickness;

  /// Empty space to the leading edge of the divider.
  final double indent;

  /// Empty space to the trailing edge of the divider.
  final double endIndent;

  @override
  State<CyberDivider> createState() => _CyberDividerState();
}

class _CyberDividerState extends State<CyberDivider>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 2500),
      vsync: this,
    );
    unawaited(_controller!.repeat());
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    return RepaintBoundary(
      child: Padding(
        padding: EdgeInsetsDirectional.only(
          start: widget.indent,
          end: widget.endIndent,
        ),
        child: disableAnimations
            ? _StaticLine(
                color: widget.color,
                thickness: widget.thickness,
              )
            : _AnimatedLine(
                animation: _controller!,
                color: widget.color,
                thickness: widget.thickness,
              ),
      ),
    );
  }
}

/// The static (non-animated) version of the divider.
///
/// Rendered when the user has animations disabled via accessibility settings.
class _StaticLine extends StatelessWidget {
  const _StaticLine({
    required this.color,
    required this.thickness,
  });

  final Color color;
  final double thickness;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: thickness,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              color.withValues(alpha: 0.0),
              color.withValues(alpha: 0.6),
              color,
              color.withValues(alpha: 0.6),
              color.withValues(alpha: 0.0),
            ],
            stops: const [0.0, 0.25, 0.5, 0.75, 1.0],
          ),
        ),
      ),
    );
  }
}

/// The animated version with a shimmer highlight that sweeps along the line.
class _AnimatedLine extends AnimatedWidget {
  const _AnimatedLine({
    required Animation<double> animation,
    required this.color,
    required this.thickness,
  }) : super(listenable: animation);

  final Color color;
  final double thickness;

  @override
  Widget build(BuildContext context) {
    final progress = (listenable as Animation<double>).value;

    // Shimmer highlight travels from -0.2 to 1.2 so it enters/exits smoothly.
    final shimmerCenter = -0.2 + (progress * 1.4);

    return SizedBox(
      height: thickness,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              color.withValues(alpha: 0.0),
              color.withValues(alpha: 0.5),
              // Shimmer highlight blended on top of the base gradient
              Colors.white.withValues(alpha: 0.5),
              color.withValues(alpha: 0.5),
              color.withValues(alpha: 0.0),
            ],
            stops: [
              0.0,
              (shimmerCenter - 0.06).clamp(0.0, 1.0),
              shimmerCenter.clamp(0.0, 1.0),
              (shimmerCenter + 0.06).clamp(0.0, 1.0),
              1.0,
            ],
          ),
        ),
      ),
    );
  }
}
