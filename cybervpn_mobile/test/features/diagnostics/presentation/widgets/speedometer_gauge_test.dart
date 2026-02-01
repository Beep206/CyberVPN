import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/speedometer_gauge.dart';

void main() {
  group('SpeedometerGauge', () {
    testWidgets('renders SpeedometerGauge with default parameters',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 50.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify the widget builds without errors
      expect(find.byType(SpeedometerGauge), findsOneWidget);
      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('displays correct speed value at zero speed', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 0.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should show 0.0 speed
      expect(find.text('0.0'), findsOneWidget);
      expect(find.text('Mbps'), findsOneWidget);
    });

    testWidgets('displays correct speed value at mid-range speed',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 50.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should show 50.0 speed
      expect(find.text('50.0'), findsOneWidget);
      expect(find.text('Mbps'), findsOneWidget);
    });

    testWidgets('displays correct speed value at maximum speed',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 100.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should show 100.0 speed
      expect(find.text('100.0'), findsOneWidget);
      expect(find.text('Mbps'), findsOneWidget);
    });

    testWidgets('clamps speed values above maxSpeed', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 150.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should clamp to 100.0
      expect(find.text('100.0'), findsOneWidget);
    });

    testWidgets('uses custom label when provided', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 25.0,
                  label: 'KB/s',
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should show custom label
      expect(find.text('KB/s'), findsOneWidget);
      expect(find.text('Mbps'), findsNothing);
    });

    testWidgets('animates when speed changes', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 20.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Initial speed should be 20.0
      expect(find.text('20.0'), findsOneWidget);

      // Update speed to 80.0
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 80.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      // Should trigger animation
      await tester.pump();

      // After animation completes
      await tester.pumpAndSettle();

      // Speed should now be 80.0
      expect(find.text('80.0'), findsOneWidget);
    });

    testWidgets('animation completes without errors', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 30.0,
                  maxSpeed: 100.0,
                  animationDuration: Duration(milliseconds: 500),
                ),
              ),
            ),
          ),
        ),
      );

      // Pump initial frame
      await tester.pump();

      // Let animation progress
      await tester.pump(const Duration(milliseconds: 250));

      // Complete animation
      await tester.pumpAndSettle();

      // Verify no errors occurred
      expect(tester.takeException(), isNull);
    });

    testWidgets('respects custom maxSpeed parameter', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 200.0,
                  maxSpeed: 200.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should show 200.0 when maxSpeed is 200
      expect(find.text('200.0'), findsOneWidget);
    });

    testWidgets('uses explicit size when provided', (tester) async {
      const testSize = 250.0;

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SpeedometerGauge(
                speed: 50.0,
                size: testSize,
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the SizedBox that wraps the gauge
      final sizedBox = tester.widget<SizedBox>(
        find.descendant(
          of: find.byType(SpeedometerGauge),
          matching: find.byType(SizedBox),
        ).first,
      );

      expect(sizedBox.width, equals(testSize));
      expect(sizedBox.height, equals(testSize));
    });

    testWidgets('handles rapid speed changes without errors', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 10.0,
                  animationDuration: Duration(milliseconds: 100),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Rapidly change speed multiple times
      for (var i = 20; i <= 100; i += 20) {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 300,
                  height: 300,
                  child: SpeedometerGauge(
                    speed: i.toDouble(),
                    animationDuration: const Duration(milliseconds: 100),
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.pump();
      }

      await tester.pumpAndSettle();

      // Verify no errors occurred
      expect(tester.takeException(), isNull);
    });

    testWidgets('displays speed with one decimal place', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 33.7,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Should show speed with one decimal place
      expect(find.text('33.7'), findsOneWidget);
    });

    testWidgets('gauge uses cyberpunk colors', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 75.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the Text widget displaying speed
      final speedText = tester.widget<Text>(
        find.descendant(
          of: find.byType(SpeedometerGauge),
          matching: find.byType(Text),
        ).first,
      );

      // Verify the color matches cyberpunk theme (matrixGreen for high speeds)
      expect(speedText.style?.color, equals(CyberColors.matrixGreen));
    });

    testWidgets('speed color changes based on value - low speed',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 15.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the Text widget displaying speed
      final speedText = tester.widget<Text>(
        find.descendant(
          of: find.byType(SpeedometerGauge),
          matching: find.byType(Text),
        ).first,
      );

      // Low speed (< 30% of max) should be neonPink
      expect(speedText.style?.color, equals(CyberColors.neonPink));
    });

    testWidgets('speed color changes based on value - medium speed',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 50.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the Text widget displaying speed
      final speedText = tester.widget<Text>(
        find.descendant(
          of: find.byType(SpeedometerGauge),
          matching: find.byType(Text),
        ).first,
      );

      // Medium speed (30-60% of max) should be neonCyan
      expect(speedText.style?.color, equals(CyberColors.neonCyan));
    });

    testWidgets('speed color changes based on value - high speed',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 85.0,
                  maxSpeed: 100.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the Text widget displaying speed
      final speedText = tester.widget<Text>(
        find.descendant(
          of: find.byType(SpeedometerGauge),
          matching: find.byType(Text),
        ).first,
      );

      // High speed (> 60% of max) should be matrixGreen
      expect(speedText.style?.color, equals(CyberColors.matrixGreen));
    });

    testWidgets('uses Orbitron font for speed value', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 42.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the speed value text widget
      final speedText = tester.widget<Text>(
        find.text('42.0'),
      );

      // Verify it uses Orbitron font (cyberpunk theme)
      expect(speedText.style?.fontFamily, equals('Orbitron'));
      expect(speedText.style?.fontWeight, equals(FontWeight.w700));
    });

    testWidgets('uses JetBrains Mono font for label', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 42.0,
                  label: 'Mbps',
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Find the label text widget
      final labelText = tester.widget<Text>(
        find.text('Mbps'),
      );

      // Verify it uses JetBrains Mono font
      expect(labelText.style?.fontFamily, equals('JetBrains Mono'));
    });
  });

  group('SpeedometerGaugeState', () {
    testWidgets('animation controller is disposed properly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: 300,
                height: 300,
                child: SpeedometerGauge(
                  speed: 50.0,
                ),
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Remove the widget
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify no errors from improper disposal
      expect(tester.takeException(), isNull);
    });
  });
}
