import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';

void main() {
  // ===========================================================================
  // DiagnosticStepStatus enum tests
  // ===========================================================================

  group('DiagnosticStepStatus', () {
    test('has all expected values', () {
      expect(DiagnosticStepStatus.values, containsAll([
        DiagnosticStepStatus.pending,
        DiagnosticStepStatus.running,
        DiagnosticStepStatus.success,
        DiagnosticStepStatus.failed,
        DiagnosticStepStatus.warning,
      ]));
    });

    test('has exactly 5 values', () {
      expect(DiagnosticStepStatus.values.length, equals(5));
    });
  });

  // ===========================================================================
  // DiagnosticStep entity tests
  // ===========================================================================

  group('DiagnosticStep', () {
    test('creates a success step', () {
      const step = DiagnosticStep(
        name: 'Network Connectivity',
        status: DiagnosticStepStatus.success,
        duration: Duration(milliseconds: 150),
        message: 'Device is connected to the network',
      );

      expect(step.name, equals('Network Connectivity'));
      expect(step.status, equals(DiagnosticStepStatus.success));
      expect(step.duration?.inMilliseconds, equals(150));
      expect(step.message, equals('Device is connected to the network'));
      expect(step.suggestion, isNull);
    });

    test('creates a failed step with suggestion', () {
      const step = DiagnosticStep(
        name: 'DNS Resolution',
        status: DiagnosticStepStatus.failed,
        duration: Duration(seconds: 5),
        message: 'DNS lookup failed',
        suggestion: 'Check DNS settings or try a different network',
      );

      expect(step.name, equals('DNS Resolution'));
      expect(step.status, equals(DiagnosticStepStatus.failed));
      expect(step.duration?.inSeconds, equals(5));
      expect(step.message, contains('DNS lookup failed'));
      expect(step.suggestion, isNotNull);
      expect(step.suggestion, contains('DNS settings'));
    });

    test('creates a warning step', () {
      const step = DiagnosticStep(
        name: 'VPN Server TCP Handshake',
        status: DiagnosticStepStatus.warning,
        message: 'No server target provided, skipping TCP handshake',
        suggestion: 'Select a VPN server to run full diagnostics',
      );

      expect(step.status, equals(DiagnosticStepStatus.warning));
      expect(step.suggestion, isNotNull);
      // duration is optional
      expect(step.duration, isNull);
    });

    test('creates a pending step', () {
      const step = DiagnosticStep(
        name: 'Full VPN Tunnel',
        status: DiagnosticStepStatus.pending,
      );

      expect(step.status, equals(DiagnosticStepStatus.pending));
      expect(step.message, isNull);
      expect(step.suggestion, isNull);
      expect(step.duration, isNull);
    });

    test('creates a running step', () {
      const step = DiagnosticStep(
        name: 'API Reachability',
        status: DiagnosticStepStatus.running,
      );

      expect(step.status, equals(DiagnosticStepStatus.running));
    });
  });

  // ===========================================================================
  // DiagnosticResult entity tests
  // ===========================================================================

  group('DiagnosticResult', () {
    test('creates a result with all steps passing', () {
      final steps = [
        const DiagnosticStep(
          name: 'Network Connectivity',
          status: DiagnosticStepStatus.success,
          duration: Duration(milliseconds: 100),
          message: 'Connected',
        ),
        const DiagnosticStep(
          name: 'DNS Resolution',
          status: DiagnosticStepStatus.success,
          duration: Duration(milliseconds: 200),
          message: 'Resolved',
        ),
        const DiagnosticStep(
          name: 'API Reachability',
          status: DiagnosticStepStatus.success,
          duration: Duration(milliseconds: 300),
          message: 'API OK',
        ),
      ];

      final result = DiagnosticResult(
        steps: steps,
        ranAt: DateTime(2025, 6, 15, 10, 30),
        totalDuration: const Duration(milliseconds: 600),
      );

      expect(result.steps.length, equals(3));
      expect(
        result.steps.every(
          (s) => s.status == DiagnosticStepStatus.success,
        ),
        isTrue,
      );
      expect(result.ranAt, equals(DateTime(2025, 6, 15, 10, 30)));
      expect(result.totalDuration.inMilliseconds, equals(600));
    });

    test('creates a result with mixed statuses', () {
      final steps = [
        const DiagnosticStep(
          name: 'Network Connectivity',
          status: DiagnosticStepStatus.success,
          message: 'Connected',
        ),
        const DiagnosticStep(
          name: 'DNS Resolution',
          status: DiagnosticStepStatus.failed,
          message: 'Failed',
          suggestion: 'Check DNS',
        ),
        const DiagnosticStep(
          name: 'API Reachability',
          status: DiagnosticStepStatus.warning,
          message: 'Skipped',
        ),
      ];

      final result = DiagnosticResult(
        steps: steps,
        ranAt: DateTime.now(),
        totalDuration: const Duration(seconds: 5),
      );

      final failedSteps = result.steps
          .where((s) => s.status == DiagnosticStepStatus.failed)
          .toList();
      expect(failedSteps.length, equals(1));
      expect(failedSteps.first.name, equals('DNS Resolution'));

      final warningSteps = result.steps
          .where((s) => s.status == DiagnosticStepStatus.warning)
          .toList();
      expect(warningSteps.length, equals(1));
    });

    test('creates a result with all 6 steps', () {
      final steps = List.generate(
        6,
        (i) => DiagnosticStep(
          name: 'Step $i',
          status: DiagnosticStepStatus.success,
          duration: Duration(milliseconds: 100 * (i + 1)),
        ),
      );

      final result = DiagnosticResult(
        steps: steps,
        ranAt: DateTime(2025, 1, 1),
        totalDuration: const Duration(seconds: 2),
      );

      expect(result.steps.length, equals(6));
    });

    test('handles empty steps list', () {
      final result = DiagnosticResult(
        steps: const [],
        ranAt: DateTime(2025, 1, 1),
        totalDuration: Duration.zero,
      );

      expect(result.steps, isEmpty);
      expect(result.totalDuration, equals(Duration.zero));
    });
  });
}
