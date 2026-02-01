import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/shared/widgets/feature_tooltip.dart';

void main() {
  group('FeatureTooltip', () {
    testWidgets('renders with correct message text', (tester) async {
      final targetKey = GlobalKey();
      bool dismissed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                // Target widget
                Center(
                  child: ElevatedButton(
                    key: targetKey,
                    onPressed: () {},
                    child: const Text('Target'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );

      // Show the tooltip
      FeatureTooltip.show(
        context: tester.element(find.byType(Scaffold)),
        targetKey: targetKey,
        message: 'This is a test tooltip',
        position: TooltipPosition.bottom,
        onDismiss: () {
          dismissed = true;
        },
      );

      await tester.pumpAndSettle();

      // Verify tooltip message is displayed
      expect(find.text('This is a test tooltip'), findsOneWidget);
      expect(dismissed, isFalse);
    });

    testWidgets('tapping backdrop calls onDismiss callback', (tester) async {
      final targetKey = GlobalKey();
      bool dismissed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                Center(
                  child: Container(
                    key: targetKey,
                    width: 100,
                    height: 50,
                    color: Colors.blue,
                    child: const Text('Target'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );

      // Show the tooltip
      FeatureTooltip.show(
        context: tester.element(find.byType(Scaffold)),
        targetKey: targetKey,
        message: 'Tap to dismiss',
        position: TooltipPosition.bottom,
        onDismiss: () {
          dismissed = true;
        },
      );

      await tester.pumpAndSettle();

      // Verify tooltip is shown
      expect(find.text('Tap to dismiss'), findsOneWidget);
      expect(dismissed, isFalse);

      // Tap the backdrop (anywhere on screen away from the tooltip)
      await tester.tapAt(const Offset(10, 10));
      await tester.pumpAndSettle();

      // Verify onDismiss was called
      expect(dismissed, isTrue);
    });

    testWidgets('tooltip animates in correctly', (tester) async {
      final targetKey = GlobalKey();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: Container(
                key: targetKey,
                width: 100,
                height: 50,
                color: Colors.blue,
              ),
            ),
          ),
        ),
      );

      // Show the tooltip
      FeatureTooltip.show(
        context: tester.element(find.byType(Scaffold)),
        targetKey: targetKey,
        message: 'Animated tooltip',
        position: TooltipPosition.top,
      );

      // Pump a few frames to trigger animation
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // Tooltip should be visible during animation
      expect(find.text('Animated tooltip'), findsOneWidget);

      await tester.pumpAndSettle();

      // Tooltip should still be visible after animation completes
      expect(find.text('Animated tooltip'), findsOneWidget);
    });

    testWidgets('tooltip supports different positions', (tester) async {
      final targetKey = GlobalKey();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: Container(
                key: targetKey,
                width: 100,
                height: 50,
                color: Colors.blue,
              ),
            ),
          ),
        ),
      );

      for (final position in TooltipPosition.values) {
        // Show the tooltip with different position
        final overlayEntry = FeatureTooltip.show(
          context: tester.element(find.byType(Scaffold)),
          targetKey: targetKey,
          message: 'Position: ${position.name}',
          position: position,
        );

        await tester.pumpAndSettle();

        // Verify tooltip is displayed
        expect(find.text('Position: ${position.name}'), findsOneWidget);

        // Remove the overlay for next iteration
        overlayEntry?.remove();
        await tester.pumpAndSettle();
      }
    });
  });
}
