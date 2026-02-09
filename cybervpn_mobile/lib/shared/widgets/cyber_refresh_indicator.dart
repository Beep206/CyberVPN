import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A pull-to-refresh indicator that adapts to the active theme.
///
/// When the cyberpunk theme is active ([CyberColors.isCyberpunkTheme]),
/// it renders a neon ring spinner with a [CyberColors.matrixGreen] glow.
/// When the Material You theme is active, it delegates to the standard
/// Material [RefreshIndicator] using the current theme colors.
///
/// Haptic feedback is triggered when the user pulls past the refresh
/// threshold, providing a tactile signal that releasing will start
/// the refresh.
///
/// Usage:
/// ```dart
/// CyberRefreshIndicator(
///   onRefresh: () async {
///     await ref.read(serverListProvider.notifier).refresh();
///   },
///   child: CustomScrollView(slivers: [ ... ]),
/// )
/// ```
class CyberRefreshIndicator extends StatelessWidget {
  const CyberRefreshIndicator({
    super.key,
    required this.onRefresh,
    required this.child,
    this.color,
    this.displacement = 40.0,
    this.edgeOffset = 0.0,
  });

  /// Callback invoked when the user completes the pull-to-refresh gesture.
  final Future<void> Function() onRefresh;

  /// The scrollable content wrapped by this indicator.
  final Widget child;

  /// Override color for the indicator. If null, uses theme-appropriate
  /// defaults (matrixGreen for cyberpunk, primary for Material You).
  final Color? color;

  /// The distance from the top of the scroll view at which the indicator
  /// will settle during a refresh.
  final double displacement;

  /// The offset applied to the indicator when the scroll position is at
  /// the top edge (e.g., behind an app bar).
  final double edgeOffset;

  @override
  Widget build(BuildContext context) {
    final isCyberpunk = CyberColors.isCyberpunkTheme(context);

    if (!isCyberpunk) {
      // Material You: use the standard RefreshIndicator with theme colors.
      return RefreshIndicator(
        onRefresh: onRefresh,
        color: color ?? Theme.of(context).colorScheme.primary,
        backgroundColor: Theme.of(context).colorScheme.surface,
        displacement: displacement,
        edgeOffset: edgeOffset,
        child: child,
      );
    }

    // Cyberpunk theme: use the custom neon ring indicator.
    return _CyberRefreshIndicatorBody(
      onRefresh: onRefresh,
      color: color ?? CyberColors.matrixGreen,
      displacement: displacement,
      edgeOffset: edgeOffset,
      child: child,
    );
  }
}

// ---------------------------------------------------------------------------
// Cyberpunk implementation
// ---------------------------------------------------------------------------

class _CyberRefreshIndicatorBody extends StatefulWidget {
  const _CyberRefreshIndicatorBody({
    required this.onRefresh,
    required this.child,
    required this.color,
    required this.displacement,
    required this.edgeOffset,
  });

  final Future<void> Function() onRefresh;
  final Widget child;
  final Color color;
  final double displacement;
  final double edgeOffset;

  @override
  State<_CyberRefreshIndicatorBody> createState() =>
      _CyberRefreshIndicatorBodyState();
}

enum _RefreshState { idle, drag, armed, refreshing, done }

class _CyberRefreshIndicatorBodyState extends State<_CyberRefreshIndicatorBody>
    with TickerProviderStateMixin {
  _RefreshState _state = _RefreshState.idle;

  /// How far the user has dragged, in logical pixels.
  double _dragOffset = 0.0;

  /// The pull distance at which the refresh is triggered.
  static const double _triggerDistance = 100.0;

  /// Maximum drag distance for visual capping.
  static const double _maxDragDistance = 150.0;

  /// Whether haptic feedback has been fired for the current drag.
  bool _hapticFired = false;

  late final AnimationController _spinController;
  late final AnimationController _fadeController;

  @override
  void initState() {
    super.initState();
    _spinController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _fadeController = AnimationController(
      vsync: this,
      duration: AnimDurations.fast,
    );
  }

  @override
  void dispose() {
    _spinController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  // ---- Scroll notification handling ----

  bool _handleScrollNotification(ScrollNotification notification) {
    if (_state == _RefreshState.refreshing || _state == _RefreshState.done) {
      return false;
    }

    if (notification is ScrollStartNotification) {
      // Nothing special.
    } else if (notification is ScrollUpdateNotification) {
      _handleScrollUpdate(notification);
    } else if (notification is OverscrollNotification) {
      _handleOverscroll(notification);
    } else if (notification is ScrollEndNotification) {
      _handleScrollEnd();
    }
    return false;
  }

  void _handleScrollUpdate(ScrollUpdateNotification notification) {
    // Only react to overscroll at the top.
    if (notification.metrics.pixels < 0) {
      final overscroll = -notification.metrics.pixels;
      _updateDrag(overscroll);
    } else if (_state == _RefreshState.drag) {
      // The list scrolled back below the top; cancel the drag.
      _resetDrag();
    }
  }

  void _handleOverscroll(OverscrollNotification notification) {
    if (notification.overscroll < 0) {
      // Pulling down past the top.
      _updateDrag(_dragOffset + notification.overscroll.abs());
    }
  }

  void _updateDrag(double offset) {
    setState(() {
      _dragOffset = offset.clamp(0.0, _maxDragDistance);
      if (_dragOffset > 0 && _state == _RefreshState.idle) {
        _state = _RefreshState.drag;
        _fadeController.forward();
      }
      if (_dragOffset >= _triggerDistance && _state == _RefreshState.drag) {
        _state = _RefreshState.armed;
        if (!_hapticFired) {
          _hapticFired = true;
          unawaited(HapticFeedback.mediumImpact());
        }
      } else if (_dragOffset < _triggerDistance &&
          _state == _RefreshState.armed) {
        _state = _RefreshState.drag;
        _hapticFired = false;
      }
    });
  }

  void _handleScrollEnd() {
    if (_state == _RefreshState.armed) {
      _startRefresh();
    } else if (_state == _RefreshState.drag) {
      _resetDrag();
    }
  }

  void _startRefresh() {
    setState(() {
      _state = _RefreshState.refreshing;
      _dragOffset = widget.displacement + 20;
    });
    unawaited(_spinController.repeat());

    widget.onRefresh().whenComplete(() {
      if (!mounted) return;
      _spinController.stop();
      setState(() => _state = _RefreshState.done);
      _fadeController.reverse().whenComplete(() {
        if (!mounted) return;
        _resetDrag();
      });
    });
  }

  void _resetDrag() {
    setState(() {
      _state = _RefreshState.idle;
      _dragOffset = 0.0;
      _hapticFired = false;
    });
    _spinController.stop();
    _spinController.reset();
    _fadeController.reset();
  }

  // ---- Build ----

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    // The fractional pull progress from 0..1 used for indicator sizing.
    final pullProgress = (_dragOffset / _triggerDistance).clamp(0.0, 1.0);

    return NotificationListener<ScrollNotification>(
      onNotification: _handleScrollNotification,
      child: Stack(
        children: [
          widget.child,

          // Indicator overlay
          if (_state != _RefreshState.idle)
            Positioned(
              top:
                  widget.edgeOffset +
                  (_state == _RefreshState.refreshing ||
                          _state == _RefreshState.done
                      ? widget.displacement
                      : _dragOffset - 50),
              left: 0,
              right: 0,
              child: Center(
                child: FadeTransition(
                  opacity: _fadeController,
                  child: _CyberNeonRing(
                    color: widget.color,
                    size: 40.0,
                    pullProgress: pullProgress,
                    isRefreshing: _state == _RefreshState.refreshing,
                    spinAnimation: _spinController,
                    disableAnimations: disableAnimations,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Neon ring painter
// ---------------------------------------------------------------------------

/// A cyberpunk-themed neon ring that draws a glowing arc during pull
/// and spins during the refresh phase.
class _CyberNeonRing extends StatelessWidget {
  const _CyberNeonRing({
    required this.color,
    required this.size,
    required this.pullProgress,
    required this.isRefreshing,
    required this.spinAnimation,
    required this.disableAnimations,
  });

  final Color color;
  final double size;
  final double pullProgress;
  final bool isRefreshing;
  final Animation<double> spinAnimation;
  final bool disableAnimations;

  @override
  Widget build(BuildContext context) {
    // Scale up slightly as user pulls.
    final scale = 0.6 + (pullProgress * 0.4);

    return RepaintBoundary(
      child: Container(
        width: size + 16,
        height: size + 16,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: CyberEffects.neonGlow(
            color,
            intensity: pullProgress * 0.8,
          ),
        ),
        child: Transform.scale(
          scale: scale,
          child: isRefreshing && !disableAnimations
              ? AnimatedBuilder(
                  animation: spinAnimation,
                  builder: (context, child) {
                    return CustomPaint(
                      size: Size(size, size),
                      painter: _NeonRingPainter(
                        color: color,
                        sweepFraction: 0.75,
                        rotation: spinAnimation.value * 2 * math.pi,
                      ),
                    );
                  },
                )
              : CustomPaint(
                  size: Size(size, size),
                  painter: _NeonRingPainter(
                    color: color,
                    sweepFraction: pullProgress,
                    rotation: 0,
                  ),
                ),
        ),
      ),
    );
  }
}

class _NeonRingPainter extends CustomPainter {
  _NeonRingPainter({
    required this.color,
    required this.sweepFraction,
    required this.rotation,
  });

  final Color color;

  /// 0..1 how much of the ring to draw.
  final double sweepFraction;

  /// Rotation angle in radians.
  final double rotation;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 4;
    const strokeWidth = 3.0;

    // Track (dim ring).
    final trackPaint = Paint()
      ..color = color.withValues(alpha: 0.15)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, trackPaint);

    // Active arc.
    if (sweepFraction <= 0) return;

    final sweepAngle = sweepFraction * 2 * math.pi;
    final startAngle = -math.pi / 2 + rotation;

    // Glow layer (wider, transparent).
    final glowPaint = Paint()
      ..color = color.withValues(alpha: 0.3)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth + 4
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      glowPaint,
    );

    // Solid arc.
    final arcPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(_NeonRingPainter oldDelegate) {
    return oldDelegate.sweepFraction != sweepFraction ||
        oldDelegate.rotation != rotation ||
        oldDelegate.color != color;
  }
}
