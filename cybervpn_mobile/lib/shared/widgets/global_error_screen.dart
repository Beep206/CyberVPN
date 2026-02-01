import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// A user-friendly error screen that replaces Flutter's default red error
/// screen for unrecoverable widget build errors.
///
/// Shows an error icon, a descriptive message, and two action buttons:
/// - **Report** -- captures the error with Sentry including breadcrumbs.
/// - **Restart** -- terminates and restarts the application.
///
/// The error is automatically logged to Sentry (if configured) when this
/// widget is first built.
class GlobalErrorScreen extends StatefulWidget {
  const GlobalErrorScreen({required this.error, super.key});

  /// The error details forwarded by [ErrorWidget.builder].
  final FlutterErrorDetails error;

  @override
  State<GlobalErrorScreen> createState() => _GlobalErrorScreenState();
}

class _GlobalErrorScreenState extends State<GlobalErrorScreen> {
  bool _reported = false;
  bool _errorLogged = false;

  @override
  void initState() {
    super.initState();
    _logErrorToSentry();
  }

  /// Logs the error to Sentry automatically on first build.
  Future<void> _logErrorToSentry() async {
    if (_errorLogged) return;
    _errorLogged = true;
    await Sentry.captureException(
      widget.error.exception,
      stackTrace: widget.error.stack,
    );
  }

  /// Called when the user taps the **Report** button.
  ///
  /// Sends the error with a breadcrumb indicating the user explicitly
  /// requested the report.
  Future<void> _onReport() async {
    Sentry.addBreadcrumb(
      Breadcrumb(
        message: 'User tapped Report on GlobalErrorScreen',
        category: 'ui.action',
        level: SentryLevel.info,
      ),
    );
    await Sentry.captureException(
      widget.error.exception,
      stackTrace: widget.error.stack,
    );
    if (mounted) {
      setState(() => _reported = true);
    }
  }

  /// Called when the user taps the **Restart** button.
  ///
  /// Uses [SystemNavigator.pop] to request the OS to close and restart the
  /// application.
  Future<void> _onRestart() async {
    await SystemNavigator.pop();
  }

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
                // App logo placeholder
                Icon(
                  Icons.shield_outlined,
                  size: 80,
                  color: theme.colorScheme.error,
                ),
                const SizedBox(height: Spacing.lg),

                // Title
                Text(
                  'Something went wrong',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    color: theme.colorScheme.onSurface,
                    fontWeight: FontWeight.w700,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.md),

                // Error description
                Text(
                  'An unexpected error occurred. You can report this '
                  'issue or restart the app.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.xl),

                // Report button
                FilledButton.icon(
                  onPressed: _reported ? null : _onReport,
                  icon: Icon(
                    _reported ? Icons.check : Icons.bug_report_outlined,
                  ),
                  label: Text(_reported ? 'Reported' : 'Report'),
                ),
                const SizedBox(height: Spacing.md),

                // Restart button
                OutlinedButton.icon(
                  onPressed: _onRestart,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Restart'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
