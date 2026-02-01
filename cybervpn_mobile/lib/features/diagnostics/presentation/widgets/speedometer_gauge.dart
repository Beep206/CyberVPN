import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

// ---------------------------------------------------------------------------
// SpeedometerGauge
// ---------------------------------------------------------------------------

/// An animated speedometer gauge that displays the current network speed.
///
/// The gauge draws a 240-degree arc with tick marks, a glow-effect needle,
/// and a centered speed readout. The needle animates smoothly between speed
/// values using an internal [AnimationController].
///
/// Uses cyberpunk color tokens: matrix green for high speeds, neon pink for
/// low speeds, with a gradient transition between them.
class SpeedometerGauge extends StatefulWidget {
  const SpeedometerGauge({
    super.key,
    required this.speed,
    this.maxSpeed = 100.0,
    this.label = 'Mbps',
    this.animationDuration = const Duration(milliseconds: 800),
    this.size,
  });

  /// Current speed value to display (0 to [maxSpeed]).
  final double speed;

  /// Maximum speed on the gauge scale.
  final double maxSpeed;

  /// Unit label displayed below the speed value.
  final String label;

  /// Duration for the needle animation when speed changes.
  final Duration animationDuration;

  /// Optional explicit size. If null, the widget sizes itself based on
  /// available space via [LayoutBuilder].
  final double? size;

  @override
  State<SpeedometerGauge> createState() => SpeedometerGaugeState();
}

class SpeedometerGaugeState extends State<SpeedometerGauge>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;
  double _previousSpeed = 0.0;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.animationDuration,
    );
    _animation = Tween<double>(begin: 0.0, end: _clamp(widget.speed))
        .animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));
    _controller.forward();
  }

  @override
  void didUpdateWidget(covariant SpeedometerGauge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.speed != widget.speed) {
      _previousSpeed = _animation.value;
      _animation = Tween<double>(
        begin: _previousSpeed,
        end: _clamp(widget.speed),
      ).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOut),
      );
      _controller
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  double _clamp(double value) =>
      value.clamp(0.0, widget.maxSpeed) / widget.maxSpeed;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, _) {
        final fraction = _animation.value;
        final displaySpeed = fraction * widget.maxSpeed;

        return LayoutBuilder(
          builder: (context, constraints) {
            final side = widget.size ??
                math.min(constraints.maxWidth, constraints.maxHeight);

            return SizedBox(
              width: side,
              height: side,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Gauge arcs, ticks, and needle
                  CustomPaint(
                    size: Size(side, side),
                    painter: _SpeedometerPainter(
                      fraction: fraction,
                      maxSpeed: widget.maxSpeed,
                    ),
                  ),
                  // Center speed readout
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        displaySpeed.toStringAsFixed(1),
                        style: TextStyle(
                          fontFamily: 'Orbitron',
                          fontSize: side * 0.12,
                          fontWeight: FontWeight.w700,
                          color: _speedColor(fraction),
                          shadows: [
                            Shadow(
                              color:
                                  _speedColor(fraction).withValues(alpha: 0.6),
                              blurRadius: 12,
                            ),
                          ],
                        ),
                      ),
                      Text(
                        widget.label,
                        style: TextStyle(
                          fontFamily: 'JetBrains Mono',
                          fontSize: side * 0.04,
                          color: Colors.white38,
                          letterSpacing: 2,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  static Color _speedColor(double fraction) {
    if (fraction > 0.6) return CyberColors.matrixGreen;
    if (fraction > 0.3) return CyberColors.neonCyan;
    return CyberColors.neonPink;
  }
}

// ---------------------------------------------------------------------------
// Custom Painter
// ---------------------------------------------------------------------------

class _SpeedometerPainter extends CustomPainter {
  _SpeedometerPainter({
    required this.fraction,
    required this.maxSpeed,
  });

  /// 0.0 to 1.0, representing current speed / max speed.
  final double fraction;
  final double maxSpeed;

  // Arc geometry: 240 degrees, starting at 150 degrees (bottom-left).
  static const double _startAngle = 150 * (math.pi / 180);
  static const double _sweepAngle = 240 * (math.pi / 180);
  static const int _majorTicks = 10;
  static const int _minorTicksPerMajor = 4;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width * 0.40;
    final rect = Rect.fromCircle(center: center, radius: radius);

    // -- Background arc --
    final bgPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.025
      ..color = Colors.white.withValues(alpha: 0.08)
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(rect, _startAngle, _sweepAngle, false, bgPaint);

    // -- Filled arc (gradient from pink to green) --
    final filledSweep = _sweepAngle * fraction;
    if (filledSweep > 0) {
      final gradientPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = size.width * 0.025
        ..strokeCap = StrokeCap.round
        ..shader = const SweepGradient(
          startAngle: _startAngle,
          endAngle: _startAngle + _sweepAngle,
          colors: [
            CyberColors.neonPink,
            CyberColors.neonCyan,
            CyberColors.matrixGreen,
          ],
          stops: [0.0, 0.5, 1.0],
        ).createShader(rect);

      canvas.drawArc(rect, _startAngle, filledSweep, false, gradientPaint);

      // Glow layer on filled arc
      final glowPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = size.width * 0.04
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8)
        ..shader = SweepGradient(
          startAngle: _startAngle,
          endAngle: _startAngle + _sweepAngle,
          colors: [
            CyberColors.neonPink.withValues(alpha: 0.3),
            CyberColors.neonCyan.withValues(alpha: 0.3),
            CyberColors.matrixGreen.withValues(alpha: 0.3),
          ],
          stops: const [0.0, 0.5, 1.0],
        ).createShader(rect);

      canvas.drawArc(rect, _startAngle, filledSweep, false, glowPaint);
    }

    // -- Tick marks --
    _drawTicks(canvas, center, radius, size);

    // -- Needle --
    _drawNeedle(canvas, center, radius, size);
  }

  void _drawTicks(Canvas canvas, Offset center, double radius, Size size) {
    final majorPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.6)
      ..strokeWidth = 2;
    final minorPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.2)
      ..strokeWidth = 1;

    const tickSpacing = _sweepAngle / _majorTicks;
    const minorSpacing = tickSpacing / (_minorTicksPerMajor + 1);

    for (var i = 0; i <= _majorTicks; i++) {
      final majorAngle = _startAngle + tickSpacing * i;
      final outerR = radius + size.width * 0.03;
      final innerR = radius - size.width * 0.03;

      // Major tick
      canvas.drawLine(
        _polarToCartesian(center, innerR, majorAngle),
        _polarToCartesian(center, outerR, majorAngle),
        majorPaint,
      );

      // Speed label for major ticks
      final speedValue = (maxSpeed / _majorTicks * i).round();
      final labelOffset =
          _polarToCartesian(center, radius - size.width * 0.08, majorAngle);

      final textPainter = TextPainter(
        text: TextSpan(
          text: '$speedValue',
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.4),
            fontSize: size.width * 0.03,
            fontFamily: 'JetBrains Mono',
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(
        canvas,
        labelOffset -
            Offset(textPainter.width / 2, textPainter.height / 2),
      );

      // Minor ticks (except after the last major)
      if (i < _majorTicks) {
        for (var j = 1; j <= _minorTicksPerMajor; j++) {
          final minorAngle = majorAngle + minorSpacing * j;
          final minorOuterR = radius + size.width * 0.015;
          final minorInnerR = radius - size.width * 0.015;

          canvas.drawLine(
            _polarToCartesian(center, minorInnerR, minorAngle),
            _polarToCartesian(center, minorOuterR, minorAngle),
            minorPaint,
          );
        }
      }
    }
  }

  void _drawNeedle(Canvas canvas, Offset center, double radius, Size size) {
    final needleAngle = _startAngle + _sweepAngle * fraction;
    final needleLength = radius * 0.85;
    final needleTip = _polarToCartesian(center, needleLength, needleAngle);

    // Needle shadow / glow
    final glowPaint = Paint()
      ..color = _needleColor().withValues(alpha: 0.4)
      ..strokeWidth = 4
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);

    canvas.drawLine(center, needleTip, glowPaint);

    // Needle line
    final needlePaint = Paint()
      ..color = _needleColor()
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(center, needleTip, needlePaint);

    // Center dot
    final dotPaint = Paint()..color = _needleColor();
    canvas.drawCircle(center, size.width * 0.02, dotPaint);

    // Center dot glow
    final dotGlowPaint = Paint()
      ..color = _needleColor().withValues(alpha: 0.4)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
    canvas.drawCircle(center, size.width * 0.03, dotGlowPaint);
  }

  Color _needleColor() {
    if (fraction > 0.6) return CyberColors.matrixGreen;
    if (fraction > 0.3) return CyberColors.neonCyan;
    return CyberColors.neonPink;
  }

  static Offset _polarToCartesian(
      Offset center, double radius, double angle) {
    return Offset(
      center.dx + radius * math.cos(angle),
      center.dy + radius * math.sin(angle),
    );
  }

  @override
  bool shouldRepaint(covariant _SpeedometerPainter oldDelegate) {
    return oldDelegate.fraction != fraction;
  }
}
