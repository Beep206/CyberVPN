import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/subscription_state.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/redeem_invite_code_dialog.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/plan_entity.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Fake notifier to supply predetermined state
// ---------------------------------------------------------------------------

class _FakeSubscriptionNotifier extends SubscriptionNotifier {
  _FakeSubscriptionNotifier(this._initialState);

  final SubscriptionState _initialState;

  @override
  Future<SubscriptionState> build() async => _initialState;

  @override
  Future<void> redeemInviteCode(String code) async {}

  @override
  void clearPurchaseState() {}
}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestableDialog({
  required SubscriptionState subscriptionState,
}) {
  return ProviderScope(
    overrides: [
      subscriptionProvider.overrideWith(
        () => _FakeSubscriptionNotifier(subscriptionState),
      ),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: RedeemInviteCodeDialog(),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('RedeemInviteCodeDialog - Rendering', () {
    testWidgets('test_renders_dialog_title', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Redeem Invite Code'), findsOneWidget);
    });

    testWidgets('test_renders_code_input_field', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
    });

    testWidgets('test_renders_redeem_button', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Redeem'), findsOneWidget);
    });

    testWidgets('test_renders_cancel_button', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Cancel'), findsOneWidget);
    });
  });

  group('RedeemInviteCodeDialog - Input Validation', () {
    testWidgets('test_code_input_converts_to_uppercase', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      final textField = find.byType(TextFormField);
      await tester.enterText(textField, 'invite123');
      await tester.pump();

      final TextField widget = tester.widget(find.byType(TextField));
      expect(widget.controller?.text, 'INVITE123');
    });

    testWidgets('test_shows_error_for_empty_code', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      final redeemButton = find.text('Redeem');
      await tester.tap(redeemButton);
      await tester.pump();

      expect(find.text('Please enter an invite code'), findsOneWidget);
    });
  });

  group('RedeemInviteCodeDialog - Redemption Flow', () {
    testWidgets('test_shows_loading_state_during_redemption', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.loading,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('test_disables_button_during_loading', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.loading,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pump();

      final redeemButton = find.widgetWithText(ElevatedButton, 'Redeem');
      final button = tester.widget<ElevatedButton>(redeemButton);
      expect(button.enabled, isFalse);
    });

    testWidgets('test_closes_dialog_on_success', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.success,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(RedeemInviteCodeDialog), findsNothing);
    });

    testWidgets('test_shows_success_snackbar', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.success,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Invite code redeemed successfully'), findsOneWidget);
    });

    testWidgets('test_shows_error_snackbar_on_failure', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.error,
        purchaseError: 'Invalid invite code',
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Invalid invite code'), findsOneWidget);
    });
  });

  group('RedeemInviteCodeDialog - Cancel Action', () {
    testWidgets('test_cancel_button_closes_dialog', (tester) async {
      const subscriptionState = SubscriptionState(
        availablePlans: <PlanEntity>[],
        purchaseState: PurchaseState.idle,
      );

      await tester.pumpWidget(
        buildTestableDialog(
          subscriptionState: subscriptionState,
        ),
      );
      await tester.pumpAndSettle();

      final cancelButton = find.text('Cancel');
      await tester.tap(cancelButton);
      await tester.pumpAndSettle();

      expect(find.byType(RedeemInviteCodeDialog), findsNothing);
    });
  });
}
