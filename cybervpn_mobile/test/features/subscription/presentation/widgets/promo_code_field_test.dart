import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/promo_code_field.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestablePromoCodeField({
  Function(String)? onValidate,
}) {
  return MaterialApp(
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: Scaffold(
      body: PromoCodeField(
        onValidate: onValidate ?? (code) {},
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
      expect(find.byType(TextFormField), findsNothing);
    });

    testWidgets('test_shows_expand_icon', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.expand_more), findsOneWidget);
    });
  });

  group('PromoCodeField - Expand/Collapse', () {
    testWidgets('test_expands_on_tap', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.byIcon(Icons.expand_less), findsOneWidget);
    });

    testWidgets('test_collapses_on_second_tap', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      // Expand
      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      // Collapse
      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsNothing);
      expect(find.byIcon(Icons.expand_more), findsOneWidget);
    });

    testWidgets('test_shows_input_field_when_expanded', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.text('Apply'), findsOneWidget);
    });
  });

  group('PromoCodeField - Input Validation', () {
    testWidgets('test_code_input_converts_to_uppercase', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextFormField);
      await tester.enterText(textField, 'promo20');
      await tester.pump();

      final TextField widget = tester.widget(find.byType(TextField));
      expect(widget.controller?.text, 'PROMO20');
    });

    testWidgets('test_apply_button_disabled_when_empty', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final applyButton = find.widgetWithText(ElevatedButton, 'Apply');
      final button = tester.widget<ElevatedButton>(applyButton);
      expect(button.enabled, isFalse);
    });

    testWidgets('test_apply_button_enabled_with_code', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextFormField);
      await tester.enterText(textField, 'CODE123');
      await tester.pump();

      final applyButton = find.widgetWithText(ElevatedButton, 'Apply');
      final button = tester.widget<ElevatedButton>(applyButton);
      expect(button.enabled, isTrue);
    });
  });

  group('PromoCodeField - Validation Callback', () {
    testWidgets('test_calls_onValidate_when_apply_tapped', (tester) async {
      String? validatedCode;

      await tester.pumpWidget(
        buildTestablePromoCodeField(
          onValidate: (code) => validatedCode = code,
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextFormField);
      await tester.enterText(textField, 'SAVE20');
      await tester.pump();

      await tester.tap(find.text('Apply'));
      await tester.pump();

      expect(validatedCode, 'SAVE20');
    });
  });

  group('PromoCodeField - Discount Display', () {
    testWidgets('test_shows_discount_badge_after_validation', (tester) async {
      await tester.pumpWidget(buildTestablePromoCodeField());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Have a promo code?'));
      await tester.pumpAndSettle();

      final textField = find.byType(TextFormField);
      await tester.enterText(textField, 'DISCOUNT10');
      await tester.pump();

      await tester.tap(find.text('Apply'));
      await tester.pumpAndSettle();

      // After validation, discount badge should appear
      expect(find.textContaining('10% off'), findsOneWidget);
    });
  });
}
