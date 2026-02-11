import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';

// ---------------------------------------------------------------------------
// CancelSubscriptionSheet
// ---------------------------------------------------------------------------

/// Bottom sheet for confirming subscription cancellation.
///
/// Shows a warning message with red theme and requires explicit confirmation.
/// On confirmation, calls POST /subscriptions/cancel and closes with result.
class CancelSubscriptionSheet extends ConsumerStatefulWidget {
  const CancelSubscriptionSheet({
    super.key,
    required this.subscriptionId,
  });

  final String subscriptionId;

  /// Shows the cancel subscription bottom sheet.
  ///
  /// Returns `true` if the subscription was successfully cancelled, `false` otherwise.
  static Future<bool?> show(BuildContext context, String subscriptionId) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (context) => CancelSubscriptionSheet(subscriptionId: subscriptionId),
    );
  }

  @override
  ConsumerState<CancelSubscriptionSheet> createState() => _CancelSubscriptionSheetState();
}

class _CancelSubscriptionSheetState extends ConsumerState<CancelSubscriptionSheet> {
  bool _isCancelling = false;

  Future<void> _confirmCancel() async {
    setState(() => _isCancelling = true);

    final repo = ref.read(subscriptionRepositoryProvider);
    final result = await repo.cancelSubscription(widget.subscriptionId);

    if (!mounted) return;

    switch (result) {
      case Success():
        // Show success message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).subscriptionCancelled),
          ),
        );
        // Close with success
        Navigator.of(context).pop(true);
      case Failure(:final failure):
        // Show error message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(failure.message),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
        setState(() => _isCancelling = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          24,
          24,
          24,
          24 + MediaQuery.of(context).viewInsets.bottom,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Warning icon
            Icon(
              Icons.warning_amber_rounded,
              size: 64,
              color: colorScheme.error,
            ),
            const SizedBox(height: 16),

            // Title
            Text(
              l10n.subscriptionCancelTitle,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),

            // Warning message
            Text(
              l10n.subscriptionCancelWarning,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),

            // Details
            Text(
              l10n.subscriptionCancelDetails,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),

            // Cancel button (red)
            FilledButton(
              key: const Key('btn_confirm_cancel'),
              onPressed: _isCancelling ? null : _confirmCancel,
              style: FilledButton.styleFrom(
                backgroundColor: colorScheme.error,
                foregroundColor: colorScheme.onError,
              ),
              child: _isCancelling
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(l10n.subscriptionCancelButton),
            ),
            const SizedBox(height: 12),

            // Keep subscription button
            OutlinedButton(
              key: const Key('btn_keep_subscription'),
              onPressed: _isCancelling ? null : () => Navigator.of(context).pop(false),
              child: Text(l10n.subscriptionKeepButton),
            ),
          ],
        ),
      ),
    );
  }
}
