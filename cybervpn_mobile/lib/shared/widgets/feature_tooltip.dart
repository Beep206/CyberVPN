import 'package:flutter/material.dart';

/// Position of the tooltip relative to the target widget.
enum TooltipPosition {
  top,
  bottom,
  left,
  right,
}

/// A feature discovery tooltip that displays a pointed bubble with message text
/// and tap-anywhere-to-dismiss functionality.
///
/// This widget uses an overlay to display the tooltip and can be positioned
/// relative to a target widget using a GlobalKey.
///
/// Example usage:
/// ```dart
/// final _buttonKey = GlobalKey();
///
/// // In build method:
/// ElevatedButton(
///   key: _buttonKey,
///   onPressed: () {},
///   child: Text('Click me'),
/// ),
///
/// // Show tooltip:
/// FeatureTooltip.show(
///   context: context,
///   targetKey: _buttonKey,
///   message: 'This is a helpful tip!',
///   position: TooltipPosition.bottom,
///   onDismiss: () {
///     // Handle dismissal
///   },
/// );
/// ```
class FeatureTooltip {
  /// Show a feature tooltip positioned relative to a target widget.
  ///
  /// [context] - The build context.
  /// [targetKey] - GlobalKey of the target widget to position the tooltip.
  /// [message] - The message text to display in the tooltip.
  /// [position] - The position of the tooltip relative to the target (default: bottom).
  /// [onDismiss] - Callback invoked when the tooltip is dismissed.
  static OverlayEntry? show({
    required BuildContext context,
    required GlobalKey targetKey,
    required String message,
    TooltipPosition position = TooltipPosition.bottom,
    VoidCallback? onDismiss,
  }) {
    final overlay = Overlay.of(context);
    late OverlayEntry overlayEntry;

    overlayEntry = OverlayEntry(
      builder: (context) => _FeatureTooltipOverlay(
        targetKey: targetKey,
        message: message,
        position: position,
        onDismiss: () {
          overlayEntry.remove();
          onDismiss?.call();
        },
      ),
    );

    overlay.insert(overlayEntry);
    return overlayEntry;
  }
}

/// Internal widget that renders the tooltip overlay.
class _FeatureTooltipOverlay extends StatefulWidget {
  final GlobalKey targetKey;
  final String message;
  final TooltipPosition position;
  final VoidCallback onDismiss;

  const _FeatureTooltipOverlay({
    required this.targetKey,
    required this.message,
    required this.position,
    required this.onDismiss,
  });

  @override
  State<_FeatureTooltipOverlay> createState() => _FeatureTooltipOverlayState();
}

class _FeatureTooltipOverlayState extends State<_FeatureTooltipOverlay>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );

    _fadeAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeOut,
    );

    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeOutBack,
      ),
    );

    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  void _handleDismiss() async {
    await _animationController.reverse();
    widget.onDismiss();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final targetRenderBox =
        widget.targetKey.currentContext?.findRenderObject() as RenderBox?;

    if (targetRenderBox == null) {
      // Target widget not found, dismiss immediately
      WidgetsBinding.instance.addPostFrameCallback((_) {
        widget.onDismiss();
      });
      return const SizedBox.shrink();
    }

    final targetSize = targetRenderBox.size;
    final targetPosition = targetRenderBox.localToGlobal(Offset.zero);

    return Stack(
      children: [
        // Semi-transparent backdrop - tap anywhere to dismiss
        Positioned.fill(
          child: GestureDetector(
            onTap: _handleDismiss,
            child: FadeTransition(
              opacity: _fadeAnimation,
              child: Container(
                color: Colors.black.withValues(alpha: 0.3),
              ),
            ),
          ),
        ),
        // Tooltip bubble
        Positioned(
          left: _calculateLeft(targetPosition, targetSize),
          top: _calculateTop(targetPosition, targetSize),
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: ScaleTransition(
              scale: _scaleAnimation,
              child: _TooltipBubble(
                message: widget.message,
                position: widget.position,
                theme: theme,
              ),
            ),
          ),
        ),
      ],
    );
  }

  double? _calculateLeft(Offset targetPosition, Size targetSize) {
    const padding = 16.0;
    switch (widget.position) {
      case TooltipPosition.left:
        return targetPosition.dx - 200 - padding;
      case TooltipPosition.right:
        return targetPosition.dx + targetSize.width + padding;
      case TooltipPosition.top:
      case TooltipPosition.bottom:
        // Center horizontally
        return (targetPosition.dx + targetSize.width / 2) - 100;
    }
  }

  double? _calculateTop(Offset targetPosition, Size targetSize) {
    const padding = 16.0;
    switch (widget.position) {
      case TooltipPosition.top:
        return targetPosition.dy - 80 - padding;
      case TooltipPosition.bottom:
        return targetPosition.dy + targetSize.height + padding;
      case TooltipPosition.left:
      case TooltipPosition.right:
        // Center vertically
        return targetPosition.dy + (targetSize.height / 2) - 40;
    }
  }
}

/// Internal widget that renders the tooltip bubble with arrow.
class _TooltipBubble extends StatelessWidget {
  final String message;
  final TooltipPosition position;
  final ThemeData theme;

  const _TooltipBubble({
    required this.message,
    required this.position,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 200,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: _getAlignment(),
        children: [
          if (position == TooltipPosition.bottom) _buildArrow(true),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Text(
              message,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onPrimaryContainer,
              ),
              textAlign: TextAlign.center,
            ),
          ),
          if (position == TooltipPosition.top) _buildArrow(false),
        ],
      ),
    );
  }

  CrossAxisAlignment _getAlignment() {
    switch (position) {
      case TooltipPosition.left:
        return CrossAxisAlignment.end;
      case TooltipPosition.right:
        return CrossAxisAlignment.start;
      case TooltipPosition.top:
      case TooltipPosition.bottom:
        return CrossAxisAlignment.center;
    }
  }

  Widget _buildArrow(bool pointingUp) {
    return CustomPaint(
      size: const Size(16, 8),
      painter: _ArrowPainter(
        color: theme.colorScheme.primaryContainer,
        pointingUp: pointingUp,
      ),
    );
  }
}

/// Custom painter for the tooltip arrow.
class _ArrowPainter extends CustomPainter {
  final Color color;
  final bool pointingUp;

  _ArrowPainter({required this.color, required this.pointingUp});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final path = Path();

    if (pointingUp) {
      // Arrow pointing up (for bottom tooltip)
      path.moveTo(size.width / 2, 0);
      path.lineTo(0, size.height);
      path.lineTo(size.width, size.height);
    } else {
      // Arrow pointing down (for top tooltip)
      path.moveTo(0, 0);
      path.lineTo(size.width, 0);
      path.lineTo(size.width / 2, size.height);
    }

    path.close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
