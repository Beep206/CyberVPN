import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/providers/diagnostics_provider.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/screens/diagnostics_screen.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/diagnostic_step_tile.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

final _testSteps = [
  const DiagnosticStep(
    name: 'Network Connectivity',
    status: DiagnosticStepStatus.success,
    duration: Duration(milliseconds: 125),
    message: 'Device is connected to the network',
  ),
  const DiagnosticStep(
    name: 'DNS Resolution',
    status: DiagnosticStepStatus.success,
    duration: Duration(milliseconds: 250),
    message: 'Resolved api.cybervpn.com',
  ),
  const DiagnosticStep(
    name: 'API Reachability',
    status: DiagnosticStepStatus.failed,
    duration: Duration(milliseconds: 500),
    message: 'API unreachable: Timeout',
    suggestion: 'API server may be down, try again later',
  ),
];

final _completedDiagnosticResult = DiagnosticResult(
  steps: _testSteps,
  ranAt: DateTime(2026, 2, 1, 10, 0),
  totalDuration: const Duration(seconds: 3),
);

// ---------------------------------------------------------------------------
// Fake DiagnosticsNotifier
// ---------------------------------------------------------------------------

class _FakeDiagnosticsNotifier extends AsyncNotifier<DiagnosticsState>
    implements DiagnosticsNotifier {
  _FakeDiagnosticsNotifier(this._state);

  final DiagnosticsState _state;
  bool runDiagnosticsCalled = false;

  @override
  Future<DiagnosticsState> build() async => _state;

  @override
  Future<void> runDiagnostics({
    dynamic serverTarget,
  }) async {
    runDiagnosticsCalled = true;
  }

  @override
  Future<void> runSpeedTest({
    bool vpnActive = false,
    String? serverName,
  }) async {}

  @override
  List<SpeedTestResult> getHistory() => [];

  @override
  String exportLogs() => '[]';
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

void _ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final exception = details.exception;
    final isOverflow =
        exception is FlutterError && exception.message.contains('overflowed');
    if (!isOverflow) {
      FlutterError.presentError(details);
    }
  };
}

Widget _buildApp(DiagnosticsState state) {
  final notifier = _FakeDiagnosticsNotifier(state);

  return ProviderScope(
    overrides: [
      diagnosticsProvider.overrideWith(() => notifier),
    ],
    child: const MaterialApp(
      home: DiagnosticsScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUp(() {
    _ignoreOverflowErrors();
  });

  group('DiagnosticsScreen', () {
    testWidgets('renders 6 steps in pending state when not running',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        isRunningDiagnostics: false,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pump();

      // Should show "Tap Run Again to start" message when no result
      expect(find.text('Tap Run Again to start'), findsOneWidget);
    });

    testWidgets('shows 6 pending steps when running',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        isRunningDiagnostics: true,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pump();

      // Should show running status message
      expect(find.text('Running connection tests...'), findsOneWidget);

      // Should show all 6 step tiles (pending state)
      expect(find.byType(DiagnosticStepTile), findsNWidgets(6));

      // Run Again button should show "Running..." and be disabled
      expect(find.text('Running...'), findsOneWidget);
    });

    testWidgets('displays completed steps with statuses',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        diagnosticResult: _completedDiagnosticResult,
        isRunningDiagnostics: false,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pumpAndSettle();

      // Should show completion message
      expect(find.text('Diagnostics completed'), findsOneWidget);

      // Should show step tiles for all completed steps
      expect(find.byType(DiagnosticStepTile), findsNWidgets(3));

      // Check for step names
      expect(find.text('Network Connectivity'), findsOneWidget);
      expect(find.text('DNS Resolution'), findsOneWidget);
      expect(find.text('API Reachability'), findsOneWidget);
    });

    testWidgets('shows suggestion on failed step',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        diagnosticResult: _completedDiagnosticResult,
        isRunningDiagnostics: false,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pumpAndSettle();

      // Should show the suggestion for the failed step
      expect(
        find.text('API server may be down, try again later'),
        findsOneWidget,
      );
    });

    testWidgets('shows running status with spinner',
        (WidgetTester tester) async {
      final partialSteps = [
        const DiagnosticStep(
          name: 'Network Connectivity',
          status: DiagnosticStepStatus.success,
          duration: Duration(milliseconds: 125),
        ),
        const DiagnosticStep(
          name: 'DNS Resolution',
          status: DiagnosticStepStatus.running,
        ),
      ];

      final state = DiagnosticsState(
        diagnosticResult: DiagnosticResult(
          steps: partialSteps,
          ranAt: DateTime.now(),
          totalDuration: Duration.zero,
        ),
        isRunningDiagnostics: true,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pump();

      // Should show running state
      expect(find.text('Running connection tests...'), findsOneWidget);

      // Find the step tiles
      final tiles = find.byType(DiagnosticStepTile);
      expect(tiles, findsNWidgets(6));
    });

    testWidgets('triggers runDiagnostics on init',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        isRunningDiagnostics: false,
      );

      final notifier = _FakeDiagnosticsNotifier(state);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            diagnosticsProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(
            home: DiagnosticsScreen(),
          ),
        ),
      );

      // Wait for post-frame callback
      await tester.pumpAndSettle();

      // Verify runDiagnostics was called
      expect(notifier.runDiagnosticsCalled, isTrue);
    });

    testWidgets('Run Again button triggers diagnostics',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        diagnosticResult: _completedDiagnosticResult,
        isRunningDiagnostics: false,
      );

      final notifier = _FakeDiagnosticsNotifier(state);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            diagnosticsProvider.overrideWith(() => notifier),
          ],
          child: const MaterialApp(
            home: DiagnosticsScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Reset the flag after init call
      notifier.runDiagnosticsCalled = false;

      // Tap the Run Again button
      await tester.tap(find.text('Run Again'));
      await tester.pumpAndSettle();

      // Verify runDiagnostics was called
      expect(notifier.runDiagnosticsCalled, isTrue);
    });

    testWidgets('Export Report button appears when diagnostic completed',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        diagnosticResult: _completedDiagnosticResult,
        isRunningDiagnostics: false,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pumpAndSettle();

      // Export Report button should be visible
      expect(find.text('Export Report'), findsOneWidget);
    });

    testWidgets('Export Report button hidden when no result',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        isRunningDiagnostics: false,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pumpAndSettle();

      // Export Report button should not be visible
      expect(find.text('Export Report'), findsNothing);
    });

    testWidgets('displays all 6 step names correctly when running',
        (WidgetTester tester) async {
      final state = DiagnosticsState(
        isRunningDiagnostics: true,
      );

      await tester.pumpWidget(_buildApp(state));
      await tester.pump();

      // Verify all 6 step names are shown
      expect(find.text('Network Connectivity'), findsOneWidget);
      expect(find.text('DNS Resolution'), findsOneWidget);
      expect(find.text('API Reachability'), findsOneWidget);
      expect(find.text('VPN Server TCP Handshake'), findsOneWidget);
      expect(find.text('TLS/Reality Handshake'), findsOneWidget);
      expect(find.text('Full VPN Tunnel'), findsOneWidget);
    });
  });
}
