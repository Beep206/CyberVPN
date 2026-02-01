import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/profile/presentation/widgets/usage_ring.dart';

void main() {
  group('UsageRing', () {
    // Helper to wrap widget with MaterialApp for theme
    Widget buildWidget(UsageRing ring) {
      return MaterialApp(
        theme: cyberpunkDarkTheme(),
        home: Scaffold(
          body: Center(child: ring),
        ),
      );
    }

    testWidgets('displays circular progress indicators', (tester) async {
      const ring = UsageRing(
        usedValue: 5.2,
        totalValue: 10.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      // Should have 2 circular progress indicators: background and progress
      expect(find.byType(CircularProgressIndicator), findsNWidgets(2));
    });

    testWidgets('displays default center text with used/total values',
        (tester) async {
      const ring = UsageRing(
        usedValue: 5.2,
        totalValue: 10.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      expect(find.text('5.2 / 10'), findsOneWidget);
    });

    testWidgets('displays custom center text when provided', (tester) async {
      const ring = UsageRing(
        usedValue: 5.2,
        totalValue: 10.0,
        centerText: 'Custom Text',
      );

      await tester.pumpWidget(buildWidget(ring));

      expect(find.text('Custom Text'), findsOneWidget);
      expect(find.text('5.2 / 10'), findsNothing);
    });

    testWidgets('displays subtitle when provided', (tester) async {
      const ring = UsageRing(
        usedValue: 5.2,
        totalValue: 10.0,
        subtitle: 'GB Used',
      );

      await tester.pumpWidget(buildWidget(ring));

      expect(find.text('GB Used'), findsOneWidget);
    });

    testWidgets('does not display subtitle when null', (tester) async {
      const ring = UsageRing(
        usedValue: 5.2,
        totalValue: 10.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      // Only one Text widget should be present (the center text)
      expect(find.byType(Text), findsOneWidget);
    });

    testWidgets('calculates correct ratio for 50% progress', (tester) async {
      const ring = UsageRing(
        usedValue: 50.0,
        totalValue: 100.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      // Find the progress indicator (not the background one)
      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );

      // The second one is the progress ring (first is background)
      final progressRing = progressIndicators.elementAt(1);
      expect(progressRing.value, 0.5);
    });

    testWidgets('calculates correct ratio for 100% progress', (tester) async {
      const ring = UsageRing(
        usedValue: 100.0,
        totalValue: 100.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      final progressRing = progressIndicators.elementAt(1);
      expect(progressRing.value, 1.0);
    });

    testWidgets('clamps ratio to 0.0 when used > total', (tester) async {
      const ring = UsageRing(
        usedValue: 150.0,
        totalValue: 100.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      final progressRing = progressIndicators.elementAt(1);
      // Should be clamped to 1.0
      expect(progressRing.value, 1.0);
    });

    testWidgets('handles zero total value safely', (tester) async {
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 0.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );
      final progressRing = progressIndicators.elementAt(1);
      expect(progressRing.value, 0.0);
    });

    testWidgets('uses custom size when provided', (tester) async {
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 10.0,
        size: 200,
      );

      await tester.pumpWidget(buildWidget(ring));

      final sizedBoxes = tester.widgetList<SizedBox>(find.byType(SizedBox));
      // First SizedBox is the outer container
      final outerBox = sizedBoxes.first;
      expect(outerBox.width, 200);
      expect(outerBox.height, 200);
    });

    testWidgets('uses default size 160 when not specified', (tester) async {
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 10.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      final sizedBoxes = tester.widgetList<SizedBox>(find.byType(SizedBox));
      final outerBox = sizedBoxes.first;
      expect(outerBox.width, 160);
      expect(outerBox.height, 160);
    });

    testWidgets('uses custom stroke width when provided', (tester) async {
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 10.0,
        strokeWidth: 16,
      );

      await tester.pumpWidget(buildWidget(ring));

      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );

      for (final indicator in progressIndicators) {
        expect(indicator.strokeWidth, 16);
      }
    });

    testWidgets('uses default stroke width 12 when not specified',
        (tester) async {
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 10.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );

      for (final indicator in progressIndicators) {
        expect(indicator.strokeWidth, 12);
      }
    });

    testWidgets('uses custom accent color when provided', (tester) async {
      const customColor = Color(0xFFFF00FF);
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 10.0,
        accentColor: customColor,
      );

      await tester.pumpWidget(buildWidget(ring));

      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );

      // Second indicator is the progress ring
      final progressRing = progressIndicators.elementAt(1);
      final colorAnimation = progressRing.valueColor as AlwaysStoppedAnimation<Color>;
      expect(colorAnimation.value, customColor);
    });

    testWidgets('uses theme primary color as default accent', (tester) async {
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 10.0,
      );

      await tester.pumpWidget(buildWidget(ring));

      final progressIndicators = tester.widgetList<CircularProgressIndicator>(
        find.byType(CircularProgressIndicator),
      );

      final progressRing = progressIndicators.elementAt(1);
      final colorAnimation = progressRing.valueColor as AlwaysStoppedAnimation<Color>;
      expect(colorAnimation.value, CyberColors.matrixGreen);
    });

    testWidgets('displays multiple text widgets when subtitle provided',
        (tester) async {
      const ring = UsageRing(
        usedValue: 5.0,
        totalValue: 10.0,
        centerText: 'Main',
        subtitle: 'Sub',
      );

      await tester.pumpWidget(buildWidget(ring));

      expect(find.text('Main'), findsOneWidget);
      expect(find.text('Sub'), findsOneWidget);
    });

    testWidgets('formats decimal values correctly', (tester) async {
      const ring = UsageRing(
        usedValue: 5.234567,
        totalValue: 10.987654,
      );

      await tester.pumpWidget(buildWidget(ring));

      // Used value should be 1 decimal, total should be 0 decimals
      expect(find.text('5.2 / 11'), findsOneWidget);
    });
  });
}
