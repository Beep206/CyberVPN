import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A cyberpunk-style glitch text widget that renders an RGB channel-split
/// animation effect.
///
/// When [isActive] is `true` (and the system has not requested reduced motion),
/// three copies of [text] are stacked with slight random pixel offsets: one
/// tinted red, one rendered as-is (green channel / original), and one tinted
/// blue.  The offsets are randomized every ~100 ms to produce a flickering
/// "glitch" aesthetic.
///
/// When [isActive] is `false` or [MediaQuery.disableAnimations] is `true`,
/// the widget falls back to a single plain [Text].
///
/// Wrapped in a [RepaintBoundary] so that the high-frequency repaints stay
/// isolated from the rest of the widget tree.
///
/// ```dart
/// GlitchText(
///   text: 'CYBER VPN',
///   style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
/// )
/// ```
class GlitchText extends StatefulWidget {
  const GlitchText({
    super.key,
    required this.text,
    this.style,
    this.isActive = true,
  });

  /// The string to render.
  final String text;

  /// Optional [TextStyle] applied to all three channel layers and to the
  /// plain-text fallback.  Color is overridden per layer when glitching.
  final TextStyle? style;

  /// Whether the glitch animation is running.  Defaults to `true`.
  final bool isActive;

  @override
  State<GlitchText> createState() => _GlitchTextState();
}

class _GlitchTextState extends State<GlitchText> {
  static const double _maxOffset = 2.0;
  static const Duration _interval = Duration(milliseconds: 100);

  final Random _rng = Random();

  Timer? _timer;

  /// Current pixel offsets for the red channel layer.
  double _redDx = 0;
  double _redDy = 0;

  /// Current pixel offsets for the blue channel layer.
  double _blueDx = 0;
  double _blueDy = 0;

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------

  @override
  void initState() {
    super.initState();
    // Timer is started lazily in didChangeDependencies where we can read
    // MediaQuery.
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncTimer();
  }

  @override
  void didUpdateWidget(covariant GlitchText oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isActive != widget.isActive) {
      _syncTimer();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _timer = null;
    super.dispose();
  }

  // ------------------------------------------------------------------
  // Timer management
  // ------------------------------------------------------------------

  /// Returns `true` when the animation should actually be running.
  bool get _shouldAnimate {
    if (!widget.isActive) return false;
    // Respect the system "reduce motion" / "disable animations" setting.
    final mq = MediaQuery.maybeOf(context);
    if (mq != null && mq.disableAnimations) return false;
    return true;
  }

  void _syncTimer() {
    if (_shouldAnimate) {
      _startTimer();
    } else {
      _stopTimer();
    }
  }

  void _startTimer() {
    if (_timer != null) return; // already running
    _timer = Timer.periodic(_interval, (_) => _randomizeOffsets());
    // Immediately show a glitch frame rather than waiting 100 ms.
    _randomizeOffsets();
  }

  void _stopTimer() {
    _timer?.cancel();
    _timer = null;
    // Reset offsets so the text sits cleanly when animation is off.
    if (_redDx != 0 || _redDy != 0 || _blueDx != 0 || _blueDy != 0) {
      setState(() {
        _redDx = 0;
        _redDy = 0;
        _blueDx = 0;
        _blueDy = 0;
      });
    }
  }

  /// Pick new random offsets in the range [-_maxOffset, _maxOffset].
  void _randomizeOffsets() {
    if (!mounted) return;
    setState(() {
      _redDx = _rng.nextDouble() * _maxOffset * 2 - _maxOffset;
      _redDy = _rng.nextDouble() * _maxOffset * 2 - _maxOffset;
      _blueDx = _rng.nextDouble() * _maxOffset * 2 - _maxOffset;
      _blueDy = _rng.nextDouble() * _maxOffset * 2 - _maxOffset;
    });
  }

  // ------------------------------------------------------------------
  // Build
  // ------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    // Fast path: no animation requested -- render plain text.
    if (!_shouldAnimate) {
      return RepaintBoundary(
        child: Text(
          widget.text,
          style: widget.style,
        ),
      );
    }

    final baseStyle = (widget.style ?? const TextStyle()).copyWith(
      // Ensure the base layer uses the neon cyan from the design system so it
      // reads well on dark backgrounds when no explicit color was provided.
      color: widget.style?.color ?? CyberColors.neonCyan,
    );

    return RepaintBoundary(
      child: Stack(
        children: [
          // --- Red channel layer ---
          Transform.translate(
            offset: Offset(_redDx, _redDy),
            child: Text(
              widget.text,
              style: baseStyle.copyWith(
                color: CyberColors.neonPink.withValues(alpha: 0.7),
              ),
            ),
          ),

          // --- Green / original layer (on top) ---
          Text(
            widget.text,
            style: baseStyle,
          ),

          // --- Blue channel layer ---
          Transform.translate(
            offset: Offset(_blueDx, _blueDy),
            child: Text(
              widget.text,
              style: baseStyle.copyWith(
                color: CyberColors.matrixGreen.withValues(alpha: 0.7),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
