import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/diagnostics/data/services/speed_test_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/data/services/diagnostic_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';

// ---------------------------------------------------------------------------
// Since _bytesToMbps and _calculateJitter are private static methods on
// SpeedTestService, we test them indirectly by verifying the publicly
// observable behaviour of the SpeedTestProgress model and by duplicating
// the well-defined formula in standalone tests.
//
// Formula for _bytesToMbps: (bytes * 8) / (elapsedMs * 1000)
// Formula for _calculateJitter: sqrt( sum((x - mean)^2) / n )
// ---------------------------------------------------------------------------

import 'dart:math';

/// Duplicates the _bytesToMbps formula so we can verify edge cases directly.
double bytesToMbps(int bytes, int elapsedMs) {
  if (elapsedMs <= 0) return 0;
  return (bytes * 8) / (elapsedMs * 1000);
}

/// Duplicates the _calculateJitter formula.
int calculateJitter(List<int> values) {
  if (values.length < 2) return 0;
  final mean = values.reduce((a, b) => a + b) / values.length;
  final sumSquaredDiff = values.fold<double>(
    0,
    (sum, v) => sum + (v - mean) * (v - mean),
  );
  return sqrt(sumSquaredDiff / values.length).round();
}

void main() {
  // ===========================================================================
  // Speed calculation tests (bytesToMbps)
  // ===========================================================================

  group('bytesToMbps calculation', () {
    test('returns 0 when elapsed time is 0', () {
      expect(bytesToMbps(1000000, 0), equals(0.0));
    });

    test('returns 0 when elapsed time is negative', () {
      expect(bytesToMbps(1000000, -5), equals(0.0));
    });

    test('returns 0 when bytes is 0', () {
      expect(bytesToMbps(0, 1000), equals(0.0));
    });

    test('calculates correctly for known values', () {
      // 1_000_000 bytes in 1000 ms = 1 s
      // bits = 8_000_000, megabits = 8.0, over 1 second = 8 Mbps
      final result = bytesToMbps(1000000, 1000);
      expect(result, closeTo(8.0, 0.001));
    });

    test('calculates correctly for 100 MB in 10 seconds', () {
      // 100 MB = 104_857_600 bytes, 10 s = 10_000 ms
      // bits = 838_860_800, megabits = 838.8608, over 10 s = 83.88608 Mbps
      final result = bytesToMbps(104857600, 10000);
      expect(result, closeTo(83.886, 0.01));
    });

    test('handles very large byte counts (1 TB in 60 seconds)', () {
      // 1 TB = 1_099_511_627_776 bytes, 60 s = 60_000 ms
      final result = bytesToMbps(1099511627776, 60000);
      // bits = 8_796_093_022_208, megabits = 8_796_093.022208
      // over 60 s = 146_601.5503... Mbps
      expect(result, greaterThan(100000));
    });

    test('handles very small transfer (1 byte in 1 ms)', () {
      // 1 byte = 8 bits, 1 ms: 8 / 1000 = 0.008 Mbps
      final result = bytesToMbps(1, 1);
      expect(result, closeTo(0.008, 0.001));
    });
  });

  // ===========================================================================
  // Jitter calculation tests
  // ===========================================================================

  group('jitter calculation', () {
    test('returns 0 for single value list', () {
      expect(calculateJitter([100]), equals(0));
    });

    test('returns 0 for empty list', () {
      expect(calculateJitter([]), equals(0));
    });

    test('returns 0 when all values are identical', () {
      expect(calculateJitter([50, 50, 50, 50]), equals(0));
    });

    test('calculates correct jitter for known values', () {
      // Values: [10, 20, 30]
      // Mean: 20, diffs: [-10, 0, 10], squared: [100, 0, 100]
      // Sum: 200, div n=3: 66.67, sqrt: ~8.16, rounds to 8
      expect(calculateJitter([10, 20, 30]), equals(8));
    });

    test('calculates correct jitter for two values', () {
      // Values: [0, 100]
      // Mean: 50, diffs: [-50, 50], squared: [2500, 2500]
      // Sum: 5000, div n=2: 2500, sqrt: 50
      expect(calculateJitter([0, 100]), equals(50));
    });

    test('handles large ping values', () {
      // All same large values should give 0 jitter
      expect(calculateJitter([999, 999, 999]), equals(0));
    });
  });

  // ===========================================================================
  // SpeedTestProgress model tests
  // ===========================================================================

  group('SpeedTestProgress', () {
    test('can be created with all fields', () {
      const progress = SpeedTestProgress(
        phase: SpeedTestPhase.download,
        progressFraction: 0.5,
        currentSpeedMbps: 42.0,
        currentLatencyMs: null,
        pingCount: null,
      );

      expect(progress.phase, equals(SpeedTestPhase.download));
      expect(progress.progressFraction, equals(0.5));
      expect(progress.currentSpeedMbps, equals(42.0));
      expect(progress.currentLatencyMs, isNull);
      expect(progress.pingCount, isNull);
    });

    test('latency phase includes latency and ping count', () {
      const progress = SpeedTestProgress(
        phase: SpeedTestPhase.latency,
        progressFraction: 0.7,
        currentSpeedMbps: 0,
        currentLatencyMs: 25,
        pingCount: 7,
      );

      expect(progress.phase, equals(SpeedTestPhase.latency));
      expect(progress.currentSpeedMbps, equals(0));
      expect(progress.currentLatencyMs, equals(25));
      expect(progress.pingCount, equals(7));
    });
  });

  // ===========================================================================
  // SpeedTestPhase enum tests
  // ===========================================================================

  group('SpeedTestPhase', () {
    test('has all expected values', () {
      expect(SpeedTestPhase.values, containsAll([
        SpeedTestPhase.download,
        SpeedTestPhase.upload,
        SpeedTestPhase.latency,
        SpeedTestPhase.idle,
      ]));
    });

    test('has exactly 4 values', () {
      expect(SpeedTestPhase.values.length, equals(4));
    });
  });

  // ===========================================================================
  // SpeedTestResult entity tests
  // ===========================================================================

  group('SpeedTestResult', () {
    test('can be created with all required fields', () {
      final now = DateTime.now();
      final result = SpeedTestResult(
        downloadMbps: 100.5,
        uploadMbps: 50.2,
        latencyMs: 15,
        jitterMs: 3,
        testedAt: now,
        vpnActive: true,
        serverName: 'US-East-1',
      );

      expect(result.downloadMbps, equals(100.5));
      expect(result.uploadMbps, equals(50.2));
      expect(result.latencyMs, equals(15));
      expect(result.jitterMs, equals(3));
      expect(result.testedAt, equals(now));
      expect(result.vpnActive, isTrue);
      expect(result.serverName, equals('US-East-1'));
    });

    test('serverName is optional', () {
      final result = SpeedTestResult(
        downloadMbps: 0,
        uploadMbps: 0,
        latencyMs: 0,
        jitterMs: 0,
        testedAt: DateTime(2025, 1, 1),
        vpnActive: false,
      );

      expect(result.serverName, isNull);
    });

    test('handles zero speed values', () {
      final result = SpeedTestResult(
        downloadMbps: 0.0,
        uploadMbps: 0.0,
        latencyMs: 0,
        jitterMs: 0,
        testedAt: DateTime(2025, 6, 15),
        vpnActive: false,
      );

      expect(result.downloadMbps, equals(0.0));
      expect(result.uploadMbps, equals(0.0));
    });
  });

  // ===========================================================================
  // DiagnosticStepNames tests
  // ===========================================================================

  group('DiagnosticStepNames', () {
    test('networkConnectivity is correct', () {
      expect(DiagnosticStepNames.networkConnectivity, 'Network Connectivity');
    });

    test('dnsResolution is correct', () {
      expect(DiagnosticStepNames.dnsResolution, 'DNS Resolution');
    });

    test('apiReachability is correct', () {
      expect(DiagnosticStepNames.apiReachability, 'API Reachability');
    });

    test('vpnTcpHandshake is correct', () {
      expect(DiagnosticStepNames.vpnTcpHandshake, 'VPN Server TCP Handshake');
    });

    test('tlsHandshake is correct', () {
      expect(DiagnosticStepNames.tlsHandshake, 'TLS/Reality Handshake');
    });

    test('fullTunnel is correct', () {
      expect(DiagnosticStepNames.fullTunnel, 'Full VPN Tunnel');
    });
  });
}
