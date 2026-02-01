import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/widgets/permission_card.dart';

void main() {
  group('PermissionCard', () {
    testWidgets('displays permission information correctly',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PermissionCard(
              icon: Icons.vpn_lock,
              title: 'VPN Connection',
              description: 'Test description',
            ),
          ),
        ),
      );

      // Assert
      expect(find.text('VPN Connection'), findsOneWidget);
      expect(find.text('Test description'), findsOneWidget);
      expect(find.byIcon(Icons.vpn_lock), findsOneWidget);
    });

    testWidgets('shows pending state by default',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PermissionCard(
              icon: Icons.vpn_lock,
              title: 'VPN Connection',
              description: 'Test description',
            ),
          ),
        ),
      );

      // Assert - should show outlined circle for pending
      expect(find.byIcon(Icons.circle_outlined), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsNothing);
    });

    testWidgets('shows granted state when permission is granted',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PermissionCard(
              icon: Icons.vpn_lock,
              title: 'VPN Connection',
              description: 'Test description',
              isGranted: true,
            ),
          ),
        ),
      );

      // Assert - should show check circle for granted
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
      expect(find.byIcon(Icons.circle_outlined), findsNothing);
    });

    testWidgets('shows loading indicator when processing',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PermissionCard(
              icon: Icons.vpn_lock,
              title: 'VPN Connection',
              description: 'Test description',
              isProcessing: true,
            ),
          ),
        ),
      );

      // Assert - should show progress indicator
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsNothing);
      expect(find.byIcon(Icons.circle_outlined), findsNothing);
    });

    testWidgets('applies different styling when granted',
        (WidgetTester tester) async {
      // Arrange
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
          ),
          home: const Scaffold(
            body: PermissionCard(
              icon: Icons.vpn_lock,
              title: 'VPN Connection',
              description: 'Test description',
              isGranted: true,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Assert - should have border when granted
      final container = tester.widget<Container>(
        find.descendant(
          of: find.byType(PermissionCard),
          matching: find.byType(Container).first,
        ),
      );
      final decoration = container.decoration as BoxDecoration;
      expect(decoration.border, isNotNull);
      expect((decoration.border as Border).top.width, equals(2.0));
    });
  });
}
