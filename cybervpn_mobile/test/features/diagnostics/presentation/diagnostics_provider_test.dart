import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:cybervpn_mobile/features/diagnostics/data/services/diagnostic_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/data/services/speed_test_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/providers/diagnostics_provider.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockSpeedTestService extends Mock implements SpeedTestService {}

class MockDiagnosticService extends Mock implements DiagnosticService {}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

SpeedTestResult _createSpeedTestResult({
  double download = 50.0,
  double upload = 25.0,
  int latency = 15,
  int jitter = 3,
  DateTime? testedAt,
}) {
  return SpeedTestResult(
    downloadMbps: download,
    uploadMbps: upload,
    latencyMs: latency,
    jitterMs: jitter,
    testedAt: testedAt ?? DateTime(2025, 1, 1, 12, 0),
    vpnActive: false,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockSpeedTestService mockSpeedTestService;
  late MockDiagnosticService mockDiagnosticService;
  late ProviderContainer container;

  setUp(() {
    mockSpeedTestService = MockSpeedTestService();
    mockDiagnosticService = MockDiagnosticService();

    // Default stub for getHistory (returns empty on init).
    when(() => mockSpeedTestService.getHistory())
        .thenAnswer((_) async => []);

    container = ProviderContainer(
      overrides: [
        speedTestServiceProvider.overrideWithValue(mockSpeedTestService),
        diagnosticServiceProvider.overrideWithValue(mockDiagnosticService),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  /// Waits for the AsyncNotifier to settle into an AsyncData state.
  Future<DiagnosticsState> waitForState() async {
    // Read the provider to trigger build.
    final sub = container.listen(diagnosticsProvider, (_, _) {});
    // Allow microtasks to complete.
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);
    final value = container.read(diagnosticsProvider);
    sub.close();
    return value.requireValue;
  }

  // =========================================================================
  // Initialization
  // =========================================================================

  group('DiagnosticsNotifier initialization', () {
    test('initial state has empty lists and null results', () async {
      final state = await waitForState();

      expect(state.speedTestResult, isNull);
      expect(state.isRunningSpeedTest, isFalse);
      expect(state.diagnosticResult, isNull);
      expect(state.isRunningDiagnostics, isFalse);
      expect(state.speedHistory, isEmpty);
      expect(state.logEntries, isEmpty);
    });

    test('loads persisted speed history on init', () async {
      final history = [
        _createSpeedTestResult(download: 100.0, testedAt: DateTime(2025, 1, 2)),
        _createSpeedTestResult(download: 80.0, testedAt: DateTime(2025, 1, 1)),
      ];

      when(() => mockSpeedTestService.getHistory())
          .thenAnswer((_) async => history);

      final state = await waitForState();

      expect(state.speedHistory, hasLength(2));
      expect(state.speedHistory.first.downloadMbps, 100.0);
    });
  });

  // =========================================================================
  // runSpeedTest
  // =========================================================================

  group('runSpeedTest', () {
    test('updates state with result on success', () async {
      final result = _createSpeedTestResult(download: 95.0, upload: 40.0);

      when(() => mockSpeedTestService.runSpeedTest(
            vpnActive: any(named: 'vpnActive'),
            serverName: any(named: 'serverName'),
            progressController: any(named: 'progressController'),
          )).thenAnswer((_) async => result);

      when(() => mockSpeedTestService.getHistory())
          .thenAnswer((_) async => [result]);

      // Wait for init.
      await waitForState();

      // Run the speed test.
      await container
          .read(diagnosticsProvider.notifier)
          .runSpeedTest();

      final state = container.read(diagnosticsProvider).requireValue;

      expect(state.isRunningSpeedTest, isFalse);
      expect(state.speedTestResult, isNotNull);
      expect(state.speedTestResult!.downloadMbps, 95.0);
      expect(state.speedTestResult!.uploadMbps, 40.0);
      expect(state.speedHistory, hasLength(1));
      expect(state.logEntries, isNotEmpty);
    });

    test('sets isRunningSpeedTest to false on error', () async {
      when(() => mockSpeedTestService.runSpeedTest(
            vpnActive: any(named: 'vpnActive'),
            serverName: any(named: 'serverName'),
            progressController: any(named: 'progressController'),
          )).thenThrow(Exception('Network error'));

      await waitForState();

      await container
          .read(diagnosticsProvider.notifier)
          .runSpeedTest();

      final state = container.read(diagnosticsProvider).requireValue;

      expect(state.isRunningSpeedTest, isFalse);
      expect(state.speedTestResult, isNull);

      // Should have error log entry.
      final errorLogs =
          state.logEntries.where((e) => e.level == 'error').toList();
      expect(errorLogs, isNotEmpty);
    });

    test('does not run if already running', () async {
      final result = _createSpeedTestResult();
      var callCount = 0;

      when(() => mockSpeedTestService.runSpeedTest(
            vpnActive: any(named: 'vpnActive'),
            serverName: any(named: 'serverName'),
            progressController: any(named: 'progressController'),
          )).thenAnswer((_) async {
        callCount++;
        // Simulate a slow speed test.
        await Future<void>.delayed(const Duration(milliseconds: 50));
        return result;
      });

      when(() => mockSpeedTestService.getHistory())
          .thenAnswer((_) async => [result]);

      await waitForState();

      // Start first speed test (will take 50ms).
      final firstRun = container
          .read(diagnosticsProvider.notifier)
          .runSpeedTest();

      // Give it a moment to set isRunningSpeedTest = true.
      await Future<void>.delayed(Duration.zero);

      // Attempt second speed test while first is running.
      // This should be a no-op since isRunningSpeedTest is true.
      await container
          .read(diagnosticsProvider.notifier)
          .runSpeedTest();

      // Wait for first run to complete.
      await firstRun;

      // Only one actual service call should have been made.
      expect(callCount, 1);
    });
  });

  // =========================================================================
  // runDiagnostics
  // =========================================================================

  group('runDiagnostics', () {
    test('updates step statuses in sequence', () async {
      final steps = [
        const DiagnosticStep(
          name: DiagnosticStepNames.networkConnectivity,
          status: DiagnosticStepStatus.success,
          message: 'Connected',
        ),
        const DiagnosticStep(
          name: DiagnosticStepNames.dnsResolution,
          status: DiagnosticStepStatus.success,
          message: 'Resolved',
        ),
        const DiagnosticStep(
          name: DiagnosticStepNames.apiReachability,
          status: DiagnosticStepStatus.failed,
          message: 'API unreachable',
          suggestion: 'Check server',
        ),
      ];

      when(() => mockDiagnosticService.runDiagnostics(
            serverTarget: any(named: 'serverTarget'),
          )).thenAnswer((_) => Stream.fromIterable(steps));

      await waitForState();

      await container
          .read(diagnosticsProvider.notifier)
          .runDiagnostics();

      final state = container.read(diagnosticsProvider).requireValue;

      expect(state.isRunningDiagnostics, isFalse);
      expect(state.diagnosticResult, isNotNull);
      expect(state.diagnosticResult!.steps, hasLength(3));
      expect(
        state.diagnosticResult!.steps[0].status,
        DiagnosticStepStatus.success,
      );
      expect(
        state.diagnosticResult!.steps[2].status,
        DiagnosticStepStatus.failed,
      );
      // Should have log entries for start + each step + completion.
      expect(state.logEntries.length, greaterThanOrEqualTo(5));
    });

    test('sets isRunningDiagnostics to false on error', () async {
      when(() => mockDiagnosticService.runDiagnostics(
            serverTarget: any(named: 'serverTarget'),
          )).thenAnswer(
        (_) => Stream.error(Exception('Diagnostics failed')),
      );

      await waitForState();

      await container
          .read(diagnosticsProvider.notifier)
          .runDiagnostics();

      final state = container.read(diagnosticsProvider).requireValue;

      expect(state.isRunningDiagnostics, isFalse);
    });
  });

  // =========================================================================
  // getHistory / exportLogs
  // =========================================================================

  group('getHistory', () {
    test('returns history sorted by timestamp descending', () async {
      final older = _createSpeedTestResult(
        download: 50.0,
        testedAt: DateTime(2025, 1, 1),
      );
      final newer = _createSpeedTestResult(
        download: 100.0,
        testedAt: DateTime(2025, 6, 1),
      );

      // Return in non-sorted order.
      when(() => mockSpeedTestService.getHistory())
          .thenAnswer((_) async => [older, newer]);

      await waitForState();

      final history =
          container.read(diagnosticsProvider.notifier).getHistory();

      expect(history.first.testedAt.isAfter(history.last.testedAt), isTrue);
      expect(history.first.downloadMbps, 100.0);
    });
  });

  group('exportLogs', () {
    test('returns valid JSON string', () async {
      // Trigger a speed test to generate log entries.
      final result = _createSpeedTestResult();
      when(() => mockSpeedTestService.runSpeedTest(
            vpnActive: any(named: 'vpnActive'),
            serverName: any(named: 'serverName'),
            progressController: any(named: 'progressController'),
          )).thenAnswer((_) async => result);
      when(() => mockSpeedTestService.getHistory())
          .thenAnswer((_) async => [result]);

      await waitForState();

      await container
          .read(diagnosticsProvider.notifier)
          .runSpeedTest();

      final exported =
          container.read(diagnosticsProvider.notifier).exportLogs();

      // Should be valid JSON.
      final decoded = jsonDecode(exported) as List;
      expect(decoded, isNotEmpty);
      expect(decoded.first, containsPair('level', 'info'));
    });
  });

  // =========================================================================
  // Derived providers
  // =========================================================================

  group('derived providers', () {
    test('speedTestProgressProvider reflects isRunningSpeedTest', () async {
      await waitForState();

      final isRunning = container.read(speedTestProgressProvider);
      expect(isRunning, isFalse);
    });

    test('diagnosticStepsProvider returns empty when no diagnostics run',
        () async {
      await waitForState();

      final steps = container.read(diagnosticStepsProvider);
      expect(steps, isEmpty);
    });

    test('diagnosticStepsProvider returns steps after diagnostics run',
        () async {
      final diagnosticSteps = [
        const DiagnosticStep(
          name: DiagnosticStepNames.networkConnectivity,
          status: DiagnosticStepStatus.success,
        ),
      ];

      when(() => mockDiagnosticService.runDiagnostics(
            serverTarget: any(named: 'serverTarget'),
          )).thenAnswer((_) => Stream.fromIterable(diagnosticSteps));

      await waitForState();

      await container
          .read(diagnosticsProvider.notifier)
          .runDiagnostics();

      final steps = container.read(diagnosticStepsProvider);
      expect(steps, hasLength(1));
      expect(steps.first.status, DiagnosticStepStatus.success);
    });
  });
}
