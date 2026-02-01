import 'package:flutter/material.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/l10n/arb/app_localizations.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/security/device_integrity.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Dialog shown when a rooted or jailbroken device is detected.
///
/// This dialog is non-blocking and informational only. It warns users about
/// the security implications of using a rooted/jailbroken device but does
/// NOT prevent app usage. This is important for VPN users in censored regions
/// who may rely on rooted devices for additional privacy tools.
///
/// Features:
/// - Warning icon and message explaining security risks
/// - Emphasis that app usage is NOT blocked
/// - Dismiss button with persistence (won't show again after dismissed)
/// - Sentry scope tagging for monitoring
class RootDetectionDialog extends StatelessWidget {
  final DeviceIntegrityChecker integrityChecker;

  const RootDetectionDialog({
    super.key,
    required this.integrityChecker,
  });

  /// Shows the root detection dialog.
  ///
  /// Call this method when a rooted/jailbroken device is detected and the
  /// user has not previously dismissed the warning.
  ///
  /// Automatically tags the Sentry scope with 'device_rooted: true' for
  /// monitoring purposes.
  static Future<void> show({
    required BuildContext context,
    required DeviceIntegrityChecker integrityChecker,
  }) async {
    // Tag Sentry scope to track rooted device users
    await Sentry.configureScope((scope) {
      scope.setTag('device_rooted', 'true');
    });

    AppLogger.warning(
      'Showing root detection warning dialog',
      category: 'security',
    );

    if (!context.mounted) return;

    await showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (context) => RootDetectionDialog(
        integrityChecker: integrityChecker,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Radii.lg),
      ),
      backgroundColor: theme.colorScheme.surface,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(Radii.lg),
          border: Border.all(
            color: theme.colorScheme.tertiary,
            width: 2,
          ),
          boxShadow: [
            BoxShadow(
              color: theme.colorScheme.tertiary.withAlpha(76), // 0.3 * 255
              blurRadius: 16,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(theme, l10n),
              const SizedBox(height: Spacing.md),
              _buildContent(theme, l10n),
              const SizedBox(height: Spacing.lg),
              _buildDismissButton(theme, l10n, context),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(ThemeData theme, AppLocalizations l10n) {
    return Row(
      children: [
        Icon(
          Icons.security_rounded,
          color: theme.colorScheme.tertiary,
          size: 32,
        ),
        const SizedBox(width: Spacing.md),
        Expanded(
          child: Text(
            l10n.rootDetectionDialogTitle,
            style: theme.textTheme.headlineSmall?.copyWith(
              color: theme.colorScheme.tertiary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildContent(ThemeData theme, AppLocalizations l10n) {
    return Container(
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(Radii.sm),
      ),
      child: Text(
        l10n.rootDetectionDialogDescription,
        style: theme.textTheme.bodyMedium?.copyWith(
          height: 1.5,
        ),
      ),
    );
  }

  Widget _buildDismissButton(
    ThemeData theme,
    AppLocalizations l10n,
    BuildContext context,
  ) {
    return FilledButton(
      onPressed: () => _handleDismiss(context),
      style: FilledButton.styleFrom(
        backgroundColor: theme.colorScheme.tertiary,
        foregroundColor: theme.colorScheme.onTertiary,
        padding: const EdgeInsets.symmetric(vertical: Spacing.md),
      ),
      child: Text(l10n.rootDetectionDialogDismiss),
    );
  }

  Future<void> _handleDismiss(BuildContext context) async {
    // Save dismiss preference so dialog won't show again
    await integrityChecker.dismissWarning();

    if (!context.mounted) return;
    Navigator.of(context).pop();
  }
}
