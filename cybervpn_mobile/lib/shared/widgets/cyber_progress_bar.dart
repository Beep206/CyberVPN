import 'dart:async';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A cyberpunk-themed linear progress bar with a neon scan line effect.
///
/// The scan line sweeps across the filled portion of the bar, creating a
/// futuristic "scanning" appearance. The effect is achieved via a gradient
/// overlay that slides from left to right using an [AnimationController].
///
/// Example:
/// ```dart
/// CyberProgressBar(value: 0.65)
/// CyberProgressBar(value: downloadProgress, color: CyberColors.neonPink)
/// ```
class CyberProgressBar extends StatefulWidget {
  const CyberProgressBar({
    super.key,
    required this.value,
    this.color = CyberColors.neonCyan,
    this.height = 4.0,
    this.isAnimated = true,
  }) : assert(value >= 0.0 && value <= 1.0, 'value must be between 0.0 and 1.0');

  /// Progress value from 0.0 (empty) to 1.0 (full).
  final double value;

  /// The neon color used for the bar and scan effect.
  final Color color;

  /// Height of the progress bar in logical pixels.
  final double height;

  /// Whether to show the animated scan line effect.
  /// Even when true, the animation is disabled if
  /// [MediaQuery.disableAnimations] is set.
  final bool isAnimated;

  @override
  State<CyberProgressBar> createState() => _CyberProgressBarState();
}

class _CyberProgressBarState extends State<CyberProgressBar>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;

  @override
  void initState() {
    super.initState();
    if (widget.isAnimated) {
      _initController();
    }
  }

  void _initController() {
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    unawaited(_controller!.repeat());
  }

  @override
  void didUpdateWidget(CyberProgressBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isAnimated && _controller == null) {
      _initController();
    } else if (!widget.isAnimated && _controller != null) {
      _controller!.dispose();
      _controller = null;
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;
    final showScanEffect =
        widget.isAnimated && !disableAnimations && _controller != null;
    final borderRadius = BorderRadius.circular(Radii.xs);

    return RepaintBoundary(
      child: SizedBox(
        height: widget.height,
        child: ClipRRect(
          borderRadius: borderRadius,
          child: Stack(
            children: [
              // Background track
              Container(
                decoration: BoxDecoration(
                  color: widget.color.withValues(alpha: 0.15),
                  borderRadius: borderRadius,
                ),
              ),

              // Filled portion
              FractionallySizedBox(
                widthFactor: widget.value.clamp(0.0, 1.0),
                child: showScanEffect
                    ? _ScanFill(
                        animation: _controller!,
                        color: widget.color,
                        borderRadius: borderRadius,
                      )
                    : Container(
                        decoration: BoxDecoration(
                          color: widget.color,
                          borderRadius: borderRadius,
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Renders the filled bar with the sweeping scan-line gradient.
///
/// Isolated into its own [AnimatedWidget] so repaints are scoped to just the
/// gradient overlay, not the entire progress bar tree.
class _ScanFill extends AnimatedWidget {
  const _ScanFill({
    required Animation<double> animation,
    required this.color,
    required this.borderRadius,
  }) : super(listenable: animation);

  final Color color;
  final BorderRadius borderRadius;

  @override
  Widget build(BuildContext context) {
    final progress = (listenable as Animation<double>).value;

    // The highlight slides from -0.3 to 1.3 so it fully enters and exits
    // the bar rather than popping in/out at the edges.
    final scanCenter = -0.3 + (progress * 1.6);

    return Container(
      decoration: BoxDecoration(
        borderRadius: borderRadius,
        gradient: LinearGradient(
          colors: [
            color,
            color.withValues(alpha: 0.9),
            Colors.white.withValues(alpha: 0.35),
            color.withValues(alpha: 0.9),
            color,
          ],
          stops: [
            0.0,
            (scanCenter - 0.08).clamp(0.0, 1.0),
            scanCenter.clamp(0.0, 1.0),
            (scanCenter + 0.08).clamp(0.0, 1.0),
            1.0,
          ],
        ),
      ),
    );
  }
}
