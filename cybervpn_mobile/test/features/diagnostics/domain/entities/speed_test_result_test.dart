import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SpeedTestResult', () {
    late SpeedTestResult result;
    late DateTime testedAt;

    setUp(() {
      testedAt = DateTime(2026, 1, 31, 12, 0, 0);
      result = SpeedTestResult(
        downloadMbps: 85.5,
        uploadMbps: 42.3,
        latencyMs: 15,
        jitterMs: 3,
        testedAt: testedAt,
        vpnActive: true,
        serverName: 'Frankfurt DE-1',
      );
    });

    test('creates entity with all required fields', () {
      expect(result.downloadMbps, 85.5);
      expect(result.uploadMbps, 42.3);
      expect(result.latencyMs, 15);
      expect(result.jitterMs, 3);
      expect(result.testedAt, testedAt);
      expect(result.vpnActive, true);
      expect(result.serverName, 'Frankfurt DE-1');
    });

    test('serverName defaults to null when not provided', () {
      final minimal = SpeedTestResult(
        downloadMbps: 50.0,
        uploadMbps: 25.0,
        latencyMs: 20,
        jitterMs: 5,
        testedAt: testedAt,
        vpnActive: false,
      );

      expect(minimal.serverName, isNull);
    });

    test('copyWith preserves unchanged fields', () {
      final updated = result.copyWith(downloadMbps: 100.0);

      expect(updated.downloadMbps, 100.0);
      expect(updated.uploadMbps, result.uploadMbps);
      expect(updated.latencyMs, result.latencyMs);
      expect(updated.jitterMs, result.jitterMs);
      expect(updated.testedAt, result.testedAt);
      expect(updated.vpnActive, result.vpnActive);
      expect(updated.serverName, result.serverName);
    });

    test('equality for identical results', () {
      final result2 = SpeedTestResult(
        downloadMbps: 85.5,
        uploadMbps: 42.3,
        latencyMs: 15,
        jitterMs: 3,
        testedAt: testedAt,
        vpnActive: true,
        serverName: 'Frankfurt DE-1',
      );

      expect(result, equals(result2));
      expect(result.hashCode, equals(result2.hashCode));
    });

    test('inequality for different results', () {
      final result2 = SpeedTestResult(
        downloadMbps: 90.0,
        uploadMbps: 42.3,
        latencyMs: 15,
        jitterMs: 3,
        testedAt: testedAt,
        vpnActive: true,
        serverName: 'Frankfurt DE-1',
      );

      expect(result, isNot(equals(result2)));
    });

    test('toString returns meaningful representation', () {
      final str = result.toString();
      expect(str, contains('SpeedTestResult'));
    });
  });
}
