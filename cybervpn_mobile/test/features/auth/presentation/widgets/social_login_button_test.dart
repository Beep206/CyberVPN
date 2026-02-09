import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/auth/presentation/widgets/social_login_button.dart';

void main() {
  /// Wraps [child] in a [MaterialApp] so that inherited widgets
  /// (Theme, MediaQuery, etc.) are available during the test.
  Widget buildSubject({
    IconData icon = Icons.star,
    String label = 'Test Button',
    VoidCallback? onPressed,
    bool isLoading = false,
    Color? backgroundColor,
    Color? foregroundColor,
  }) {
    return MaterialApp(
      home: Scaffold(
        body: SocialLoginButton(
          icon: icon,
          label: label,
          onPressed: onPressed,
          isLoading: isLoading,
          backgroundColor: backgroundColor,
          foregroundColor: foregroundColor,
        ),
      ),
    );
  }

  group('SocialLoginButton', () {
    testWidgets('renders icon and label text', (tester) async {
      await tester.pumpWidget(buildSubject(
        icon: Icons.star,
        label: 'Continue with Star',
        onPressed: () {},
      ));

      expect(find.byIcon(Icons.star), findsOneWidget);
      expect(find.text('Continue with Star'), findsOneWidget);
    });

    testWidgets('calls onPressed when tapped', (tester) async {
      var tapped = false;
      await tester.pumpWidget(buildSubject(
        onPressed: () => tapped = true,
      ));

      await tester.tap(find.byType(OutlinedButton));
      await tester.pump();

      expect(tapped, isTrue);
    });

    testWidgets('shows CircularProgressIndicator when isLoading is true',
        (tester) async {
      await tester.pumpWidget(buildSubject(
        onPressed: () {},
        isLoading: true,
      ));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      // When loading, the label text should NOT be visible
      expect(find.text('Test Button'), findsNothing);
    });

    testWidgets('disables button when onPressed is null', (tester) async {
      await tester.pumpWidget(buildSubject(
        onPressed: null,
      ));

      final button =
          tester.widget<OutlinedButton>(find.byType(OutlinedButton));
      expect(button.onPressed, isNull);
    });

    testWidgets('disables button when isLoading is true', (tester) async {
      await tester.pumpWidget(buildSubject(
        onPressed: () {},
        isLoading: true,
      ));

      final button =
          tester.widget<OutlinedButton>(find.byType(OutlinedButton));
      // When isLoading is true, onPressed is set to null in the widget
      expect(button.onPressed, isNull);
    });

    testWidgets('Telegram factory renders correct icon and label',
        (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: SocialLoginButton.telegram(
            onPressed: () {},
          ),
        ),
      ));

      expect(find.byIcon(Icons.telegram), findsOneWidget);
      expect(find.text('Continue with Telegram'), findsOneWidget);
    });

    testWidgets('custom backgroundColor is applied', (tester) async {
      const customColor = Color(0xFFFF5722);
      await tester.pumpWidget(buildSubject(
        onPressed: () {},
        backgroundColor: customColor,
      ));

      final button =
          tester.widget<OutlinedButton>(find.byType(OutlinedButton));
      // Verify the button style has the custom background color.
      // OutlinedButton.styleFrom sets backgroundColor on the ButtonStyle.
      final resolvedBg = button.style?.backgroundColor
          ?.resolve(<WidgetState>{});
      expect(resolvedBg, equals(customColor));
    });
  });
}
