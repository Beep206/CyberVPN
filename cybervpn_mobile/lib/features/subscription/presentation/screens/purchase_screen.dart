import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/security/screen_protection.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/payment_method_picker.dart';

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
        title: const Text('Complete Purchase'),
        leading: _currentStep <= 1
            ? const BackButton()
            : const SizedBox.shrink(),
      ),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        child: _buildStep(),
      ),
    );
  }

  Widget _buildStep() {
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
          message: ref.read(subscriptionProvider).value?.purchaseError ??
              'An error occurred',
          onRetry: () {
            ref.read(subscriptionProvider.notifier).clearPurchaseState();
            setState(() => _currentStep = 1);
          },
        ),
    };
  }

  void _startPurchase() {
    if (_selectedPaymentMethod == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a payment method')),
      );
      return;
    }
    unawaited(ref.read(subscriptionProvider.notifier).purchase(widget.plan));
  }
}

// ---------------------------------------------------------------------------
// Step 1: Review
// ---------------------------------------------------------------------------

class _ReviewStep extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(Icons.receipt_long, size: 48, color: colorScheme.primary),
          const SizedBox(height: 16),
          Text(
            'Review Your Order',
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
                  Text(plan.name, style: theme.textTheme.titleMedium),
                  const SizedBox(height: 8),
                  _InfoRow(label: 'Duration', value: '${plan.durationDays} days'),
                  _InfoRow(
                    label: 'Traffic',
                    value: plan.trafficLimitGb > 0
                        ? '${plan.trafficLimitGb} GB'
                        : 'Unlimited',
                  ),
                  _InfoRow(label: 'Devices', value: '${plan.maxDevices}'),
                  const Divider(height: 24),
                  // Price
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Total', style: theme.textTheme.titleMedium),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          if (originalPrice != null &&
                              originalPrice! > plan.price)
                            Text(
                              '${plan.currency} ${originalPrice!.toStringAsFixed(2)}',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                decoration: TextDecoration.lineThrough,
                                color: colorScheme.onSurfaceVariant,
                              ),
                            ),
                          Text(
                            '${plan.currency} ${plan.price.toStringAsFixed(2)}',
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

          const Spacer(),

          FilledButton(
            onPressed: onContinue,
            child: const Text('Continue to Payment'),
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
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Select Payment Method',
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
            child: const Text('Pay Now'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: onBack,
            child: const Text('Back'),
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
            'Processing payment...',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Please do not close the app.',
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

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.check_circle, size: 72, color: colorScheme.primary),
          const SizedBox(height: 24),
          Text(
            'Subscription Activated!',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'You are now subscribed to ${plan.name}.',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            '${plan.durationDays} days of secure VPN access',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 32),
          FilledButton.icon(
            onPressed: onDone,
            icon: const Icon(Icons.vpn_key),
            label: const Text('Start Using VPN'),
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

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.error_outline, size: 72, color: colorScheme.error),
          const SizedBox(height: 24),
          Text(
            'Payment Failed',
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
            label: const Text('Try Again'),
          ),
        ],
      ),
    );
  }
}
