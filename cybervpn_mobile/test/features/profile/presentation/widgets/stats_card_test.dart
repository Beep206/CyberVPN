import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/profile/presentation/widgets/stats_card.dart';

void main() {
  group('StatsCard', () {
    // Helper to wrap widget with MaterialApp for theme
    Widget buildWidget(StatsCard card) {
      return MaterialApp(
        theme: cyberpunkDarkTheme(),
        home: Scaffold(
          body: card,
        ),
      );
    }

    testWidgets('displays icon, label, and value', (tester) async {
      const card = StatsCard(
        icon: Icons.star,
        label: 'Test Label',
        value: 'Test Value',
      );

      await tester.pumpWidget(buildWidget(card));

      expect(find.byIcon(Icons.star), findsOneWidget);
      expect(find.text('Test Label'), findsOneWidget);
      expect(find.text('Test Value'), findsOneWidget);
    });

    testWidgets('displays progress bar when progress is provided',
        (tester) async {
      const card = StatsCard(
        icon: Icons.data_usage,
        label: 'Traffic',
        value: '5.2 / 10 GB',
        progress: 0.52,
      );

      await tester.pumpWidget(buildWidget(card));

      expect(find.byType(LinearProgressIndicator), findsOneWidget);

      final progressIndicator = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(progressIndicator.value, 0.52);
    });

    testWidgets('does not display progress bar when progress is null',
        (tester) async {
      const card = StatsCard(
        icon: Icons.star,
        label: 'Current Plan',
        value: 'Active',
      );

      await tester.pumpWidget(buildWidget(card));

      expect(find.byType(LinearProgressIndicator), findsNothing);
    });

    testWidgets('uses custom accent color when provided', (tester) async {
      const customColor = Color(0xFFFF00FF);
      const card = StatsCard(
        icon: Icons.star,
        label: 'Test',
        value: 'Value',
        accentColor: customColor,
      );

      await tester.pumpWidget(buildWidget(card));

      final icon = tester.widget<Icon>(find.byType(Icon));
      expect(icon.color, customColor);
    });

    testWidgets('uses theme primary color as default accent', (tester) async {
      const card = StatsCard(
        icon: Icons.star,
        label: 'Test',
        value: 'Value',
      );

      await tester.pumpWidget(buildWidget(card));

      final icon = tester.widget<Icon>(find.byType(Icon));
      expect(icon.color, CyberColors.matrixGreen);
    });

    testWidgets('icon is wrapped in colored container', (tester) async {
      const card = StatsCard(
        icon: Icons.star,
        label: 'Test',
        value: 'Value',
      );

      await tester.pumpWidget(buildWidget(card));

      final container = tester.widget<Container>(
        find.ancestor(
          of: find.byType(Icon),
          matching: find.byType(Container),
        ).first,
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.borderRadius, BorderRadius.circular(Radii.sm));
    });

    testWidgets('displays full progress bar when value is 1.0', (tester) async {
      const card = StatsCard(
        icon: Icons.data_usage,
        label: 'Traffic',
        value: '10 / 10 GB',
        progress: 1.0,
      );

      await tester.pumpWidget(buildWidget(card));

      final progressIndicator = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(progressIndicator.value, 1.0);
    });

    testWidgets('displays empty progress bar when value is 0.0', (tester) async {
      const card = StatsCard(
        icon: Icons.data_usage,
        label: 'Traffic',
        value: '0 / 10 GB',
        progress: 0.0,
      );

      await tester.pumpWidget(buildWidget(card));

      final progressIndicator = tester.widget<LinearProgressIndicator>(
        find.byType(LinearProgressIndicator),
      );
      expect(progressIndicator.value, 0.0);
    });

    testWidgets('card is wrapped in Card widget', (tester) async {
      const card = StatsCard(
        icon: Icons.star,
        label: 'Test',
        value: 'Value',
      );

      await tester.pumpWidget(buildWidget(card));

      expect(find.byType(Card), findsOneWidget);
    });

    testWidgets('supports different icon types', (tester) async {
      const icons = [
        Icons.workspace_premium_outlined,
        Icons.data_usage_outlined,
        Icons.calendar_today_outlined,
        Icons.devices_outlined,
      ];

      for (final icon in icons) {
        final card = StatsCard(
          icon: icon,
          label: 'Label',
          value: 'Value',
        );

        await tester.pumpWidget(buildWidget(card));
        expect(find.byIcon(icon), findsOneWidget);

        // Clean up for next iteration
        await tester.pumpWidget(Container());
      }
    });

    testWidgets('maintains layout with long value text', (tester) async {
      const card = StatsCard(
        icon: Icons.star,
        label: 'Test',
        value: 'Very Long Value Text That Should Still Display Properly',
      );

      await tester.pumpWidget(buildWidget(card));

      expect(find.text('Very Long Value Text That Should Still Display Properly'),
             findsOneWidget);
    });
  });
}
