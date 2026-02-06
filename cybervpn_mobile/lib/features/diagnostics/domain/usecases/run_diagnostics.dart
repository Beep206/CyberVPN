import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/repositories/diagnostics_repository.dart';

/// Use case for running a full connection diagnostic sequence.
///
/// Delegates to [DiagnosticsRepository] to execute all diagnostic steps
/// (connectivity, DNS, API reachability, VPN handshake, etc.) and returns
/// the aggregated [DiagnosticResult] with per-step status and suggestions.
@immutable
class RunDiagnosticsUseCase {
  final DiagnosticsRepository _repository;

  const RunDiagnosticsUseCase(this._repository);

  Future<DiagnosticResult> call() async {
    return _repository.runDiagnostics();
  }
}
