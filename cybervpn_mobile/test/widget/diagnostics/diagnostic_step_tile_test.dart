import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/diagnostic_step_tile.dart';

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

Widget _buildTile({
  required String stepName,
  required DiagnosticStepStatus status,
  Duration? duration,
  String? message,
  String? suggestion,
}) {
  return MaterialApp(
    home: Scaffold(
      body: DiagnosticStepTile(
        stepName: stepName,
        status: status,
        duration: duration,
        message: message,
        suggestion: suggestion,
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('DiagnosticStepTile', () {
    testWidgets('renders pending state correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Network Connectivity',
          status: DiagnosticStepStatus.pending,
        ),
      );

      // Should show step name
      expect(find.text('Network Connectivity'), findsOneWidget);

      // Should show pending icon (radio_button_unchecked)
      expect(find.byIcon(Icons.radio_button_unchecked), findsOneWidget);

      // Should not show duration, message, or suggestion
      expect(find.text('125ms'), findsNothing);
    });

    testWidgets('renders running state with spinner',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'DNS Resolution',
          status: DiagnosticStepStatus.running,
        ),
      );

      // Should show step name
      expect(find.text('DNS Resolution'), findsOneWidget);

      // Should show spinner
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('renders success state with check icon',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Network Connectivity',
          status: DiagnosticStepStatus.success,
          duration: const Duration(milliseconds: 125),
          message: 'Device is connected to the network',
        ),
      );

      await tester.pumpAndSettle();

      // Should show step name
      expect(find.text('Network Connectivity'), findsOneWidget);

      // Should show success icon (check_circle)
      expect(find.byIcon(Icons.check_circle), findsOneWidget);

      // Should show duration
      expect(find.text('125ms'), findsOneWidget);

      // Should show message
      expect(find.text('Device is connected to the network'), findsOneWidget);
    });

    testWidgets('renders failed state with X icon and suggestion',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'API Reachability',
          status: DiagnosticStepStatus.failed,
          duration: const Duration(milliseconds: 500),
          message: 'API unreachable: Timeout',
          suggestion: 'API server may be down, try again later',
        ),
      );

      await tester.pumpAndSettle();

      // Should show step name
      expect(find.text('API Reachability'), findsOneWidget);

      // Should show failed icon (cancel)
      expect(find.byIcon(Icons.cancel), findsOneWidget);

      // Should show duration
      expect(find.text('500ms'), findsOneWidget);

      // Should show message
      expect(find.text('API unreachable: Timeout'), findsOneWidget);

      // Should show suggestion with lightbulb icon
      expect(
        find.text('API server may be down, try again later'),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.lightbulb_outline), findsOneWidget);
    });

    testWidgets('renders warning state with warning icon',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'VPN Server TCP Handshake',
          status: DiagnosticStepStatus.warning,
          message: 'No server target provided, skipping TCP handshake',
          suggestion: 'Select a VPN server to run full diagnostics',
        ),
      );

      await tester.pumpAndSettle();

      // Should show step name
      expect(find.text('VPN Server TCP Handshake'), findsOneWidget);

      // Should show warning icon
      expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);

      // Should show message
      expect(
        find.text('No server target provided, skipping TCP handshake'),
        findsOneWidget,
      );

      // Warning status does NOT show suggestion box (only failed status does)
      expect(
        find.text('Select a VPN server to run full diagnostics'),
        findsNothing,
      );
    });

    testWidgets('does not show suggestion for non-failed statuses',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Test Step',
          status: DiagnosticStepStatus.success,
          message: 'Success message',
          suggestion: 'This should not appear',
        ),
      );

      await tester.pumpAndSettle();

      // Suggestion should not be shown for success status
      expect(find.text('This should not appear'), findsNothing);
      expect(find.byIcon(Icons.lightbulb_outline), findsNothing);
    });

    testWidgets('animates status transitions',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Test Step',
          status: DiagnosticStepStatus.pending,
        ),
      );

      // Initial state: pending
      expect(find.byIcon(Icons.radio_button_unchecked), findsOneWidget);

      // Update to running
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Test Step',
          status: DiagnosticStepStatus.running,
        ),
      );

      // Should now show spinner
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Update to success
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Test Step',
          status: DiagnosticStepStatus.success,
          duration: const Duration(milliseconds: 200),
        ),
      );

      // Trigger the animation
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 150));

      // Should now show success icon
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });

    testWidgets('duration is formatted correctly',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Test Step',
          status: DiagnosticStepStatus.success,
          duration: const Duration(milliseconds: 1234),
        ),
      );

      await tester.pumpAndSettle();

      // Should show duration in milliseconds
      expect(find.text('1234ms'), findsOneWidget);
    });

    testWidgets('renders without duration when not provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Test Step',
          status: DiagnosticStepStatus.running,
        ),
      );

      await tester.pump();

      // Should not show any duration text
      expect(find.textContaining('ms'), findsNothing);
    });

    testWidgets('renders without message when not provided',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        _buildTile(
          stepName: 'Test Step',
          status: DiagnosticStepStatus.success,
          duration: const Duration(milliseconds: 100),
        ),
      );

      await tester.pumpAndSettle();

      // Should only show step name and duration, no message
      expect(find.text('Test Step'), findsOneWidget);
      expect(find.text('100ms'), findsOneWidget);
    });
  });
}
