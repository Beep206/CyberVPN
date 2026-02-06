import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/shared/services/version_service.dart';

/// In-app update dialog supporting mandatory and optional update modes.
///
/// Mandatory mode:
/// - Fullscreen barrier dismissible false
/// - Blocks all app interaction
/// - Shows only "Update Now" button
///
/// Optional mode:
/// - Barrier dismissible true
/// - Shows "Update Now" and "Later" buttons
/// - Includes "Remind me in 3 days" snooze option
class InAppUpdateDialog extends StatefulWidget {
  /// Update information from [VersionService].
  final UpdateStatus updateInfo;

  /// Callback invoked when user initiates update.
  final VoidCallback onUpdate;

  /// Callback invoked when user dismisses optional update.
  /// Only called for optional updates.
  final VoidCallback? onDismiss;

  /// SharedPreferences instance for storing snooze timestamp.
  final SharedPreferences prefs;

  const InAppUpdateDialog({
    super.key,
    required this.updateInfo,
    required this.onUpdate,
    required this.prefs,
    this.onDismiss,
  });

  /// Storage key for snooze timestamp.
  @visibleForTesting
  static const String snoozeKey = 'update_snooze_timestamp';

  /// Snooze duration (3 days).
  static const Duration _snoozeDuration = Duration(days: 3);

  /// Checks if the update dialog should be shown based on snooze status.
  ///
  /// Returns `true` if:
  /// - Never snoozed before
  /// - Snooze period has expired (3 days passed)
  /// - Update is mandatory (ignores snooze)
  static bool shouldShowDialog({
    required UpdateStatus updateInfo,
    required SharedPreferences prefs,
  }) {
    if (!updateInfo.needsUpdate) {
      return false;
    }

    // Mandatory updates always show
    if (updateInfo.isMandatory) {
      return true;
    }

    // Check snooze status for optional updates
    final snoozeTimestamp = prefs.getInt(snoozeKey);
    if (snoozeTimestamp == null) {
      return true; // Never snoozed
    }

    final snoozeTime = DateTime.fromMillisecondsSinceEpoch(snoozeTimestamp);
    final now = DateTime.now();
    final timeSinceSnooze = now.difference(snoozeTime);

    return timeSinceSnooze >= _snoozeDuration;
  }

  /// Clears the snooze timestamp (useful for testing or forcing dialog).
  static Future<void> clearSnooze(SharedPreferences prefs) async {
    await prefs.remove(snoozeKey);
  }

  /// Shows the update dialog with appropriate mode based on update info.
  static Future<void> show({
    required BuildContext context,
    required UpdateStatus updateInfo,
    required VoidCallback onUpdate,
    required SharedPreferences prefs,
    VoidCallback? onDismiss,
  }) async {
    if (!shouldShowDialog(updateInfo: updateInfo, prefs: prefs)) {
      return;
    }

    if (!context.mounted) return;

    await showDialog<void>(
      context: context,
      barrierDismissible: !updateInfo.isMandatory,
      builder: (context) => InAppUpdateDialog(
        updateInfo: updateInfo,
        onUpdate: onUpdate,
        prefs: prefs,
        onDismiss: onDismiss,
      ),
    );
  }

  @override
  State<InAppUpdateDialog> createState() => _InAppUpdateDialogState();
}

class _InAppUpdateDialogState extends State<InAppUpdateDialog> {
  bool _snoozeEnabled = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final isMandatory = widget.updateInfo.isMandatory;

    return PopScope(
      canPop: !isMandatory,
      child: Dialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.lg),
        ),
        backgroundColor: theme.colorScheme.surface,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(Radii.lg),
            border: Border.all(
              color: isMandatory
                  ? theme.colorScheme.error
                  : theme.colorScheme.primary,
              width: 2,
            ),
            boxShadow: [
              BoxShadow(
                color: (isMandatory
                        ? theme.colorScheme.error
                        : theme.colorScheme.primary)
                    .withAlpha(76), // 0.3 * 255
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
                _buildHeader(theme, isMandatory, l10n),
                const SizedBox(height: Spacing.md),
                _buildContent(theme, l10n),
                const SizedBox(height: Spacing.lg),
                if (!isMandatory) _buildSnoozeCheckbox(theme, l10n),
                if (!isMandatory) const SizedBox(height: Spacing.md),
                _buildActions(theme, isMandatory, l10n),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(ThemeData theme, bool isMandatory, AppLocalizations l10n) {
    return Row(
      children: [
        Icon(
          isMandatory ? Icons.warning_rounded : Icons.info_rounded,
          color: isMandatory
              ? theme.colorScheme.error
              : theme.colorScheme.primary,
          size: 32,
        ),
        const SizedBox(width: Spacing.md),
        Expanded(
          child: Text(
            isMandatory ? l10n.updateRequired : l10n.updateAvailable,
            style: theme.textTheme.headlineSmall?.copyWith(
              color: isMandatory
                  ? theme.colorScheme.error
                  : theme.colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildContent(ThemeData theme, AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          isMandatory
              ? l10n.updateMandatoryDescription
              : l10n.updateOptionalDescription,
          style: theme.textTheme.bodyLarge,
        ),
        const SizedBox(height: Spacing.md),
        Container(
          padding: const EdgeInsets.all(Spacing.md),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(Radii.sm),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildVersionRow(
                theme,
                l10n.updateCurrentVersion,
                widget.updateInfo.currentVersion,
              ),
              const SizedBox(height: Spacing.sm),
              _buildVersionRow(
                theme,
                l10n.updateLatestVersion,
                widget.updateInfo.latestVersion,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildVersionRow(ThemeData theme, String label, String version) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          version,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.bold,
            fontFeatures: [const FontFeature.tabularFigures()],
          ),
        ),
      ],
    );
  }

  Widget _buildSnoozeCheckbox(ThemeData theme, AppLocalizations l10n) {
    return CheckboxListTile(
      value: _snoozeEnabled,
      onChanged: (value) {
        setState(() {
          _snoozeEnabled = value ?? false;
        });
      },
      title: Text(
        l10n.updateRemindLater,
        style: theme.textTheme.bodyMedium,
      ),
      controlAffinity: ListTileControlAffinity.leading,
      contentPadding: EdgeInsets.zero,
      dense: true,
    );
  }

  Widget _buildActions(ThemeData theme, bool isMandatory, AppLocalizations l10n) {
    if (isMandatory) {
      return FilledButton(
        onPressed: widget.onUpdate,
        style: FilledButton.styleFrom(
          backgroundColor: theme.colorScheme.error,
          foregroundColor: theme.colorScheme.onError,
          padding: const EdgeInsets.symmetric(vertical: Spacing.md),
        ),
        child: Text(l10n.updateNow),
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: _handleDismiss,
          child: Text(l10n.updateLater),
        ),
        const SizedBox(width: Spacing.sm),
        FilledButton(
          onPressed: widget.onUpdate,
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.lg,
              vertical: Spacing.md,
            ),
          ),
          child: Text(l10n.updateNow),
        ),
      ],
    );
  }

  Future<void> _handleDismiss() async {
    // Store snooze timestamp if checkbox is enabled
    if (_snoozeEnabled) {
      await widget.prefs.setInt(
        InAppUpdateDialog.snoozeKey,
        DateTime.now().millisecondsSinceEpoch,
      );
    }

    if (!mounted) return;
    Navigator.of(context).pop();
    widget.onDismiss?.call();
  }

  bool get isMandatory => widget.updateInfo.isMandatory;
}
