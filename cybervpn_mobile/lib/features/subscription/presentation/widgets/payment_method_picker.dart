import 'dart:io';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';

// ---------------------------------------------------------------------------
// Payment method enum
// ---------------------------------------------------------------------------

/// Available payment methods in the CyberVPN purchase flow.
enum PaymentMethod {
  applePay(icon: Icons.apple),
  googlePay(icon: Icons.g_mobiledata),
  cryptoBot(icon: Icons.currency_bitcoin),
  yooKassa(icon: Icons.credit_card);

  const PaymentMethod({required this.icon});

  final IconData icon;

  /// Returns the localized title for this payment method.
  String title(AppLocalizations l10n) {
    switch (this) {
      case PaymentMethod.applePay:
        return l10n.subscriptionApplePay;
      case PaymentMethod.googlePay:
        return l10n.subscriptionGooglePay;
      case PaymentMethod.cryptoBot:
        return l10n.subscriptionCryptoBot;
      case PaymentMethod.yooKassa:
        return l10n.subscriptionYooKassa;
    }
  }

  /// Returns the localized subtitle for this payment method.
  String subtitle(AppLocalizations l10n) {
    switch (this) {
      case PaymentMethod.applePay:
        return l10n.subscriptionPayWithApplePay;
      case PaymentMethod.googlePay:
        return l10n.subscriptionPayWithGooglePay;
      case PaymentMethod.cryptoBot:
        return l10n.subscriptionPayWithCrypto;
      case PaymentMethod.yooKassa:
        return l10n.subscriptionPayWithCard;
    }
  }
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
    final l10n = AppLocalizations.of(context);
    final methods = _availableMethods;

    if (methods.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            l10n.subscriptionNoPaymentMethods,
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
          l10n.subscriptionPaymentMethod,
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
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        borderRadius: BorderRadius.circular(12),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: AnimatedContainer(
            duration: AnimDurations.medium,
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
                        method.title(l10n),
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        method.subtitle(l10n),
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
