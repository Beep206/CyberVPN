import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/plan_card.dart';

// ---------------------------------------------------------------------------
// Duration filter options
// ---------------------------------------------------------------------------

const _durationFilters = <PlanDuration, String>{
  PlanDuration.monthly: '1 Month',
  PlanDuration.quarterly: '3 Months',
  PlanDuration.yearly: '1 Year',
  PlanDuration.lifetime: 'Lifetime',
};

// ---------------------------------------------------------------------------
// Plans catalog screen
// ---------------------------------------------------------------------------

/// Displays the list of available subscription plans with duration filtering
/// and an optional comparison table.
class PlansScreen extends ConsumerWidget {
  const PlansScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncState = ref.watch(subscriptionProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Choose Your Plan')),
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
    final plans = _filteredPlans;
    final currentPlanId = widget.subState.currentSubscription?.planId;

    return Column(
      children: [
        // -- Duration selector ------------------------------------------------
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _durationFilters.entries.map((entry) {
                final isSelected = entry.key == _selectedDuration;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
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
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: () =>
                  setState(() => _showComparison = !_showComparison),
              icon: Icon(
                _showComparison ? Icons.view_list : Icons.compare_arrows,
              ),
              label: Text(
                _showComparison ? 'Card View' : 'Compare Plans',
              ),
            ),
          ),
        ),

        // -- Content ----------------------------------------------------------
        Expanded(
          child: plans.isEmpty
              ? Center(
                  child: Text(
                    'No plans available for this duration.',
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
                      separatorBuilder: (_, _) => const SizedBox(height: 12),
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
    // Navigate to purchase screen. Uses named route if available,
    // otherwise a simple MaterialPageRoute placeholder.
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text('Purchase')),
          body: Center(child: Text('Purchase flow for: ${plan.name}')),
        ),
      ),
    );
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

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingTextStyle: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
          columns: [
            const DataColumn(label: Text('Feature')),
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
              const DataCell(Text('Price')),
              ...plans.map((p) => DataCell(Text(
                    '${p.currency} ${p.price.toStringAsFixed(2)}',
                  ))),
            ]),
            DataRow(cells: [
              const DataCell(Text('Traffic')),
              ...plans.map((p) => DataCell(Text(
                    p.trafficLimitGb > 0
                        ? '${p.trafficLimitGb} GB'
                        : 'Unlimited',
                  ))),
            ]),
            DataRow(cells: [
              const DataCell(Text('Devices')),
              ...plans.map((p) => DataCell(Text('${p.maxDevices}'))),
            ]),
            DataRow(cells: [
              const DataCell(Text('Duration')),
              ...plans.map((p) => DataCell(Text('${p.durationDays} days'))),
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
                label: const Text('Retry'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
