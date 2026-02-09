import 'package:flutter/material.dart';

/// A CRT-style horizontal scanline overlay for the cyberpunk theme.
///
/// Renders subtle horizontal lines at 2% opacity across the child widget,
/// creating a retro CRT monitor aesthetic. The overlay uses [IgnorePointer]
/// so it never intercepts taps or gestures.
///
/// Usage:
/// ```dart
/// ScanlineOverlay(
///   enabled: isCyberpunkTheme && scanlineEnabled,
///   child: MyScreen(),
/// )
/// ```
class ScanlineOverlay extends StatelessWidget {
  const ScanlineOverlay({
    super.key,
    required this.child,
    this.enabled = true,
  });

  /// The widget to display beneath the scanline overlay.
  final Widget child;

  /// Whether the scanline effect is active.
  ///
  /// When `false`, only the [child] is rendered with no overlay.
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    if (!enabled) return child;

    return Stack(
      children: [
        child,
        Positioned.fill(
          child: IgnorePointer(
            child: CustomPaint(
              painter: _ScanlinePainter(),
            ),
          ),
        ),
      ],
    );
  }
}

/// Custom painter that draws horizontal scanlines across the entire canvas.
///
/// Lines are 1 logical pixel tall, spaced 4 pixels apart, drawn at 2% opacity
/// in black. This produces a subtle CRT effect without impacting readability.
class _ScanlinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0x05000000) // ~2% opacity black
      ..style = PaintingStyle.fill;

    const double lineHeight = 1.0;
    const double lineSpacing = 4.0;

    double y = 0;
    while (y < size.height) {
      canvas.drawRect(
        Rect.fromLTWH(0, y, size.width, lineHeight),
        paint,
      );
      y += lineSpacing;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
