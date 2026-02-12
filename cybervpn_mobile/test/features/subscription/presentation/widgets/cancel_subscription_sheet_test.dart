import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/cancel_subscription_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestableCancelSheet({
  required AsyncValue<SubscriptionState> subscriptionStateOverride,
}) {
  return ProviderScope(
    overrides: [
      subscriptionProvider.overrideWith(
        (ref) => subscriptionStateOverride,
      ),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: CancelSubscriptionSheet(),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('CancelSubscriptionSheet - Rendering', () {
    testWidgets('test_renders_confirmation_title', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Cancel Subscription?'), findsOneWidget);
    });

    testWidgets('test_renders_warning_message', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.textContaining('You will lose access'),
        findsOneWidget,
      );
    });

    testWidgets('test_renders_cancel_button', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Cancel Subscription'), findsOneWidget);
    });

    testWidgets('test_renders_keep_subscription_button', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Keep Subscription'), findsOneWidget);
    });
  });

  group('CancelSubscriptionSheet - Cancel Flow', () {
    testWidgets('test_shows_loading_during_cancellation', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.loading,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('test_disables_buttons_during_loading', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.loading,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pump();

      final cancelButton =
          find.widgetWithText(ElevatedButton, 'Cancel Subscription');
      final button = tester.widget<ElevatedButton>(cancelButton);
      expect(button.enabled, isFalse);
    });

    testWidgets('test_closes_sheet_on_success', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.success,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(CancelSubscriptionSheet), findsNothing);
    });

    testWidgets('test_shows_success_snackbar', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.success,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Subscription cancelled'), findsOneWidget);
    });

    testWidgets('test_shows_error_snackbar_on_failure', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.error,
        purchaseError: 'Failed to cancel subscription',
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Failed to cancel subscription'), findsOneWidget);
    });
  });

  group('CancelSubscriptionSheet - Keep Subscription Action', () {
    testWidgets('test_keep_button_closes_sheet', (tester) async {
      const subscriptionState = SubscriptionState(
        plans: [],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionStateOverride: const AsyncValue.data(subscriptionState),
        ),
      );
      await tester.pumpAndSettle();

      final keepButton = find.text('Keep Subscription');
      await tester.tap(keepButton);
      await tester.pumpAndSettle();

      expect(find.byType(CancelSubscriptionSheet), findsNothing);
    });
  });
}
