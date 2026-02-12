import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart' show AppFailure;
import 'package:cybervpn_mobile/features/wallet/presentation/providers/wallet_provider.dart';

// ---------------------------------------------------------------------------
// WithdrawBottomSheet
// ---------------------------------------------------------------------------

/// Bottom sheet for wallet withdrawal with amount input and method selection.
///
/// Shows amount input field and withdrawal method selection.
/// On confirmation, calls POST /wallet/withdraw and closes with result.
class WithdrawBottomSheet extends ConsumerStatefulWidget {
  const WithdrawBottomSheet({
    super.key,
    required this.maxBalance,
  });

  final double maxBalance;

  /// Shows the withdraw bottom sheet.
  ///
  /// Returns `true` if withdrawal was successfully initiated, `false` otherwise.
  static Future<bool?> show(BuildContext context, double maxBalance) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (context) => WithdrawBottomSheet(maxBalance: maxBalance),
    );
  }

  @override
  ConsumerState<WithdrawBottomSheet> createState() => _WithdrawBottomSheetState();
}

class _WithdrawBottomSheetState extends ConsumerState<WithdrawBottomSheet> {
  bool _isWithdrawing = false;
  final _formKey = GlobalKey<FormState>();
  final _amountController = TextEditingController();
  String _selectedMethod = 'crypto'; // Default method

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _confirmWithdraw() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isWithdrawing = true);

    final amount = double.parse(_amountController.text);
    final method = _selectedMethod;
    final details = <String, dynamic>{
      'method': method,
      'amount': amount,
    };

    final result = await ref.read(walletRepositoryProvider).withdrawFunds(
      amount: amount,
      method: method,
      details: details,
    );

    if (!mounted) return;

    setState(() => _isWithdrawing = false);

    result.when(
      success: (_) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Withdrawal initiated successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        Navigator.of(context).pop(true);
      },
      failure: (AppFailure failure) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(failure.message),
            backgroundColor: Colors.red,
          ),
        );
      },
    );
  }

  String? _validateAmount(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please enter an amount';
    }

    final amount = double.tryParse(value);
    if (amount == null || amount <= 0) {
      return 'Please enter a valid amount greater than 0';
    }

    if (amount > widget.maxBalance) {
      return 'Insufficient balance. Maximum: \$${widget.maxBalance.toStringAsFixed(2)}';
    }

    return null;
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
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Wallet icon
              Icon(
                Icons.account_balance_wallet,
                size: 64,
                color: colorScheme.primary,
              ),
              const SizedBox(height: 16),

              // Title
              Text(
                l10n.walletWithdraw,
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),

              // Available balance
              Text(
                'Available Balance: \$${widget.maxBalance.toStringAsFixed(2)}',
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),

              // Amount input
              TextFormField(
                controller: _amountController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,2}')),
                ],
                decoration: const InputDecoration(
                  labelText: 'Amount',
                  hintText: '0.00',
                  prefixIcon: Icon(Icons.attach_money),
                  border: OutlineInputBorder(),
                ),
                validator: _validateAmount,
              ),
              const SizedBox(height: 16),

              // Method selection
              DropdownButtonFormField<String>(
                initialValue: _selectedMethod,
                decoration: const InputDecoration(
                  labelText: 'Withdrawal Method',
                  prefixIcon: Icon(Icons.payment),
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(
                    value: 'crypto',
                    child: Text('Cryptocurrency'),
                  ),
                  DropdownMenuItem(
                    value: 'bank',
                    child: Text('Bank Transfer'),
                  ),
                  DropdownMenuItem(
                    value: 'paypal',
                    child: Text('PayPal'),
                  ),
                ],
                onChanged: (value) {
                  if (value != null) {
                    setState(() => _selectedMethod = value);
                  }
                },
              ),
              const SizedBox(height: 24),

              // Withdraw button
              FilledButton(
                key: const Key('btn_confirm_withdraw'),
                onPressed: _isWithdrawing ? null : _confirmWithdraw,
                child: _isWithdrawing
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(l10n.walletWithdraw),
              ),
              const SizedBox(height: 12),

              // Cancel button
              OutlinedButton(
                key: const Key('btn_cancel_withdraw'),
                onPressed: _isWithdrawing ? null : () => Navigator.of(context).pop(false),
                child: Text(l10n.cancel),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
