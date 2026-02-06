import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Small chip displaying server latency with color-coded background.
///
/// Colors:
/// - Green  (<100 ms)
/// - Yellow (<200 ms)
/// - Red    (>=200 ms)
/// - Gray   (unknown / null)
///
/// Shows a shimmer-like animation while [isTesting] is true.
/// Tap triggers [onTap] to re-test a single server.
class PingIndicator extends ConsumerWidget {
  const PingIndicator({
    super.key,
    required this.latencyMs,
    this.isTesting = false,
    this.onTap,
  });

  /// Current latency in milliseconds, or `null` if not yet measured.
  final int? latencyMs;

  /// Whether a ping test is currently running for this server.
  final bool isTesting;

  /// Called when the user taps the chip to re-test.
  final VoidCallback? onTap;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Color _backgroundColor(BuildContext context) {
    if (latencyMs == null) {
      return Colors.grey.shade700;
    }
    if (latencyMs! < 100) return Colors.green.shade700;
    if (latencyMs! < 200) return Colors.orange.shade700;
    return Colors.red.shade700;
  }

  Color _foregroundColor() {
    return Colors.white;
  }

  String _label() {
    if (isTesting) return '...';
    if (latencyMs == null) return '-- ms';
    return '$latencyMs ms';
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bg = _backgroundColor(context);
    final fg = _foregroundColor();

    final semanticLabel = isTesting
        ? 'Measuring latency'
        : latencyMs == null
            ? 'Latency unknown'
            : 'Latency: $latencyMs milliseconds';

    final chip = Semantics(
      label: semanticLabel,
      button: onTap != null,
      hint: onTap != null ? 'Tap to re-test server latency' : null,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(12),
            ),
            child: isTesting
                ? _ShimmerDots(color: fg)
                : Text(
                    _label(),
                    style: TextStyle(
                      color: fg,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ),
      ),
    );

    return chip;
  }
}

// ---------------------------------------------------------------------------
// Shimmer dots animation shown while testing
// ---------------------------------------------------------------------------

class _ShimmerDots extends StatefulWidget {
  const _ShimmerDots({required this.color});

  final Color color;

  @override
  State<_ShimmerDots> createState() => _ShimmerDotsState();
}

class _ShimmerDotsState extends State<_ShimmerDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    unawaited(_controller.repeat());
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
      builder: (context, _) {
        final value = _controller.value;
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (index) {
            // Stagger each dot by 0.2.
            final offset = (value - index * 0.2).clamp(0.0, 1.0);
            final opacity = (0.3 + 0.7 * _pulse(offset)).clamp(0.0, 1.0);
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 1.5),
              child: Opacity(
                opacity: opacity,
                child: Text(
                  '.',
                  style: TextStyle(
                    color: widget.color,
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }

  /// Simple sine-based pulse for a smooth shimmer feel.
  double _pulse(double t) {
    return (1.0 + (t * 3.14159 * 2).clamp(0, 6.28).toDouble().sin()) / 2.0;
  }
}

// ---------------------------------------------------------------------------
// Extension – dart:math sin via a tiny helper so we avoid importing dart:math
// in the widget file. We use the num extension approach instead.
// ---------------------------------------------------------------------------
extension _SinHelper on double {
  double sin() {
    // Taylor series approximation (sufficient for animation).
    // Normalize to [-pi, pi] range.
    double x = this % (2 * 3.14159265);
    if (x > 3.14159265) x -= 2 * 3.14159265;
    if (x < -3.14159265) x += 2 * 3.14159265;

    final x2 = x * x;
    final x3 = x2 * x;
    final x5 = x3 * x2;
    final x7 = x5 * x2;
    return x - x3 / 6 + x5 / 120 - x7 / 5040;
  }
}
