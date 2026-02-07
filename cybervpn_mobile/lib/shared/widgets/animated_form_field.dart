import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// Wraps a [TextFormField] with animated focus effects: border color
/// transition and a subtle scale bump when the field gains focus.
///
/// The animation is suppressed when the platform accessibility setting
/// [MediaQuery.disableAnimations] is active.
class AnimatedFormField extends StatefulWidget {
  const AnimatedFormField({
    super.key,
    required this.child,
  });

  /// The form field widget to wrap.
  final Widget child;

  @override
  State<AnimatedFormField> createState() => _AnimatedFormFieldState();
}

class _AnimatedFormFieldState extends State<AnimatedFormField> {
  bool _focused = false;

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;
    final scale = (!disableAnimations && _focused) ? 1.01 : 1.0;

    return Focus(
      onFocusChange: (hasFocus) => setState(() => _focused = hasFocus),
      child: AnimatedScale(
        scale: scale,
        duration: AnimDurations.fast,
        curve: Curves.easeOut,
        child: widget.child,
      ),
    );
  }
}

/// A widget that shakes its child horizontally to indicate a validation error.
///
/// Trigger by changing [shake] from `false` to `true`. The animation runs
/// once (3 cycles, ~300ms) and then stops.
class ShakeWidget extends StatefulWidget {
  const ShakeWidget({
    super.key,
    required this.child,
    this.shake = false,
    this.amplitude = 5.0,
    this.cycles = 3,
    this.duration = AnimDurations.normal,
  });

  final Widget child;

  /// Set to `true` to trigger the shake animation.
  final bool shake;

  /// Maximum horizontal displacement in logical pixels.
  final double amplitude;

  /// Number of oscillation cycles.
  final int cycles;

  /// Total duration of the shake.
  final Duration duration;

  @override
  State<ShakeWidget> createState() => _ShakeWidgetState();
}

class _ShakeWidgetState extends State<ShakeWidget>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _offsetAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: widget.duration);

    // Oscillate: 0 → amplitude → -amplitude → ... → 0
    _offsetAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.elasticIn),
    );
  }

  @override
  void didUpdateWidget(covariant ShakeWidget old) {
    super.didUpdateWidget(old);
    if (widget.shake && !old.shake) {
      if (!MediaQuery.of(context).disableAnimations) {
        _controller.forward(from: 0);
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _offsetAnimation,
      builder: (context, child) {
        final progress = _offsetAnimation.value;
        // Use sin to oscillate: progress goes 0→1, we want `cycles` full waves.
        final sineValue =
            (progress * widget.cycles * 2 * 3.14159).sinApprox();
        final offset = sineValue * widget.amplitude * (1 - progress);
        return Transform.translate(
          offset: Offset(offset, 0),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}

extension _SinApprox on double {
  /// Fast sine approximation using Taylor series (3 terms).
  double sinApprox() {
    double x = this % (2 * 3.14159265);
    if (x > 3.14159265) x -= 2 * 3.14159265;
    if (x < -3.14159265) x += 2 * 3.14159265;
    final x3 = x * x * x;
    final x5 = x3 * x * x;
    return x - x3 / 6 + x5 / 120;
  }
}

/// A brief green checkmark animation shown on form submission success.
///
/// Fades in, scales up, holds briefly, then fades out.
class SuccessCheckmark extends StatefulWidget {
  const SuccessCheckmark({
    super.key,
    this.size = 48.0,
    this.onComplete,
  });

  final double size;
  final VoidCallback? onComplete;

  @override
  State<SuccessCheckmark> createState() => _SuccessCheckmarkState();
}

class _SuccessCheckmarkState extends State<SuccessCheckmark>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scaleAnimation;
  late final Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    _scaleAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.2), weight: 30),
      TweenSequenceItem(tween: Tween(begin: 1.2, end: 1.0), weight: 20),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.0), weight: 30),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.8), weight: 20),
    ]).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));

    _opacityAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 20),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.0), weight: 50),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.0), weight: 30),
    ]).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));

    _controller.forward().whenComplete(() => widget.onComplete?.call());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) => Opacity(
        opacity: _opacityAnimation.value,
        child: Transform.scale(
          scale: _scaleAnimation.value,
          child: Icon(
            Icons.check_circle,
            size: widget.size,
            color: Theme.of(context).colorScheme.tertiary,
          ),
        ),
      ),
    );
  }
}
