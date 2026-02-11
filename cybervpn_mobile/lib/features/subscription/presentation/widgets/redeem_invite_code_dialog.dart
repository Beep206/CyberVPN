import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';

// ---------------------------------------------------------------------------
// RedeemInviteCodeDialog
// ---------------------------------------------------------------------------

/// Dialog for redeeming an invite code to activate a subscription.
///
/// Displays a text field for entering the code and handles the redemption
/// flow with loading/success/error states.
class RedeemInviteCodeDialog extends ConsumerStatefulWidget {
  const RedeemInviteCodeDialog({super.key});

  @override
  ConsumerState<RedeemInviteCodeDialog> createState() =>
      _RedeemInviteCodeDialogState();
}

class _RedeemInviteCodeDialogState
    extends ConsumerState<RedeemInviteCodeDialog> {
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Clear any previous purchase state when dialog opens.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(subscriptionProvider.notifier).clearPurchaseState();
    });
  }

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    // Listen to purchase state changes to show success/error.
    ref.listen<AsyncValue<SubscriptionState>>(subscriptionProvider,
        (previous, next) {
      final subState = next.value;
      if (subState == null) return;

      setState(() => _isLoading = subState.purchaseState == PurchaseState.loading);

      switch (subState.purchaseState) {
        case PurchaseState.success:
          // Close dialog and show success snackbar.
          if (mounted) {
            Navigator.of(context).pop(true);
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(l10n.subscriptionInviteCodeRedeemed),
                backgroundColor: CyberColors.matrixGreen,
                behavior: SnackBarBehavior.floating,
              ),
            );
          }
        case PurchaseState.error:
          // Show error snackbar.
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(subState.purchaseError ?? l10n.errorOccurred),
                backgroundColor: theme.colorScheme.error,
                behavior: SnackBarBehavior.floating,
              ),
            );
          }
        case PurchaseState.idle:
        case PurchaseState.loading:
          break;
      }
    });

    return AlertDialog(
      title: Text(l10n.subscriptionRedeemInviteCode),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              l10n.subscriptionEnterInviteCodePrompt,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: Spacing.md),
            TextFormField(
              controller: _codeController,
              decoration: InputDecoration(
                labelText: l10n.subscriptionInviteCode,
                hintText: 'XXXXXX',
                prefixIcon: const Icon(Icons.card_giftcard),
                border: const OutlineInputBorder(),
              ),
              textCapitalization: TextCapitalization.characters,
              autocorrect: false,
              enabled: !_isLoading,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return l10n.commonFieldRequired;
                }
                if (value.trim().length < 4) {
                  return l10n.subscriptionInviteCodeTooShort;
                }
                return null;
              },
              onFieldSubmitted: _isLoading ? null : (_) => _handleRedeem(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isLoading ? null : () => Navigator.of(context).pop(false),
          child: Text(l10n.cancel),
        ),
        FilledButton(
          onPressed: _isLoading ? null : _handleRedeem,
          child: _isLoading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(l10n.subscriptionRedeem),
        ),
      ],
    );
  }

  void _handleRedeem() {
    if (!_formKey.currentState!.validate()) return;

    final code = _codeController.text.trim();
    unawaited(ref.read(subscriptionProvider.notifier).redeemInviteCode(code));
  }
}
