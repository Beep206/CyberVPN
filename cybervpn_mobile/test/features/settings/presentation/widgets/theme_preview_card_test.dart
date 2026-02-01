import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/app/theme/theme_provider.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/theme_preview_card.dart';

void main() {
  group('ThemePreviewCard', () {
    // Helper to wrap widget with MaterialApp for theme
    Widget buildWidget(ThemePreviewCard card) {
      return MaterialApp(
        theme: cyberpunkDarkTheme(),
        home: Scaffold(
          body: card,
        ),
      );
    }

    testWidgets('renders with correct dimensions (120x80)', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      expect(container.constraints?.minWidth, 120);
      expect(container.constraints?.minHeight, 80);
    });

    testWidgets('Cyberpunk theme shows deepNavy background', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));

      // Find the background ColoredBox (first one in Stack)
      final coloredBoxes = tester.widgetList<ColoredBox>(
        find.descendant(
          of: find.byType(ThemePreviewCard),
          matching: find.byType(ColoredBox),
        ),
      );

      expect(coloredBoxes.first.color, CyberColors.deepNavy);
    });

    testWidgets('Material You theme shows light surface background',
        (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.materialYou,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));

      // Find the background ColoredBox (first one in Stack)
      final coloredBoxes = tester.widgetList<ColoredBox>(
        find.descendant(
          of: find.byType(ThemePreviewCard),
          matching: find.byType(ColoredBox),
        ),
      );

      // Material You uses light surface color
      expect(coloredBoxes.first.color, const Color(0xFFFCFCFC));
    });

    testWidgets('selected state shows 2px border', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: true,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));
      await tester.pump(); // Allow animation to settle

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.border, isA<Border>());

      final border = decoration.border as Border;
      expect(border.top.width, 2.0);
    });

    testWidgets('unselected state shows 1px border', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));
      await tester.pump(); // Allow animation to settle

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.border, isA<Border>());

      final border = decoration.border as Border;
      expect(border.top.width, 1.0);
    });

    testWidgets('selected state uses accent color for border', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: true,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));
      await tester.pump(); // Allow animation to settle

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      final decoration = container.decoration as BoxDecoration;
      final border = decoration.border as Border;

      // Cyberpunk uses neonCyan as accent
      expect(border.top.color, CyberColors.neonCyan);
    });

    testWidgets('unselected state uses subtle grey border', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));
      await tester.pump(); // Allow animation to settle

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      final decoration = container.decoration as BoxDecoration;
      final border = decoration.border as Border;

      // Unselected uses grey with opacity
      expect(border.top.color.alpha, lessThan(255));
    });

    testWidgets('onTap callback is invoked when tapped', (tester) async {
      var tapped = false;
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {
          tapped = true;
        },
      );

      await tester.pumpWidget(buildWidget(card));
      await tester.tap(find.byType(ThemePreviewCard));
      await tester.pump();

      expect(tapped, true);
    });

    testWidgets('selected state shows glow effect (BoxShadow)', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: true,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));
      await tester.pump(); // Allow animation to settle

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.boxShadow, isNotNull);
      expect(decoration.boxShadow!.length, greaterThan(0));
      expect(decoration.boxShadow!.first.blurRadius, 8.0);
    });

    testWidgets('unselected state has no glow effect', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));
      await tester.pump(); // Allow animation to settle

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      final decoration = container.decoration as BoxDecoration;
      expect(decoration.boxShadow, isNull);
    });

    testWidgets('preview contains Stack with positioned elements',
        (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));

      // Verify Stack structure
      expect(
        find.descendant(
          of: find.byType(ThemePreviewCard),
          matching: find.byType(Stack),
        ),
        findsOneWidget,
      );

      // Verify positioned elements exist (background, button, accent bar)
      expect(
        find.descendant(
          of: find.byType(ThemePreviewCard),
          matching: find.byType(Positioned),
        ),
        findsNWidgets(3), // Background, button, accent bar
      );
    });

    testWidgets('all 4 theme combinations render without error',
        (tester) async {
      final themes = [
        AppThemeMode.cyberpunk,
        AppThemeMode.materialYou,
      ];

      final selections = [true, false];

      for (final theme in themes) {
        for (final isSelected in selections) {
          final card = ThemePreviewCard(
            theme: theme,
            isSelected: isSelected,
            onTap: () {},
          );

          await tester.pumpWidget(buildWidget(card));
          expect(find.byType(ThemePreviewCard), findsOneWidget);

          // Clean up for next iteration
          await tester.pumpWidget(Container());
        }
      }
    });

    testWidgets('uses AnimatedContainer for smooth transitions',
        (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));

      expect(find.byType(AnimatedContainer), findsOneWidget);

      final container = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );

      expect(container.duration, AnimDurations.fast);
    });

    testWidgets('wraps content in GestureDetector', (tester) async {
      final card = ThemePreviewCard(
        theme: AppThemeMode.cyberpunk,
        isSelected: false,
        onTap: () {},
      );

      await tester.pumpWidget(buildWidget(card));

      expect(find.byType(GestureDetector), findsOneWidget);
    });
  });
}
