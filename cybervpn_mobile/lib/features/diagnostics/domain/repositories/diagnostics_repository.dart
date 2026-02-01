import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';

/// Repository contract for diagnostics operations.
///
/// Defines the interface for speed testing and connection diagnostics.
/// Implementations live in the data layer.
abstract class DiagnosticsRepository {
  /// Runs a network speed test and returns the result.
  Future<SpeedTestResult> runSpeedTest();

  /// Runs a full connection diagnostic sequence and returns the result.
  Future<DiagnosticResult> runDiagnostics();
}
