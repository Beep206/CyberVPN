import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/shared/widgets/global_error_screen.dart';

void main() {
  /// Helper to create [FlutterErrorDetails] for testing.
  FlutterErrorDetails makeErrorDetails([String message = 'test error']) {
    return FlutterErrorDetails(
      exception: Exception(message),
      stack: StackTrace.current,
      library: 'test library',
      context: ErrorDescription('while running test'),
    );
  }

  group('GlobalErrorScreen', () {
    testWidgets('renders error icon, message, Report and Restart buttons',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: GlobalErrorScreen(error: makeErrorDetails()),
        ),
      );

      // Shield icon placeholder
      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);

      // Error message
      expect(find.text('Something went wrong'), findsOneWidget);

      // Description text
      expect(
        find.text(
          'An unexpected error occurred. You can report this '
          'issue or restart the app.',
        ),
        findsOneWidget,
      );

      // Report button
      expect(find.text('Report'), findsOneWidget);

      // Restart button
      expect(find.text('Restart'), findsOneWidget);
    });

    testWidgets('Report button changes to Reported after tap', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: GlobalErrorScreen(error: makeErrorDetails()),
        ),
      );

      // Tap Report button
      await tester.tap(find.text('Report'));
      await tester.pumpAndSettle();

      // Button text should change to 'Reported'
      expect(find.text('Reported'), findsOneWidget);
      expect(find.text('Report'), findsNothing);

      // Check icon changed to check mark
      expect(find.byIcon(Icons.check), findsOneWidget);
    });

    testWidgets('Report button is disabled after reporting', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: GlobalErrorScreen(error: makeErrorDetails()),
        ),
      );

      // Tap Report once
      await tester.tap(find.text('Report'));
      await tester.pumpAndSettle();

      // After reporting, the button should show 'Reported' and tapping it
      // again should have no effect (the text stays 'Reported').
      expect(find.text('Reported'), findsOneWidget);

      // Tap it again -- should not change anything since onPressed is null.
      await tester.tap(find.text('Reported'));
      await tester.pumpAndSettle();
      expect(find.text('Reported'), findsOneWidget);
    });

    testWidgets('Restart button is present and enabled', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: GlobalErrorScreen(error: makeErrorDetails()),
        ),
      );

      final restartButton = tester.widget<OutlinedButton>(
        find.widgetWithText(OutlinedButton, 'Restart'),
      );
      expect(restartButton.onPressed, isNotNull);
    });

    testWidgets('ErrorWidget.builder renders GlobalErrorScreen on error',
        (tester) async {
      // Save originals so we can restore them.
      final originalBuilder = ErrorWidget.builder;
      final originalOnError = FlutterError.onError;

      // Configure ErrorWidget.builder as the app does.
      ErrorWidget.builder = (FlutterErrorDetails details) {
        return GlobalErrorScreen(error: details);
      };

      // Suppress FlutterError.onError so the test framework does not treat
      // the deliberate exception as a test failure.
      final errors = <FlutterErrorDetails>[];
      FlutterError.onError = errors.add;

      // Build a widget that throws during build.
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              throw Exception('deliberate test error');
            },
          ),
        ),
      );

      // Verify the error was caught.
      expect(errors, isNotEmpty);

      // The GlobalErrorScreen should be rendered instead of the red error.
      expect(find.text('Something went wrong'), findsOneWidget);
      expect(find.text('Report'), findsOneWidget);
      expect(find.text('Restart'), findsOneWidget);

      // Restore originals.
      ErrorWidget.builder = originalBuilder;
      FlutterError.onError = originalOnError;
    });
  });
}
