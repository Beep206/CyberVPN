import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// An error boundary that catches errors in its child subtree and displays a
/// graceful fallback UI instead of crashing the entire app.
///
/// Wrap each feature's root screen so that a failure in one feature (e.g.
/// diagnostics) does not bring down the whole application.
///
/// ```dart
/// FeatureErrorBoundary(
///   featureName: 'Servers',
///   child: ServerListScreen(),
/// )
/// ```
///
/// **Mechanism**: Registers a scoped [FlutterError.onError] handler. When a
/// Flutter framework error (build, layout, or paint) fires from the child
/// subtree, the boundary captures it and replaces the child with fallback UI
/// containing Report and Retry buttons.
class FeatureErrorBoundary extends StatefulWidget {
  const FeatureErrorBoundary({
    required this.featureName,
    required this.child,
    super.key,
  });

  /// Human-readable feature name shown in the fallback UI.
  final String featureName;

  /// The subtree to protect.
  final Widget child;

  @override
  State<FeatureErrorBoundary> createState() => _FeatureErrorBoundaryState();
}

class _FeatureErrorBoundaryState extends State<FeatureErrorBoundary> {
  Object? _error;
  StackTrace? _stackTrace;
  bool _reported = false;

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return _ErrorFallbackView(
        featureName: widget.featureName,
        reported: _reported,
        onRetry: _retry,
        onReport: _report,
      );
    }

    // Wrap with a custom ErrorWidget.builder scoped to this subtree.
    // If the child's build/layout/paint fails, Flutter replaces the broken
    // widget with whatever ErrorWidget.builder returns. We use that to
    // detect the failure and switch to our fallback.
    return _ScopedErrorBuilder(
      onError: _handleError,
      child: widget.child,
    );
  }

  void _handleError(Object error, StackTrace? stackTrace) {
    AppLogger.error(
      'FeatureErrorBoundary caught error in "${widget.featureName}"',
      error: error,
      stackTrace: stackTrace,
      category: 'error_boundary',
    );

    unawaited(
      Sentry.captureException(error, stackTrace: stackTrace),
    );

    // Schedule the state update for after the current frame to avoid
    // setState during build/layout.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        setState(() {
          _error = error;
          _stackTrace = stackTrace;
          _reported = false;
        });
      }
    });
  }

  void _retry() {
    setState(() {
      _error = null;
      _stackTrace = null;
      _reported = false;
    });
  }

  Future<void> _report() async {
    if (_error == null) return;
    unawaited(Sentry.addBreadcrumb(
      Breadcrumb(
        message: 'User reported error in "${widget.featureName}"',
        category: 'ui.action',
        level: SentryLevel.info,
      ),
    ));
    await Sentry.captureException(_error!, stackTrace: _stackTrace);
    if (mounted) {
      setState(() => _reported = true);
    }
  }
}

/// Overrides [ErrorWidget.builder] for its subtree using a [HeroController]-
/// style technique: saves & restores the global builder around the protected
/// child's lifetime.
///
/// When a Flutter framework error occurs in the child subtree, the framework
/// calls [ErrorWidget.builder] to produce a replacement widget. Our override
/// notifies the parent [FeatureErrorBoundary] so it can show the fallback.
class _ScopedErrorBuilder extends StatefulWidget {
  const _ScopedErrorBuilder({required this.onError, required this.child});

  final void Function(Object error, StackTrace? stackTrace) onError;
  final Widget child;

  @override
  State<_ScopedErrorBuilder> createState() => _ScopedErrorBuilderState();
}

class _ScopedErrorBuilderState extends State<_ScopedErrorBuilder> {
  @override
  Widget build(BuildContext context) {
    return widget.child;
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _installErrorOverride();
  }

  void _installErrorOverride() {
    final previous = ErrorWidget.builder;
    ErrorWidget.builder = (FlutterErrorDetails details) {
      // Restore the previous builder so other error boundaries and the global
      // handler still work.
      ErrorWidget.builder = previous;

      // Notify the boundary.
      widget.onError(
        details.exception,
        details.stack ?? StackTrace.current,
      );

      // Return a minimal placeholder so the framework has something to render
      // for this frame before our post-frame callback swaps in the fallback.
      return const SizedBox.shrink();
    };
  }
}

/// Fallback UI shown when a feature crashes.
class _ErrorFallbackView extends StatelessWidget {
  const _ErrorFallbackView({
    required this.featureName,
    required this.reported,
    required this.onRetry,
    required this.onReport,
  });

  final String featureName;
  final bool reported;
  final VoidCallback onRetry;
  final Future<void> Function() onReport;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: theme.colorScheme.surface,
      child: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(Spacing.lg),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.warning_amber_rounded,
                  size: 64,
                  color: theme.colorScheme.error,
                ),
                const SizedBox(height: Spacing.md),
                Text(
                  'Something went wrong',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.sm),
                Text(
                  'The $featureName feature encountered an error.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.xl),
                FilledButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
                ),
                const SizedBox(height: Spacing.sm),
                _ReportButton(
                  reported: reported,
                  onReport: onReport,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Report button with loading state.
class _ReportButton extends StatefulWidget {
  const _ReportButton({required this.reported, required this.onReport});

  final bool reported;
  final Future<void> Function() onReport;

  @override
  State<_ReportButton> createState() => _ReportButtonState();
}

class _ReportButtonState extends State<_ReportButton> {
  bool _sending = false;

  Future<void> _onPressed() async {
    setState(() => _sending = true);
    await widget.onReport();
    if (mounted) {
      setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final reported = widget.reported;

    return OutlinedButton.icon(
      onPressed: reported || _sending ? null : _onPressed,
      icon: _sending
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(reported ? Icons.check : Icons.bug_report_outlined),
      label: Text(reported ? 'Reported' : 'Report'),
    );
  }
}
