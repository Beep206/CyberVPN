import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_provider.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/widgets/notification_badge.dart';

void main() {
  /// Helper to build widget under test with a mocked [unreadCountProvider].
  Widget buildTestWidget({required int unreadCount}) {
    return ProviderScope(
      overrides: [
        unreadCountProvider.overrideWith((ref) => unreadCount),
      ],
      child: const MaterialApp(
        home: Scaffold(
          body: Center(
            child: NotificationBadge(),
          ),
        ),
      ),
    );
  }

  group('NotificationBadge', () {
    testWidgets('hides when count is 0', (tester) async {
      await tester.pumpWidget(buildTestWidget(unreadCount: 0));

      // AnimatedScale should scale to 0.0 when count is 0
      final animatedScale = tester.widget<AnimatedScale>(
        find.byType(AnimatedScale),
      );
      expect(animatedScale.scale, equals(0.0));

      // Badge content should be a SizedBox.shrink
      expect(find.byType(SizedBox), findsOneWidget);
      expect(find.text('0'), findsNothing);
    });

    testWidgets('shows count when count is 5', (tester) async {
      await tester.pumpWidget(buildTestWidget(unreadCount: 5));

      // AnimatedScale should scale to 1.0 when count > 0
      final animatedScale = tester.widget<AnimatedScale>(
        find.byType(AnimatedScale),
      );
      expect(animatedScale.scale, equals(1.0));

      // Badge should display '5'
      expect(find.text('5'), findsOneWidget);
    });

    testWidgets('shows "99+" when count is 100', (tester) async {
      await tester.pumpWidget(buildTestWidget(unreadCount: 100));

      // Badge should display '99+' instead of '100'
      expect(find.text('99+'), findsOneWidget);
      expect(find.text('100'), findsNothing);
    });

    testWidgets('shows "99+" when count is 150', (tester) async {
      await tester.pumpWidget(buildTestWidget(unreadCount: 150));

      // Badge should display '99+' for any count > 99
      expect(find.text('99+'), findsOneWidget);
    });

    testWidgets('shows count when count is exactly 99', (tester) async {
      await tester.pumpWidget(buildTestWidget(unreadCount: 99));

      // Badge should display '99' (not '99+') when count is exactly 99
      expect(find.text('99'), findsOneWidget);
      expect(find.text('99+'), findsNothing);
    });

    testWidgets('has correct styling', (tester) async {
      await tester.pumpWidget(buildTestWidget(unreadCount: 5));

      // Find the Container that wraps the badge
      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(NotificationBadge),
          matching: find.byType(Container),
        ),
      );

      // Verify decoration
      final decoration = container.decoration as BoxDecoration;
      expect(decoration.shape, equals(BoxShape.circle));

      // Verify text style
      final text = tester.widget<Text>(find.text('5'));
      expect(text.style?.color, equals(Colors.white));
      expect(text.style?.fontWeight, equals(FontWeight.bold));
      expect(text.style?.fontSize, equals(11));
    });

    testWidgets('animates when count changes from 0 to non-zero',
        (tester) async {
      // Start with count 0
      await tester.pumpWidget(buildTestWidget(unreadCount: 0));

      final animatedScaleBefore = tester.widget<AnimatedScale>(
        find.byType(AnimatedScale),
      );
      expect(animatedScaleBefore.scale, equals(0.0));

      // Change count to 3
      await tester.pumpWidget(buildTestWidget(unreadCount: 3));

      final animatedScaleAfter = tester.widget<AnimatedScale>(
        find.byType(AnimatedScale),
      );
      expect(animatedScaleAfter.scale, equals(1.0));

      // Verify animation duration and curve
      expect(animatedScaleAfter.duration, equals(const Duration(milliseconds: 250)));
      expect(animatedScaleAfter.curve, equals(Curves.easeInOut));

      // Pump animation to completion
      await tester.pumpAndSettle();

      // Badge should show '3'
      expect(find.text('3'), findsOneWidget);
    });

    testWidgets('animates when count changes from non-zero to 0',
        (tester) async {
      // Start with count 7
      await tester.pumpWidget(buildTestWidget(unreadCount: 7));

      final animatedScaleBefore = tester.widget<AnimatedScale>(
        find.byType(AnimatedScale),
      );
      expect(animatedScaleBefore.scale, equals(1.0));
      expect(find.text('7'), findsOneWidget);

      // Change count to 0
      await tester.pumpWidget(buildTestWidget(unreadCount: 0));

      final animatedScaleAfter = tester.widget<AnimatedScale>(
        find.byType(AnimatedScale),
      );
      expect(animatedScaleAfter.scale, equals(0.0));

      // Pump animation to completion
      await tester.pumpAndSettle();

      // Badge should be hidden
      expect(find.text('7'), findsNothing);
    });

    testWidgets('updates displayed count when count changes', (tester) async {
      // Start with count 3
      await tester.pumpWidget(buildTestWidget(unreadCount: 3));
      expect(find.text('3'), findsOneWidget);

      // Change to count 8
      await tester.pumpWidget(buildTestWidget(unreadCount: 8));
      await tester.pumpAndSettle();
      expect(find.text('8'), findsOneWidget);
      expect(find.text('3'), findsNothing);

      // Change to count 100 (should show '99+')
      await tester.pumpWidget(buildTestWidget(unreadCount: 100));
      await tester.pumpAndSettle();
      expect(find.text('99+'), findsOneWidget);
      expect(find.text('8'), findsNothing);
    });
  });
}
