import 'package:cybervpn_mobile/core/di/providers.dart'
    show subscriptionRepositoryProvider;
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/promo_code_field.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../../../helpers/mock_repositories.dart';

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestablePromoCodeField({
  void Function(double discountAmount, double finalPrice)? onPromoApplied,
  String planId = 'plan-test-1',
  MockSubscriptionRepository? repository,
}) {
  return ProviderScope(
    overrides: [
      if (repository != null)
        subscriptionRepositoryProvider.overrideWithValue(repository),
    ],
    child: MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: PromoCodeField(
          planId: planId,
          onPromoApplied: onPromoApplied ?? (_, _) {},
        ),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('PromoCodeField - Rendering', () {
    testWidgets('test_renders_collapsed_state_initially', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      expect(find.text('Have a promo code?'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
    });

    testWidgets('test_shows_expand_icon', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.local_offer_outlined), findsOneWidget);
    });
  });

  group('PromoCodeField - Expand/Collapse', () {
    testWidgets('test_expands_on_tap', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsOneWidget);
      expect(find.byKey(const Key('btn_show_promo_field')), findsNothing);
    });

    testWidgets('test_expanded_state_exposes_apply_action', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      // Expand
      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('btn_apply_promo')), findsOneWidget);
      expect(find.byKey(const Key('input_promo_code')), findsOneWidget);
    });

    testWidgets('test_shows_input_field_when_expanded', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsOneWidget);
      expect(find.text('Apply'), findsOneWidget);
    });
  });

  group('PromoCodeField - Input Validation', () {
    testWidgets('test_code_input_accepts_text', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextField);
      await tester.enterText(textField, 'promo20');
      await tester.pump();

      final TextField widget = tester.widget(find.byType(TextField));
      expect(widget.controller?.text, 'promo20');
    });

    testWidgets('test_apply_button_disabled_when_empty', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final applyButton = find.widgetWithText(FilledButton, 'Apply');
      expect(tester.widget<FilledButton>(applyButton).enabled, isTrue);

      await tester.tap(applyButton);
      await tester.pump();
      expect(find.text('This field is required'), findsOneWidget);
    });

    testWidgets('test_apply_button_enabled_with_code', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextField);
      await tester.enterText(textField, 'CODE123');
      await tester.pump();

      final applyButton = find.widgetWithText(FilledButton, 'Apply');
      final button = tester.widget<FilledButton>(applyButton);
      expect(button.enabled, isTrue);
    });
  });

  group('PromoCodeField - Validation Callback', () {
    testWidgets('test_calls_onPromoApplied_when_apply_tapped', (tester) async {
      double? discountAmount;
      double? finalPrice;
      final repository = MockSubscriptionRepository();
      when(() => repository.applyPromoCode('SAVE20', 'plan-test-1')).thenAnswer(
        (_) async => const Success<Map<String, dynamic>>({
          'discount_amount': 2.0,
          'final_price': 7.99,
        }),
      );

      await tester.pumpWidget(
        buildTestablePromoCodeField(
          repository: repository,
          onPromoApplied: (discount, price) {
            discountAmount = discount;
            finalPrice = price;
          },
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextField);
      await tester.enterText(textField, 'SAVE20');
      await tester.pump();

      await tester.tap(find.text('Apply'));
      await tester.pumpAndSettle();

      expect(discountAmount, 2.0);
      expect(finalPrice, 7.99);
    });
  });

  group('PromoCodeField - Discount Display', () {
    testWidgets('test_shows_discount_badge_after_validation', (tester) async {
      final repository = MockSubscriptionRepository();
      when(
        () => repository.applyPromoCode('DISCOUNT10', 'plan-test-1'),
      ).thenAnswer(
        (_) async => const Success<Map<String, dynamic>>({
          'discount_amount': 10.0,
          'final_price': 89.99,
        }),
      );

      await tester.pumpWidget(
        buildTestablePromoCodeField(repository: repository),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextField);
      await tester.enterText(textField, 'DISCOUNT10');
      await tester.pump();

      await tester.tap(find.text('Apply'));
      await tester.pumpAndSettle();

      expect(find.text('Discount applied: 10.00'), findsOneWidget);
      expect(find.byKey(const Key('btn_remove_promo')), findsOneWidget);
    });
  });
}
