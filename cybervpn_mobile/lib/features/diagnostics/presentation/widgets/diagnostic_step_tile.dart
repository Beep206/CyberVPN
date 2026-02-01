import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';

// ---------------------------------------------------------------------------
// DiagnosticStepTile
// ---------------------------------------------------------------------------

/// A single diagnostic step row with animated status transitions.
///
/// Shows:
/// - Step name
/// - Animated status indicator (spinner → green check / red X)
/// - Duration (if available)
/// - Message and suggestion on failure
///
/// Animations:
/// - Icon transitions (pending → running → success/failed)
/// - Color transitions matching status
/// - Scale animation on status change
/// - Slide-in animation for suggestion box
class DiagnosticStepTile extends StatefulWidget {
  const DiagnosticStepTile({
    super.key,
    required this.stepName,
    required this.status,
    this.duration,
    this.message,
    this.suggestion,
  });

  final String stepName;
  final DiagnosticStepStatus status;
  final Duration? duration;
  final String? message;
  final String? suggestion;

  @override
  State<DiagnosticStepTile> createState() => _DiagnosticStepTileState();
}

class _DiagnosticStepTileState extends State<DiagnosticStepTile>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: AnimDurations.normal,
      vsync: this,
    );

    _scaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeOutBack,
      ),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: Curves.easeIn,
      ),
    );
  }

  @override
  void didUpdateWidget(DiagnosticStepTile oldWidget) {
    super.didUpdateWidget(oldWidget);

    // Trigger animation when status changes.
    if (oldWidget.status != widget.status) {
      _animationController.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _getStatusColor(widget.status);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: Spacing.xs),
      child: AnimatedContainer(
        duration: AnimDurations.normal,
        padding: const EdgeInsets.all(Spacing.sm + 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.02),
          borderRadius: BorderRadius.circular(Radii.sm),
          border: Border.all(
            color: statusColor.withValues(alpha: 0.2),
            width: 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Main row: status icon, step name, duration
            Row(
              children: [
                // Animated status icon
                SizedBox(
                  width: 24,
                  height: 24,
                  child: _buildAnimatedStatusIcon(widget.status, statusColor),
                ),

                const SizedBox(width: Spacing.sm),

                // Step name
                Expanded(
                  child: Text(
                    widget.stepName,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.9),
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      letterSpacing: 0.3,
                    ),
                  ),
                ),

                // Duration (animated fade-in)
                if (widget.duration != null)
                  FadeTransition(
                    opacity: _fadeAnimation,
                    child: Text(
                      '${widget.duration!.inMilliseconds}ms',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 11,
                        fontFamily: 'JetBrains Mono',
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
              ],
            ),

            // Message (animated slide-in)
            if (widget.message != null)
              _AnimatedMessageBox(
                message: widget.message!,
                color: statusColor,
              ),

            // Suggestion (animated slide-in for failures)
            if (widget.status == DiagnosticStepStatus.failed &&
                widget.suggestion != null)
              _AnimatedSuggestionBox(
                suggestion: widget.suggestion!,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnimatedStatusIcon(DiagnosticStepStatus status, Color color) {
    switch (status) {
      case DiagnosticStepStatus.pending:
        return Icon(
          Icons.radio_button_unchecked,
          color: color,
          size: 20,
        );

      case DiagnosticStepStatus.running:
        return CircularProgressIndicator(
          strokeWidth: 2,
          color: color,
          value: null, // Indeterminate spinner
        );

      case DiagnosticStepStatus.success:
      case DiagnosticStepStatus.failed:
      case DiagnosticStepStatus.warning:
        // Animate the final status icon with scale.
        return ScaleTransition(
          scale: _scaleAnimation,
          child: Icon(
            _getStatusIcon(status),
            color: color,
            size: 20,
          ),
        );
    }
  }

  IconData _getStatusIcon(DiagnosticStepStatus status) {
    switch (status) {
      case DiagnosticStepStatus.success:
        return Icons.check_circle;
      case DiagnosticStepStatus.failed:
        return Icons.cancel;
      case DiagnosticStepStatus.warning:
        return Icons.warning_amber_rounded;
      case DiagnosticStepStatus.pending:
      case DiagnosticStepStatus.running:
        return Icons.radio_button_unchecked;
    }
  }

  Color _getStatusColor(DiagnosticStepStatus status) {
    switch (status) {
      case DiagnosticStepStatus.pending:
        return Colors.white.withValues(alpha: 0.3);
      case DiagnosticStepStatus.running:
        return CyberColors.neonCyan;
      case DiagnosticStepStatus.success:
        return CyberColors.matrixGreen;
      case DiagnosticStepStatus.failed:
        return CyberColors.neonPink;
      case DiagnosticStepStatus.warning:
        return Colors.orange;
    }
  }
}

// ---------------------------------------------------------------------------
// AnimatedMessageBox
// ---------------------------------------------------------------------------

class _AnimatedMessageBox extends StatefulWidget {
  const _AnimatedMessageBox({
    required this.message,
    required this.color,
  });

  final String message;
  final Color color;

  @override
  State<_AnimatedMessageBox> createState() => _AnimatedMessageBoxState();
}

class _AnimatedMessageBoxState extends State<_AnimatedMessageBox>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: AnimDurations.normal,
      vsync: this,
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(-0.1, 0),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOut,
      ),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeIn,
      ),
    );

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Padding(
          padding: const EdgeInsets.only(left: 32, top: Spacing.xs),
          child: Text(
            widget.message,
            style: TextStyle(
              color: widget.color.withValues(alpha: 0.7),
              fontSize: 12,
              letterSpacing: 0.2,
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// AnimatedSuggestionBox
// ---------------------------------------------------------------------------

class _AnimatedSuggestionBox extends StatefulWidget {
  const _AnimatedSuggestionBox({
    required this.suggestion,
  });

  final String suggestion;

  @override
  State<_AnimatedSuggestionBox> createState() => _AnimatedSuggestionBoxState();
}

class _AnimatedSuggestionBoxState extends State<_AnimatedSuggestionBox>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -0.2),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOutCubic,
      ),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeIn,
      ),
    );

    // Start animation after a brief delay to ensure message appears first.
    Future.delayed(const Duration(milliseconds: 150), () {
      if (mounted) {
        _controller.forward();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Padding(
          padding: const EdgeInsets.only(left: 32, top: Spacing.xs),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.sm,
              vertical: Spacing.xs,
            ),
            decoration: BoxDecoration(
              color: CyberColors.neonPink.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(Radii.sm - 2),
              border: Border.all(
                color: CyberColors.neonPink.withValues(alpha: 0.2),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.lightbulb_outline,
                  color: CyberColors.neonPink.withValues(alpha: 0.8),
                  size: 14,
                ),
                const SizedBox(width: Spacing.xs),
                Expanded(
                  child: Text(
                    widget.suggestion,
                    style: TextStyle(
                      color: CyberColors.neonPink.withValues(alpha: 0.9),
                      fontSize: 11,
                      letterSpacing: 0.2,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
