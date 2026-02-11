import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/types/result.dart';

// ---------------------------------------------------------------------------
// PromoCodeField
// ---------------------------------------------------------------------------

/// Expandable promo code input field with validation.
///
/// Shows a collapsed button to "Have a promo code?" that expands to reveal
/// an input field. Validates the code against the backend and displays
/// discount information or error messages.
class PromoCodeField extends ConsumerStatefulWidget {
  const PromoCodeField({
    super.key,
    required this.planId,
    required this.onPromoApplied,
  });

  final String planId;
  final void Function(double discountAmount, double finalPrice) onPromoApplied;

  @override
  ConsumerState<PromoCodeField> createState() => _PromoCodeFieldState();
}

class _PromoCodeFieldState extends ConsumerState<PromoCodeField> {
  bool _isExpanded = false;
  bool _isValidating = false;
  final _codeController = TextEditingController();
  String? _errorMessage;
  double? _discountAmount;
  double? _finalPrice;
  bool _isApplied = false;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final colorScheme = theme.colorScheme;

    if (!_isExpanded) {
      // Collapsed state: "Have a promo code?" button
      return TextButton.icon(
        key: const Key('btn_show_promo_field'),
        onPressed: () => setState(() => _isExpanded = true),
        icon: const Icon(Icons.local_offer_outlined, size: 18),
        label: Text(l10n.subscriptionHavePromoCode),
      );
    }

    // Expanded state: promo code input field
    return Card(
      elevation: 0,
      color: colorScheme.surfaceContainerHighest.withAlpha(128),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    key: const Key('input_promo_code'),
                    controller: _codeController,
                    decoration: InputDecoration(
                      labelText: l10n.subscriptionPromoCode,
                      hintText: 'SAVE20',
                      prefixIcon: const Icon(Icons.local_offer, size: 20),
                      border: const OutlineInputBorder(),
                      errorText: _errorMessage,
                      isDense: true,
                    ),
                    textCapitalization: TextCapitalization.characters,
                    autocorrect: false,
                    enabled: !_isValidating && !_isApplied,
                    onSubmitted: _isValidating || _isApplied ? null : (_) => _validatePromoCode(),
                  ),
                ),
                const SizedBox(width: 8),
                if (_isApplied)
                  IconButton(
                    key: const Key('btn_remove_promo'),
                    icon: const Icon(Icons.close),
                    tooltip: l10n.subscriptionRemovePromo,
                    onPressed: _removePromoCode,
                  )
                else
                  FilledButton(
                    key: const Key('btn_apply_promo'),
                    onPressed: _isValidating ? null : _validatePromoCode,
                    child: _isValidating
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(l10n.subscriptionApply),
                  ),
              ],
            ),

            // Success message with discount info
            if (_isApplied && _discountAmount != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: CyberColors.matrixGreen.withAlpha(25),
                  borderRadius: BorderRadius.circular(Radii.xs),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.check_circle,
                      color: CyberColors.matrixGreen,
                      size: 16,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        l10n.subscriptionPromoAppliedDiscount(
                          _discountAmount!.toStringAsFixed(2),
                        ),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: CyberColors.matrixGreen,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _validatePromoCode() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      setState(() => _errorMessage = AppLocalizations.of(context).commonFieldRequired);
      return;
    }

    setState(() {
      _isValidating = true;
      _errorMessage = null;
    });

    try {
      final repo = ref.read(subscriptionRepositoryProvider);
      final result = await repo.applyPromoCode(code, widget.planId);

      if (!mounted) return;

      switch (result) {
        case Success(:final data):
          final discountAmount = data['discount_amount'] as double;
          final finalPrice = data['final_price'] as double;

          setState(() {
            _discountAmount = discountAmount;
            _finalPrice = finalPrice;
            _isApplied = true;
            _isValidating = false;
            _errorMessage = null;
          });

          // Notify parent widget
          widget.onPromoApplied(discountAmount, finalPrice);

        case Failure(:final failure):
          setState(() {
            _errorMessage = failure.message;
            _isValidating = false;
          });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isValidating = false;
      });
    }
  }

  void _removePromoCode() {
    setState(() {
      _codeController.clear();
      _discountAmount = null;
      _finalPrice = null;
      _isApplied = false;
      _errorMessage = null;
    });

    // Notify parent widget to reset price
    widget.onPromoApplied(0.0, 0.0);
  }
}
