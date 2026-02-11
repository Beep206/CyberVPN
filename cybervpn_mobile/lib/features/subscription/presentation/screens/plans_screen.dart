import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/plan_card.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/redeem_invite_code_dialog.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/trial_card.dart';

// ---------------------------------------------------------------------------
// Plans catalog screen
// ---------------------------------------------------------------------------

/// Displays the list of available subscription plans with duration filtering
/// and an optional comparison table.
class PlansScreen extends ConsumerWidget {
  const PlansScreen({super.key});

  /// Shows the redeem invite code dialog.
  static void _showRedeemDialog(BuildContext context) {
    unawaited(showDialog<bool>(
      context: context,
      builder: (context) => const RedeemInviteCodeDialog(),
    ));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncState = ref.watch(subscriptionProvider);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.subscriptionChooseYourPlan),
        actions: [
          IconButton(
            key: const Key('btn_redeem_invite_code'),
            icon: const Icon(Icons.card_giftcard),
            tooltip: l10n.subscriptionRedeemInviteCode,
            onPressed: () => _showRedeemDialog(context),
          ),
        ],
      ),
      body: asyncState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorBody(
          message: error.toString(),
          onRetry: () => ref.invalidate(subscriptionProvider),
        ),
        data: (subState) => _PlansBody(subState: subState),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Plans body (data loaded)
// ---------------------------------------------------------------------------

class _PlansBody extends StatefulWidget {
  const _PlansBody({required this.subState});

  final SubscriptionState subState;

  @override
  State<_PlansBody> createState() => _PlansBodyState();
}

class _PlansBodyState extends State<_PlansBody> {
  PlanDuration _selectedDuration = PlanDuration.monthly;
  bool _showComparison = false;

  List<PlanEntity> get _filteredPlans => widget.subState.availablePlans
      .where((p) => p.duration == _selectedDuration)
      .toList();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final plans = _filteredPlans;
    final currentPlanId = widget.subState.currentSubscription?.planId;

    // Duration filter options — built from l10n
    final durationFilters = <PlanDuration, String>{
      PlanDuration.monthly: l10n.subscriptionDuration1Month,
      PlanDuration.quarterly: l10n.subscriptionDuration3Months,
      PlanDuration.yearly: l10n.subscriptionDuration1Year,
      PlanDuration.lifetime: l10n.subscriptionLifetime,
    };

    return Column(
      children: [
        // -- Duration selector ------------------------------------------------
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: durationFilters.entries.map((entry) {
                final isSelected = entry.key == _selectedDuration;
                return Padding(
                  padding: const EdgeInsetsDirectional.only(end: 8),
                  child: ChoiceChip(
                    label: Text(entry.value),
                    selected: isSelected,
                    onSelected: (_) =>
                        setState(() => _selectedDuration = entry.key),
                  ),
                );
              }).toList(),
            ),
          ),
        ),

        // -- Compare toggle ---------------------------------------------------
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Align(
            alignment: AlignmentDirectional.centerEnd,
            child: TextButton.icon(
              onPressed: () =>
                  setState(() => _showComparison = !_showComparison),
              icon: Icon(
                _showComparison ? Icons.view_list : Icons.compare_arrows,
              ),
              label: Text(
                _showComparison
                    ? l10n.subscriptionCardView
                    : l10n.subscriptionComparePlans,
              ),
            ),
          ),
        ),

        // -- Trial card -------------------------------------------------------
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16),
          child: TrialCard(),
        ),

        // -- Content ----------------------------------------------------------
        Expanded(
          child: plans.isEmpty
              ? Center(
                  child: Text(
                    l10n.subscriptionNoPlansForDuration,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                )
              : _showComparison
                  ? _ComparisonTable(
                      plans: plans,
                      currentPlanId: currentPlanId,
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                      itemCount: plans.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final plan = plans[index];
                        return PlanCard(
                          plan: plan,
                          selectedDuration: _selectedDuration,
                          isCurrentPlan: plan.id == currentPlanId,
                          onSubscribe: () => _navigateToPurchase(context, plan),
                        );
                      },
                    ),
        ),
      ],
    );
  }

  void _navigateToPurchase(BuildContext context, PlanEntity plan) {
    final l10n = AppLocalizations.of(context);
    // Navigate to purchase screen. Uses named route if available,
    // otherwise a simple MaterialPageRoute placeholder.
    unawaited(Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(l10n.subscriptionPurchase)),
          body: Center(child: Text(l10n.subscriptionPurchaseFlowFor(plan.name))),
        ),
      ),
    ));
  }
}

// ---------------------------------------------------------------------------
// Comparison data table
// ---------------------------------------------------------------------------

class _ComparisonTable extends StatelessWidget {
  const _ComparisonTable({
    required this.plans,
    this.currentPlanId,
  });

  final List<PlanEntity> plans;
  final String? currentPlanId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingTextStyle: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
          columns: [
            DataColumn(label: Text(l10n.subscriptionFeatureLabel)),
            ...plans.map((p) => DataColumn(
                  label: Text(
                    p.id == currentPlanId ? '${p.name} \u2713' : p.name,
                    style: p.id == currentPlanId
                        ? TextStyle(color: colorScheme.primary)
                        : null,
                  ),
                )),
          ],
          rows: [
            DataRow(cells: [
              DataCell(Text(l10n.subscriptionPriceLabel)),
              ...plans.map((p) => DataCell(Text(
                    '${p.currency} ${p.price.toStringAsFixed(2)}',
                  ))),
            ]),
            DataRow(cells: [
              DataCell(Text(l10n.subscriptionTrafficLabel)),
              ...plans.map((p) => DataCell(Text(
                    p.trafficLimitGb > 0
                        ? l10n.subscriptionTrafficGb(p.trafficLimitGb)
                        : l10n.subscriptionUnlimited,
                  ))),
            ]),
            DataRow(cells: [
              DataCell(Text(l10n.subscriptionDevicesLabel)),
              ...plans.map((p) => DataCell(Text('${p.maxDevices}'))),
            ]),
            DataRow(cells: [
              DataCell(Text(l10n.subscriptionDurationLabel)),
              ...plans.map((p) => DataCell(Text(l10n.subscriptionDurationDays(p.durationDays)))),
            ]),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error body
// ---------------------------------------------------------------------------

class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline,
              size: 48,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: Text(l10n.retry),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
