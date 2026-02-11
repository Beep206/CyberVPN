import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/security/screen_protection.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/payment_method_picker.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/promo_code_field.dart';

// ---------------------------------------------------------------------------
// Purchase flow screen
// ---------------------------------------------------------------------------

/// Multi-step purchase flow:
/// 1. Review  - plan summary, duration, price
/// 2. Payment - select payment method, confirm
/// 3. Processing - loading animation
/// 4. Success / Error - result display
///
/// This screen is protected against screenshots to secure payment information.
class PurchaseScreen extends ConsumerStatefulWidget {
  const PurchaseScreen({
    super.key,
    required this.plan,
    this.originalPrice,
  });

  final PlanEntity plan;
  final double? originalPrice;

  @override
  ConsumerState<PurchaseScreen> createState() => _PurchaseScreenState();
}

class _PurchaseScreenState extends ConsumerState<PurchaseScreen>
    with ScreenProtection {
  int _currentStep = 0;
  PaymentMethod? _selectedPaymentMethod;

  @override
  void initState() {
    super.initState();
    unawaited(enableProtection());
    // Reset purchase state when entering the screen.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(subscriptionProvider.notifier).clearPurchaseState();
    });
  }

  @override
  void dispose() {
    unawaited(disableProtection());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    // Listen to purchase state changes to auto-advance steps.
    ref.listen<AsyncValue<SubscriptionState>>(subscriptionProvider,
        (previous, next) {
      final subState = next.value;
      if (subState == null) return;

      switch (subState.purchaseState) {
        case PurchaseState.loading:
          setState(() => _currentStep = 2);
        case PurchaseState.success:
          setState(() => _currentStep = 3);
        case PurchaseState.error:
          setState(() => _currentStep = 4);
        case PurchaseState.idle:
          break;
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.subscriptionCompletePurchase),
        leading: _currentStep <= 1
            ? const BackButton()
            : const SizedBox.shrink(),
      ),
      body: AnimatedSwitcher(
        duration: AnimDurations.normal,
        child: _buildStep(),
      ),
    );
  }

  Widget _buildStep() {
    final l10n = AppLocalizations.of(context);
    return switch (_currentStep) {
      0 => _ReviewStep(
          key: const ValueKey('review'),
          plan: widget.plan,
          originalPrice: widget.originalPrice,
          onContinue: () => setState(() => _currentStep = 1),
        ),
      1 => _PaymentStep(
          key: const ValueKey('payment'),
          selectedMethod: _selectedPaymentMethod,
          onMethodChanged: (method) =>
              setState(() => _selectedPaymentMethod = method),
          onPay: _startPurchase,
          onBack: () => setState(() => _currentStep = 0),
        ),
      2 => const _ProcessingStep(key: ValueKey('processing')),
      3 => _SuccessStep(
          key: const ValueKey('success'),
          plan: widget.plan,
          onDone: () => Navigator.of(context).popUntil((route) => route.isFirst),
        ),
      _ => _ErrorStep(
          key: const ValueKey('error'),
          message: ref.watch(subscriptionProvider).value?.purchaseError ??
              l10n.errorOccurred,
          onRetry: () {
            ref.read(subscriptionProvider.notifier).clearPurchaseState();
            setState(() => _currentStep = 1);
          },
        ),
    };
  }

  void _startPurchase() {
    if (_selectedPaymentMethod == null) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.subscriptionSelectPaymentMethodSnack)),
      );
      return;
    }
    unawaited(ref.read(subscriptionProvider.notifier).purchase(widget.plan));
  }
}

// ---------------------------------------------------------------------------
// Step 1: Review
// ---------------------------------------------------------------------------

class _ReviewStep extends StatefulWidget {
  const _ReviewStep({
    super.key,
    required this.plan,
    this.originalPrice,
    required this.onContinue,
  });

  final PlanEntity plan;
  final double? originalPrice;
  final VoidCallback onContinue;

  @override
  State<_ReviewStep> createState() => _ReviewStepState();
}

class _ReviewStepState extends State<_ReviewStep> {
  double? _discountAmount;
  double? _finalPrice;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    // Calculate displayed price based on promo code application
    final displayedPrice = _finalPrice ?? widget.plan.price;
    final hasDiscount = _discountAmount != null && _discountAmount! > 0;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(Icons.receipt_long, size: 48, color: colorScheme.primary),
          const SizedBox(height: 16),
          Text(
            l10n.subscriptionReviewYourOrder,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),

          // Plan summary card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(widget.plan.name, style: theme.textTheme.titleMedium),
                  const SizedBox(height: 8),
                  _InfoRow(
                    label: l10n.subscriptionDurationLabel,
                    value: l10n.subscriptionDurationDays(widget.plan.durationDays),
                  ),
                  _InfoRow(
                    label: l10n.subscriptionTrafficLabel,
                    value: widget.plan.trafficLimitGb > 0
                        ? l10n.subscriptionTrafficGb(widget.plan.trafficLimitGb)
                        : l10n.subscriptionUnlimited,
                  ),
                  _InfoRow(
                    label: l10n.subscriptionDevicesLabel,
                    value: '${widget.plan.maxDevices}',
                  ),
                  const Divider(height: 24),
                  // Price
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(l10n.subscriptionTotal, style: theme.textTheme.titleMedium),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          // Show original price with strikethrough if promo applied
                          if (hasDiscount)
                            Text(
                              '${widget.plan.currency} ${widget.plan.price.toStringAsFixed(2)}',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                decoration: TextDecoration.lineThrough,
                                color: colorScheme.onSurfaceVariant,
                              ),
                            ),
                          // Show final price
                          Text(
                            '${widget.plan.currency} ${displayedPrice.toStringAsFixed(2)}',
                            style: theme.textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: colorScheme.primary,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Promo code field
          PromoCodeField(
            planId: widget.plan.id,
            onPromoApplied: (discountAmount, finalPrice) {
              setState(() {
                _discountAmount = discountAmount;
                _finalPrice = finalPrice;
              });
            },
          ),

          const Spacer(),

          FilledButton(
            onPressed: widget.onContinue,
            child: Text(l10n.subscriptionContinueToPayment),
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          )),
          Text(value, style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w500,
          )),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Step 2: Payment method selection
// ---------------------------------------------------------------------------

class _PaymentStep extends StatelessWidget {
  const _PaymentStep({
    super.key,
    required this.selectedMethod,
    required this.onMethodChanged,
    required this.onPay,
    required this.onBack,
  });

  final PaymentMethod? selectedMethod;
  final ValueChanged<PaymentMethod> onMethodChanged;
  final VoidCallback onPay;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.subscriptionSelectPaymentMethod,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),

          PaymentMethodPicker(
            initialMethod: selectedMethod,
            onChanged: onMethodChanged,
          ),

          const Spacer(),

          FilledButton(
            onPressed: selectedMethod != null ? onPay : null,
            child: Text(l10n.subscriptionPayNow),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: onBack,
            child: Text(l10n.commonBack),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Step 3: Processing
// ---------------------------------------------------------------------------

class _ProcessingStep extends StatelessWidget {
  const _ProcessingStep({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 64,
            height: 64,
            child: CircularProgressIndicator(strokeWidth: 3),
          ),
          const SizedBox(height: 24),
          Text(
            l10n.subscriptionProcessing,
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            l10n.subscriptionDoNotCloseApp,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Step 4: Success
// ---------------------------------------------------------------------------

class _SuccessStep extends StatelessWidget {
  const _SuccessStep({
    super.key,
    required this.plan,
    required this.onDone,
  });

  final PlanEntity plan;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.check_circle, size: 72, color: colorScheme.primary),
          const SizedBox(height: 24),
          Text(
            l10n.subscriptionActivated,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            l10n.subscriptionActivatedMessage(plan.name),
            style: theme.textTheme.bodyLarge?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            l10n.subscriptionSecureVpnAccess(plan.durationDays),
            style: theme.textTheme.bodyMedium?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 32),
          FilledButton.icon(
            onPressed: onDone,
            icon: const Icon(Icons.vpn_key),
            label: Text(l10n.subscriptionStartUsingVpn),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error step
// ---------------------------------------------------------------------------

class _ErrorStep extends StatelessWidget {
  const _ErrorStep({
    super.key,
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 72, color: colorScheme.error),
          const SizedBox(height: 24),
          Text(
            l10n.subscriptionPaymentFailed,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: colorScheme.error,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            message,
            style: theme.textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 32),
          FilledButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: Text(l10n.subscriptionTryAgain),
          ),
        ],
      ),
    );
  }
}
