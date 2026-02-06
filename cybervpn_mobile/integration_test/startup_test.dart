import 'package:cybervpn_mobile/app/app.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Integration test verifying cold start reaches an interactive screen
/// (splash → auth check → login or connection) within 5 seconds.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Startup Performance', () {
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
      await prefs.clear();
    });

    tearDown(() async {
      await prefs.clear();
    });

    testWidgets('cold start reaches interactive screen within 5 seconds',
        (tester) async {
      final stopwatch = Stopwatch()..start();

      // Build provider overrides (async because SecureStorage prewarm).
      final overrides = await buildProviderOverrides(prefs);

      await tester.pumpWidget(
        ProviderScope(
          overrides: overrides,
          child: const CyberVpnApp(),
        ),
      );

      // Pump the first frame — this should show the splash screen.
      await tester.pump();

      // Give the app up to 5 seconds to settle to an interactive screen.
      // pumpAndSettle waits until no more frames are scheduled.
      await tester.pumpAndSettle(
        const Duration(milliseconds: 100),
        EnginePhase.sendSemanticsUpdate,
        const Duration(seconds: 5),
      );

      stopwatch.stop();

      // After settling, the app should have navigated past splash to either
      // the login screen (unauthenticated) or onboarding or connection.
      // At minimum, we should NOT still be on the splash screen.
      //
      // Verify an interactive widget is present: either a text field (login),
      // a button, or the connection screen scaffold.
      final hasInteractiveWidget =
          find.byType(ElevatedButton).evaluate().isNotEmpty ||
          find.byType(FilledButton).evaluate().isNotEmpty ||
          find.byType(OutlinedButton).evaluate().isNotEmpty ||
          find.byType(TextButton).evaluate().isNotEmpty ||
          find.byType(TextField).evaluate().isNotEmpty ||
          find.byType(IconButton).evaluate().isNotEmpty;

      expect(
        hasInteractiveWidget,
        isTrue,
        reason: 'App should reach an interactive screen with tappable '
            'widgets within 5 seconds of cold start. '
            'Elapsed: ${stopwatch.elapsedMilliseconds}ms',
      );

      // Assert startup completed within the 5 second budget.
      expect(
        stopwatch.elapsedMilliseconds,
        lessThan(5000),
        reason: 'Cold start should complete in under 5 seconds. '
            'Actual: ${stopwatch.elapsedMilliseconds}ms',
      );
    });
  });
}
