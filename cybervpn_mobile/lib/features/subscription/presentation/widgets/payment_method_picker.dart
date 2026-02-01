import 'dart:io';

import 'package:flutter/material.dart';

// ---------------------------------------------------------------------------
// Payment method enum
// ---------------------------------------------------------------------------

/// Available payment methods in the CyberVPN purchase flow.
enum PaymentMethod {
  applePay(
    title: 'Apple Pay',
    subtitle: 'Pay with Apple Pay',
    icon: Icons.apple,
  ),
  googlePay(
    title: 'Google Pay',
    subtitle: 'Pay with Google Pay',
    icon: Icons.g_mobiledata,
  ),
  cryptoBot(
    title: 'CryptoBot',
    subtitle: 'Pay with Crypto',
    icon: Icons.currency_bitcoin,
  ),
  yooKassa(
    title: 'YooKassa',
    subtitle: 'Pay with Card (RU)',
    icon: Icons.credit_card,
  );

  const PaymentMethod({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;
}

// ---------------------------------------------------------------------------
// PaymentMethodPicker widget
// ---------------------------------------------------------------------------

/// Displays a selectable list of payment method cards.
///
/// On iOS, Apple Pay is shown and Google Pay is hidden.
/// On Android, Google Pay is shown and Apple Pay is hidden.
/// If [allowExternalPayments] is `false` on iOS, CryptoBot and YooKassa
/// are also hidden (App Store guideline compliance).
class PaymentMethodPicker extends StatefulWidget {
  const PaymentMethodPicker({
    super.key,
    this.initialMethod,
    this.onChanged,
    this.allowExternalPayments = true,
  });

  /// The initially selected payment method.
  final PaymentMethod? initialMethod;

  /// Called when the user selects a different payment method.
  final ValueChanged<PaymentMethod>? onChanged;

  /// When `false` on iOS, external payment methods (CryptoBot, YooKassa)
  /// are hidden to comply with App Store guidelines.
  final bool allowExternalPayments;

  @override
  State<PaymentMethodPicker> createState() => _PaymentMethodPickerState();
}

class _PaymentMethodPickerState extends State<PaymentMethodPicker> {
  PaymentMethod? _selected;

  @override
  void initState() {
    super.initState();
    _selected = widget.initialMethod;
  }

  List<PaymentMethod> get _availableMethods {
    final bool isIOS = Platform.isIOS;
    final bool isAndroid = Platform.isAndroid;

    return PaymentMethod.values.where((method) {
      // Platform-specific store pay.
      if (method == PaymentMethod.applePay && !isIOS) return false;
      if (method == PaymentMethod.googlePay && !isAndroid) return false;

      // External payment restriction on iOS.
      if (isIOS && !widget.allowExternalPayments) {
        if (method == PaymentMethod.cryptoBot ||
            method == PaymentMethod.yooKassa) {
          return false;
        }
      }

      return true;
    }).toList();
  }

  void _select(PaymentMethod method) {
    setState(() => _selected = method);
    widget.onChanged?.call(method);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final methods = _availableMethods;

    if (methods.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'No payment methods available.',
            style: theme.textTheme.bodyLarge,
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Payment Method',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),
        ...methods.map((method) => _PaymentMethodCard(
              method: method,
              isSelected: _selected == method,
              onTap: () => _select(method),
            )),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Individual payment method card
// ---------------------------------------------------------------------------

class _PaymentMethodCard extends StatelessWidget {
  const _PaymentMethodCard({
    required this.method,
    required this.isSelected,
    required this.onTap,
  });

  final PaymentMethod method;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        borderRadius: BorderRadius.circular(12),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isSelected
                    ? colorScheme.primary
                    : colorScheme.outlineVariant,
                width: isSelected ? 2 : 1,
              ),
              color: isSelected
                  ? colorScheme.primaryContainer.withValues(alpha: 0.3)
                  : colorScheme.surface,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: [
                Icon(
                  method.icon,
                  size: 28,
                  color: isSelected
                      ? colorScheme.primary
                      : colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        method.title,
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        method.subtitle,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                if (isSelected)
                  Icon(Icons.check_circle, color: colorScheme.primary)
                else
                  Icon(
                    Icons.radio_button_unchecked,
                    color: colorScheme.outlineVariant,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
