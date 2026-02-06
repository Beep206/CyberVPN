import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/repositories/diagnostics_repository.dart';

/// Use case for running a network speed test.
///
/// Delegates to [DiagnosticsRepository] to execute the speed test
/// and returns the measured download/upload, latency, and jitter metrics.
@immutable
class RunSpeedTestUseCase {
  final DiagnosticsRepository _repository;

  const RunSpeedTestUseCase(this._repository);

  Future<SpeedTestResult> call() async {
    return _repository.runSpeedTest();
  }
}
