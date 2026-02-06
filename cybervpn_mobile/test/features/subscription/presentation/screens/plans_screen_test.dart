import 'dart:async';

import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/screens/plans_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _monthlyBasic = PlanEntity(
  id: 'basic-m',
  name: 'Basic',
  description: 'Basic plan',
  price: 4.99,
  currency: 'USD',
  duration: PlanDuration.monthly,
  durationDays: 30,
  maxDevices: 3,
  trafficLimitGb: 100,
);

final _monthlyPro = PlanEntity(
  id: 'pro-m',
  name: 'Pro',
  description: 'Pro plan',
  price: 9.99,
  currency: 'USD',
  duration: PlanDuration.monthly,
  durationDays: 30,
  maxDevices: 5,
  trafficLimitGb: 0, // unlimited
  isPopular: true,
);

final _yearlyBasic = PlanEntity(
  id: 'basic-y',
  name: 'Basic Annual',
  description: 'Basic yearly plan',
  price: 39.99,
  currency: 'USD',
  duration: PlanDuration.yearly,
  durationDays: 365,
  maxDevices: 3,
  trafficLimitGb: 100,
);

final _lifetimePlan = PlanEntity(
  id: 'lifetime',
  name: 'Lifetime',
  description: 'Lifetime access',
  price: 199.99,
  currency: 'USD',
  duration: PlanDuration.lifetime,
  durationDays: 9999,
  maxDevices: 10,
  trafficLimitGb: 0,
);

final _allPlans = [_monthlyBasic, _monthlyPro, _yearlyBasic, _lifetimePlan];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  required AsyncValue<SubscriptionState> asyncState,
}) {
  return ProviderScope(
    overrides: [
      subscriptionProvider.overrideWith(() => _FakeSubscriptionNotifier(asyncState)),
    ],
    child: const MaterialApp(home: PlansScreen()),
  );
}

class _FakeSubscriptionNotifier extends AsyncNotifier<SubscriptionState>
    implements SubscriptionNotifier {
  final AsyncValue<SubscriptionState> _initial;

  _FakeSubscriptionNotifier(this._initial);

  @override
  FutureOr<SubscriptionState> build() {
    state = _initial;
    return _initial.requireValue;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('PlansScreen - loading state', () {
    testWidgets('renders CircularProgressIndicator', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: const AsyncValue.loading(),
      ));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('PlansScreen - error state', () {
    testWidgets('renders error message', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.error('Network error', StackTrace.empty),
      ));
      await tester.pump();

      expect(find.textContaining('Network error'), findsOneWidget);
    });

    testWidgets('renders retry button', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.error('Server down', StackTrace.empty),
      ));
      await tester.pump();

      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('renders error icon', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.error('Oops', StackTrace.empty),
      ));
      await tester.pump();

      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });
  });

  group('PlansScreen - data state', () {
    testWidgets('renders app bar title', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: _allPlans)),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Choose Your Plan'), findsOneWidget);
    });

    testWidgets('renders duration filter chips', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: _allPlans)),
      ));
      await tester.pumpAndSettle();

      expect(find.text('1 Month'), findsOneWidget);
      expect(find.text('3 Months'), findsOneWidget);
      expect(find.text('1 Year'), findsOneWidget);
      expect(find.text('Lifetime'), findsOneWidget);
    });

    testWidgets('shows monthly plans by default', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: _allPlans)),
      ));
      await tester.pumpAndSettle();

      // Monthly plans visible
      expect(find.text('Basic'), findsOneWidget);
      expect(find.text('Pro'), findsOneWidget);

      // Yearly/lifetime plans not visible in card view (different duration)
      expect(find.text('Basic Annual'), findsNothing);
    });

    testWidgets('renders Compare Plans button', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: _allPlans)),
      ));
      await tester.pumpAndSettle();

      expect(find.text('Compare Plans'), findsOneWidget);
    });

    testWidgets('switching duration filter shows correct plans', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: _allPlans)),
      ));
      await tester.pumpAndSettle();

      // Tap "1 Year" chip
      await tester.tap(find.text('1 Year'));
      await tester.pumpAndSettle();

      expect(find.text('Basic Annual'), findsOneWidget);
      // Monthly plans should be hidden
      expect(find.text('Basic'), findsNothing);
    });

    testWidgets('empty duration shows empty message', (tester) async {
      // Only monthly plans — quarterly filter should be empty
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: [_monthlyBasic])),
      ));
      await tester.pumpAndSettle();

      // Tap "3 Months" chip
      await tester.tap(find.text('3 Months'));
      await tester.pumpAndSettle();

      expect(find.text('No plans available for this duration.'), findsOneWidget);
    });

    testWidgets('tapping Compare Plans toggles to comparison table', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: _allPlans)),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Compare Plans'));
      await tester.pumpAndSettle();

      // After toggling, button label changes to "Card View"
      expect(find.text('Card View'), findsOneWidget);
      // Comparison table headers
      expect(find.text('Feature'), findsOneWidget);
      expect(find.text('Price'), findsOneWidget);
      expect(find.text('Traffic'), findsOneWidget);
      expect(find.text('Devices'), findsOneWidget);
    });

    testWidgets('comparison table shows plan data', (tester) async {
      await tester.pumpWidget(_buildTestWidget(
        asyncState: AsyncValue.data(SubscriptionState(availablePlans: _allPlans)),
      ));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Compare Plans'));
      await tester.pumpAndSettle();

      // Monthly plans are shown in comparison
      expect(find.text('USD 4.99'), findsOneWidget);
      expect(find.text('USD 9.99'), findsOneWidget);
      expect(find.text('100 GB'), findsOneWidget);
      expect(find.text('Unlimited'), findsOneWidget);
    });
  });
}
