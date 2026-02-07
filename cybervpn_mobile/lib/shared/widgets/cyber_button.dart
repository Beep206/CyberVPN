import 'dart:async';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A cyberpunk-themed button with animated neon border glow and press feedback.
///
/// The button continuously pulses with a subtle glow effect around its border,
/// and scales down briefly on press for tactile feedback. A [Material] ink
/// splash is rendered underneath the glow layer.
///
/// The glow animation is automatically disabled when
/// [MediaQuery.disableAnimations] is true.
///
/// Example:
/// ```dart
/// CyberButton(
///   onPressed: () => print('tapped'),
///   child: const Text('CONNECT'),
/// )
/// ```
class CyberButton extends StatefulWidget {
  const CyberButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.color = CyberColors.neonCyan,
    this.isLoading = false,
  });

  /// Callback invoked when the button is tapped. Ignored while [isLoading].
  final VoidCallback? onPressed;

  /// The content displayed inside the button.
  final Widget child;

  /// The neon color used for the border glow and ink splash.
  final Color color;

  /// When true, shows a loading indicator and disables interaction.
  final bool isLoading;

  @override
  State<CyberButton> createState() => _CyberButtonState();
}

class _CyberButtonState extends State<CyberButton>
    with SingleTickerProviderStateMixin {
  AnimationController? _glowController;
  late Animation<double> _glowAnimation;

  /// Tracks whether the button is currently pressed for the scale effect.
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _initGlowAnimation();
  }

  void _initGlowAnimation() {
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );

    _glowAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _glowController!, curve: Curves.easeInOut),
    );

    unawaited(_glowController!.repeat(reverse: true));
  }

  @override
  void dispose() {
    _glowController?.dispose();
    super.dispose();
  }

  void _handleTapDown(TapDownDetails _) {
    if (!_isInteractive) return;
    setState(() => _isPressed = true);
  }

  void _handleTapUp(TapUpDetails _) {
    setState(() => _isPressed = false);
  }

  void _handleTapCancel() {
    setState(() => _isPressed = false);
  }

  bool get _isInteractive =>
      widget.onPressed != null && !widget.isLoading;

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    // If animations are disabled, stop the controller and render a static glow.
    if (disableAnimations) {
      _glowController?.stop();
    } else if (_glowController != null && !_glowController!.isAnimating) {
      unawaited(_glowController!.repeat(reverse: true));
    }

    final double scale = _isPressed && !disableAnimations ? 0.95 : 1.0;

    return RepaintBoundary(
      child: GestureDetector(
        onTapDown: _handleTapDown,
        onTapUp: _handleTapUp,
        onTapCancel: _handleTapCancel,
        child: AnimatedScale(
          scale: scale,
          duration: AnimDurations.fast,
          curve: Curves.easeOut,
          child: _buildBody(disableAnimations),
        ),
      ),
    );
  }

  Widget _buildBody(bool disableAnimations) {
    if (disableAnimations) {
      return _buildContainer(glowValue: 0.5);
    }

    return _GlowBuilder(
      animation: _glowAnimation,
      builder: (context, _) {
        return _buildContainer(glowValue: _glowAnimation.value);
      },
    );
  }

  Widget _buildContainer({required double glowValue}) {
    // Interpolate blur and spread radius based on the glow pulse value.
    final double blurRadius = 6.0 + (glowValue * 8.0); // 6..14
    final double spreadRadius = 0.5 + (glowValue * 1.5); // 0.5..2.0
    final double borderOpacity = 0.6 + (glowValue * 0.4); // 0.6..1.0

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: widget.color.withValues(alpha: borderOpacity),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: widget.color.withValues(alpha: 0.25 + glowValue * 0.15),
            blurRadius: blurRadius,
            spreadRadius: spreadRadius,
          ),
        ],
      ),
      child: Material(
        color: CyberColors.deepNavy.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(Radii.md),
        child: InkWell(
          onTap: _isInteractive ? widget.onPressed : null,
          borderRadius: BorderRadius.circular(Radii.md),
          splashColor: widget.color.withValues(alpha: 0.2),
          highlightColor: widget.color.withValues(alpha: 0.08),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.lg,
              vertical: Spacing.md,
            ),
            child: Center(
              child: widget.isLoading
                  ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor:
                            AlwaysStoppedAnimation<Color>(widget.color),
                      ),
                    )
                  : DefaultTextStyle.merge(
                      style: TextStyle(
                        color: widget.color,
                        fontWeight: FontWeight.w600,
                        letterSpacing: AppTypography.labelLetterSpacing,
                      ),
                      child: IconTheme.merge(
                        data: IconThemeData(color: widget.color),
                        child: widget.child,
                      ),
                    ),
            ),
          ),
        ),
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
