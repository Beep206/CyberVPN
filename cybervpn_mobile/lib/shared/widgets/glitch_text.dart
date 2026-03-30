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
  static const Duration _frameInterval = Duration(milliseconds: 140);
  static const Duration _burstDuration = Duration(milliseconds: 420);
  static const Duration _idleDuration = Duration(milliseconds: 2200);

  final Random _rng = Random();

  Timer? _frameTimer;
  Timer? _cycleTimer;

  /// Current pixel offsets for the red channel layer.
  double _redDx = 0;
  double _redDy = 0;

  /// Current pixel offsets for the blue channel layer.
  double _blueDx = 0;
  double _blueDy = 0;

  bool _isBursting = false;

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
    _cancelTimers();
    super.dispose();
  }

  // ------------------------------------------------------------------
  // Timer management
  // ------------------------------------------------------------------

  /// Returns `true` when the animation should actually be running.
  bool get _shouldAnimate {
    if (!widget.isActive) return false;
    // Only animate in the cyberpunk theme; render plain text in Material You.
    if (!CyberColors.isCyberpunkTheme(context)) return false;
    // Pause the effect when this subtree is tick-disabled (inactive route/tab).
    // ignore: deprecated_member_use
    if (!TickerMode.getNotifier(context).value) return false;
    // Respect the system "reduce motion" / "disable animations" setting.
    final mq = MediaQuery.maybeOf(context);
    if (mq != null && mq.disableAnimations) return false;
    return true;
  }

  void _syncTimer() {
    if (_shouldAnimate) {
      _ensureBurstScheduled();
    } else {
      _stopTimer();
    }
  }

  void _ensureBurstScheduled() {
    if (_frameTimer != null || _cycleTimer != null) {
      return;
    }

    _startBurst();
  }

  void _startBurst() {
    if (!_shouldAnimate) {
      _stopTimer();
      return;
    }

    _frameTimer?.cancel();
    _isBursting = true;
    _frameTimer = Timer.periodic(_frameInterval, (_) => _randomizeOffsets());
    _randomizeOffsets();

    _cycleTimer?.cancel();
    _cycleTimer = Timer(_burstDuration, () {
      _frameTimer?.cancel();
      _frameTimer = null;
      _isBursting = false;
      _resetOffsets();

      if (!_shouldAnimate) {
        _cycleTimer = null;
        return;
      }

      _cycleTimer = Timer(_idleDuration, _startBurst);
    });
  }

  void _stopTimer() {
    _cancelTimers();
    _resetOffsets();
  }

  void _cancelTimers() {
    _frameTimer?.cancel();
    _cycleTimer?.cancel();
    _frameTimer = null;
    _cycleTimer = null;
    _isBursting = false;
  }

  void _resetOffsets() {
    if (_redDx == 0 && _redDy == 0 && _blueDx == 0 && _blueDy == 0) {
      return;
    }

    setState(() {
      _redDx = 0;
      _redDy = 0;
      _blueDx = 0;
      _blueDy = 0;
    });
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
    if (!_shouldAnimate || !_isBursting) {
      return RepaintBoundary(child: Text(widget.text, style: widget.style));
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
          Text(widget.text, style: baseStyle),

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
