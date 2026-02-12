import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('DiagnosticStepStatus', () {
    test('has all expected values', () {
      expect(DiagnosticStepStatus.values, hasLength(5));
      expect(DiagnosticStepStatus.values, contains(DiagnosticStepStatus.pending));
      expect(DiagnosticStepStatus.values, contains(DiagnosticStepStatus.running));
      expect(DiagnosticStepStatus.values, contains(DiagnosticStepStatus.success));
      expect(DiagnosticStepStatus.values, contains(DiagnosticStepStatus.failed));
      expect(DiagnosticStepStatus.values, contains(DiagnosticStepStatus.warning));
    });
  });

  group('DiagnosticStep', () {
    test('creates step with required fields only', () {
      const step = DiagnosticStep(
        name: 'Check Connectivity',
        status: DiagnosticStepStatus.pending,
      );

      expect(step.name, 'Check Connectivity');
      expect(step.status, DiagnosticStepStatus.pending);
      expect(step.duration, isNull);
      expect(step.message, isNull);
      expect(step.suggestion, isNull);
    });

    test('creates step with all optional fields', () {
      const step = DiagnosticStep(
        name: 'DNS Resolution',
        status: DiagnosticStepStatus.failed,
        duration: Duration(milliseconds: 500),
        message: 'DNS lookup timed out',
        suggestion: 'Check your DNS settings or try a different DNS provider',
      );

      expect(step.name, 'DNS Resolution');
      expect(step.status, DiagnosticStepStatus.failed);
      expect(step.duration, const Duration(milliseconds: 500));
      expect(step.message, 'DNS lookup timed out');
      expect(step.suggestion, 'Check your DNS settings or try a different DNS provider');
    });

    test('copyWith updates specified fields', () {
      const step = DiagnosticStep(
        name: 'API Reachability',
        status: DiagnosticStepStatus.running,
      );

      final updated = step.copyWith(
        status: DiagnosticStepStatus.success,
        duration: const Duration(milliseconds: 120),
        message: 'API is reachable',
      );

      expect(updated.name, 'API Reachability');
      expect(updated.status, DiagnosticStepStatus.success);
      expect(updated.duration, const Duration(milliseconds: 120));
      expect(updated.message, 'API is reachable');
      expect(updated.suggestion, isNull);
    });

    test('equality for identical steps', () {
      const step1 = DiagnosticStep(
        name: 'Test Step',
        status: DiagnosticStepStatus.success,
        duration: Duration(seconds: 1),
      );
      const step2 = DiagnosticStep(
        name: 'Test Step',
        status: DiagnosticStepStatus.success,
        duration: Duration(seconds: 1),
      );

      expect(step1, equals(step2));
      expect(step1.hashCode, equals(step2.hashCode));
    });

    test('inequality for different steps', () {
      const step1 = DiagnosticStep(
        name: 'Test Step',
        status: DiagnosticStepStatus.success,
      );
      const step2 = DiagnosticStep(
        name: 'Test Step',
        status: DiagnosticStepStatus.failed,
      );

      expect(step1, isNot(equals(step2)));
    });
  });

  group('DiagnosticResult', () {
    late DiagnosticResult result;
    late DateTime ranAt;
    late List<DiagnosticStep> steps;

    setUp(() {
      ranAt = DateTime(2026, 1, 31, 12, 0, 0);
      steps = [
        const DiagnosticStep(
          name: 'Internet Connectivity',
          status: DiagnosticStepStatus.success,
          duration: Duration(milliseconds: 200),
          message: 'Connected via WiFi',
        ),
        const DiagnosticStep(
          name: 'DNS Resolution',
          status: DiagnosticStepStatus.success,
          duration: Duration(milliseconds: 150),
        ),
        const DiagnosticStep(
          name: 'VPN Connection',
          status: DiagnosticStepStatus.warning,
          duration: Duration(seconds: 2),
          message: 'High latency detected',
          suggestion: 'Try connecting to a closer server',
        ),
      ];
      result = DiagnosticResult(
        steps: steps,
        ranAt: ranAt,
        totalDuration: const Duration(seconds: 3),
      );
    });

    test('creates result with all required fields', () {
      expect(result.steps, hasLength(3));
      expect(result.ranAt, ranAt);
      expect(result.totalDuration, const Duration(seconds: 3));
    });

    test('steps are accessible by index', () {
      expect(result.steps[0].name, 'Internet Connectivity');
      expect(result.steps[1].name, 'DNS Resolution');
      expect(result.steps[2].name, 'VPN Connection');
    });

    test('copyWith preserves unchanged fields', () {
      final newRanAt = DateTime(2026, 2, 1, 10, 0, 0);
      final updated = result.copyWith(ranAt: newRanAt);

      expect(updated.ranAt, newRanAt);
      expect(updated.steps, result.steps);
      expect(updated.totalDuration, result.totalDuration);
    });

    test('equality for identical results', () {
      final result2 = DiagnosticResult(
        steps: [
          const DiagnosticStep(
            name: 'Internet Connectivity',
            status: DiagnosticStepStatus.success,
            duration: Duration(milliseconds: 200),
            message: 'Connected via WiFi',
          ),
          const DiagnosticStep(
            name: 'DNS Resolution',
            status: DiagnosticStepStatus.success,
            duration: Duration(milliseconds: 150),
          ),
          const DiagnosticStep(
            name: 'VPN Connection',
            status: DiagnosticStepStatus.warning,
            duration: Duration(seconds: 2),
            message: 'High latency detected',
            suggestion: 'Try connecting to a closer server',
          ),
        ],
        ranAt: ranAt,
        totalDuration: const Duration(seconds: 3),
      );

      expect(result, equals(result2));
      expect(result.hashCode, equals(result2.hashCode));
    });

    test('inequality for different results', () {
      final result2 = DiagnosticResult(
        steps: [],
        ranAt: ranAt,
        totalDuration: const Duration(seconds: 1),
      );

      expect(result, isNot(equals(result2)));
    });

    test('toString returns meaningful representation', () {
      final str = result.toString();
      expect(str, contains('DiagnosticResult'));
    });
  });
}
