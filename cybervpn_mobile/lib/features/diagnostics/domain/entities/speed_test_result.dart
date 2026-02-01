import 'package:freezed_annotation/freezed_annotation.dart';

part 'speed_test_result.freezed.dart';

/// Speed test result entity containing network performance metrics.
///
/// Captures download/upload throughput, latency, and jitter measurements
/// along with VPN connection context at the time of testing.
@freezed
abstract class SpeedTestResult with _$SpeedTestResult {
  const factory SpeedTestResult({
    required double downloadMbps,
    required double uploadMbps,
    required int latencyMs,
    required int jitterMs,
    required DateTime testedAt,
    required bool vpnActive,
    String? serverName,
  }) = _SpeedTestResult;
}
