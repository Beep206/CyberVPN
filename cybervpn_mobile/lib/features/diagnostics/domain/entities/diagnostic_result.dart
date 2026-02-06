import 'package:freezed_annotation/freezed_annotation.dart';

part 'diagnostic_result.freezed.dart';

/// Status of an individual diagnostic step.
enum DiagnosticStepStatus {
  pending,
  running,
  success,
  failed,
  warning,
}

/// A single step in the diagnostic process.
///
/// Tracks the step name, execution status, duration, and optional
/// informational message or actionable suggestion on failure.
@freezed
sealed class DiagnosticStep with _$DiagnosticStep {
  const factory DiagnosticStep({
    required String name,
    required DiagnosticStepStatus status,
    Duration? duration,
    String? message,
    String? suggestion,
  }) = _DiagnosticStep;
}

/// Aggregated result of a full diagnostic run.
///
/// Contains the ordered list of diagnostic steps, the timestamp
/// when the diagnostic was initiated, and the total wall-clock duration.
@freezed
sealed class DiagnosticResult with _$DiagnosticResult {
  const factory DiagnosticResult({
    required List<DiagnosticStep> steps,
    required DateTime ranAt,
    required Duration totalDuration,
  }) = _DiagnosticResult;
}
