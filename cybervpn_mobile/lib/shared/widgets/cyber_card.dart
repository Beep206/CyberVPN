import 'dart:async';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A cyberpunk-themed card with an animated glowing border.
///
/// The border subtly pulses between low and high glow intensity using a
/// [BoxShadow] driven by an [AnimationController]. The animation is
/// automatically skipped when [MediaQuery.disableAnimations] is true, or
/// when [isAnimated] is set to false.
///
/// Example:
/// ```dart
/// CyberCard(
///   child: Column(
///     children: [
///       Text('Server Status', style: theme.textTheme.titleMedium),
///       Text('Online'),
///     ],
///   ),
/// )
/// ```
class CyberCard extends StatefulWidget {
  const CyberCard({
    super.key,
    required this.child,
    this.color = CyberColors.matrixGreen,
    this.padding,
    this.isAnimated = true,
  });

  /// The content displayed inside the card.
  final Widget child;

  /// The neon color used for the border and glow effect.
  final Color color;

  /// Inner padding of the card. Defaults to [Spacing.md] on all sides.
  final EdgeInsetsGeometry? padding;

  /// Whether the border glow should animate. When false, a static glow is
  /// rendered regardless of the accessibility setting.
  final bool isAnimated;

  @override
  State<CyberCard> createState() => _CyberCardState();
}

class _CyberCardState extends State<CyberCard>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    if (widget.isAnimated) {
      _initAnimation();
    }
  }

  void _initAnimation() {
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    );

    _glowAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller!, curve: Curves.easeInOut),
    );

    unawaited(_controller!.repeat(reverse: true));
  }

  @override
  void didUpdateWidget(CyberCard oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (widget.isAnimated && _controller == null) {
      _initAnimation();
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
    final shouldAnimate =
        widget.isAnimated && !disableAnimations && _controller != null;

    // Pause or resume the controller based on accessibility.
    if (widget.isAnimated && _controller != null) {
      if (disableAnimations && _controller!.isAnimating) {
        _controller!.stop();
      } else if (!disableAnimations && !_controller!.isAnimating) {
        unawaited(_controller!.repeat(reverse: true));
      }
    }

    if (!shouldAnimate) {
      return RepaintBoundary(
        child: _buildCard(glowValue: 0.3),
      );
    }

    return RepaintBoundary(
      child: _GlowBuilder(
        animation: _glowAnimation,
        builder: (context, _) => _buildCard(glowValue: _glowAnimation.value),
      ),
    );
  }

  Widget _buildCard({required double glowValue}) {
    final double blurRadius = 4.0 + (glowValue * 6.0); // 4..10
    final double spreadRadius = 0.0 + (glowValue * 1.0); // 0..1
    final double borderOpacity = 0.3 + (glowValue * 0.35); // 0.3..0.65

    return DecoratedBox(
      decoration: BoxDecoration(
        color: CyberColors.deepNavy.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: widget.color.withValues(alpha: borderOpacity),
          width: 1.0,
        ),
        boxShadow: [
          BoxShadow(
            color: widget.color.withValues(alpha: 0.12 + glowValue * 0.10),
            blurRadius: blurRadius,
            spreadRadius: spreadRadius,
          ),
        ],
      ),
      child: Padding(
        padding: widget.padding ?? const EdgeInsets.all(Spacing.md),
        child: widget.child,
      ),
    );
  }
}

/// Private [AnimatedWidget] wrapper that rebuilds on each animation tick.
class _GlowBuilder extends AnimatedWidget {
  const _GlowBuilder({
    required Animation<double> animation,
    required this.builder,
  }) : super(listenable: animation);

  final Widget Function(BuildContext context, Widget? child) builder;

  @override
  Widget build(BuildContext context) => builder(context, null);
}
