import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show dioProvider;
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/diagnostics/data/services/diagnostic_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/data/services/speed_test_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';

// ---------------------------------------------------------------------------
// Log Entry
// ---------------------------------------------------------------------------

/// A timestamped log entry produced during diagnostics operations.
class LogEntry {
  const LogEntry({
    required this.timestamp,
    required this.level,
    required this.message,
  });

  final DateTime timestamp;
  final String level;
  final String message;

  Map<String, dynamic> toJson() => {
        'timestamp': timestamp.toIso8601String(),
        'level': level,
        'message': message,
      };
}

// ---------------------------------------------------------------------------
// Diagnostics State
// ---------------------------------------------------------------------------

/// Immutable state for the diagnostics feature.
class DiagnosticsState {
  const DiagnosticsState({
    this.speedTestResult,
    this.isRunningSpeedTest = false,
    this.diagnosticResult,
    this.isRunningDiagnostics = false,
    this.speedHistory = const [],
    this.logEntries = const [],
  });

  /// Most recent speed test result, if any.
  final SpeedTestResult? speedTestResult;

  /// Whether a speed test is currently in progress.
  final bool isRunningSpeedTest;

  /// Most recent diagnostics result, if any.
  final DiagnosticResult? diagnosticResult;

  /// Whether a diagnostics run is currently in progress.
  final bool isRunningDiagnostics;

  /// Speed test history, most recent first.
  final List<SpeedTestResult> speedHistory;

  /// Timestamped log entries from diagnostics operations.
  final List<LogEntry> logEntries;

  DiagnosticsState copyWith({
    SpeedTestResult? Function()? speedTestResult,
    bool? isRunningSpeedTest,
    DiagnosticResult? Function()? diagnosticResult,
    bool? isRunningDiagnostics,
    List<SpeedTestResult>? speedHistory,
    List<LogEntry>? logEntries,
  }) {
    return DiagnosticsState(
      speedTestResult: speedTestResult != null
          ? speedTestResult()
          : this.speedTestResult,
      isRunningSpeedTest: isRunningSpeedTest ?? this.isRunningSpeedTest,
      diagnosticResult: diagnosticResult != null
          ? diagnosticResult()
          : this.diagnosticResult,
      isRunningDiagnostics: isRunningDiagnostics ?? this.isRunningDiagnostics,
      speedHistory: speedHistory ?? this.speedHistory,
      logEntries: logEntries ?? this.logEntries,
    );
  }
}

// ---------------------------------------------------------------------------
// Dependency providers (override in DI setup / tests)
// ---------------------------------------------------------------------------

/// Provides the [SpeedTestService] lazily via ref.watch.
final speedTestServiceProvider = Provider<SpeedTestService>((ref) {
  return SpeedTestService(
    dio: ref.watch(dioProvider),
    sharedPreferences: ref.watch(sharedPreferencesProvider),
  );
});

/// Provides the [DiagnosticService] lazily via ref.watch.
final diagnosticServiceProvider = Provider<DiagnosticService>((ref) {
  return DiagnosticService(dio: ref.watch(dioProvider));
});

// ---------------------------------------------------------------------------
// DiagnosticsNotifier
// ---------------------------------------------------------------------------

final diagnosticsProvider =
    AsyncNotifierProvider<DiagnosticsNotifier, DiagnosticsState>(
  DiagnosticsNotifier.new,
);

/// Manages speed test and diagnostics state.
///
/// Provides methods to run speed tests and connection diagnostics,
/// maintain history, and export logs.
class DiagnosticsNotifier extends AsyncNotifier<DiagnosticsState> {
  late final SpeedTestService _speedTestService;
  late final DiagnosticService _diagnosticService;

  @override
  Future<DiagnosticsState> build() async {
    _speedTestService = ref.watch(speedTestServiceProvider);
    _diagnosticService = ref.watch(diagnosticServiceProvider);

    // Load persisted speed test history on init.
    final history = await _speedTestService.getHistory();

    return DiagnosticsState(speedHistory: history);
  }

  // -- Public API -----------------------------------------------------------

  /// Runs a full speed test (download, upload, latency, jitter).
  ///
  /// Updates [DiagnosticsState.isRunningSpeedTest] during execution and
  /// stores the result in [DiagnosticsState.speedTestResult] and
  /// [DiagnosticsState.speedHistory].
  Future<void> runSpeedTest({
    bool vpnActive = false,
    String? serverName,
  }) async {
    final current = state.value;
    if (current == null || current.isRunningSpeedTest) return;

    _updateState(current.copyWith(isRunningSpeedTest: true));
    _addLog('info', 'Speed test started');

    try {
      final result = await _speedTestService.runSpeedTest(
        vpnActive: vpnActive,
        serverName: serverName,
      );

      // Reload history from persistence (service already saved the result).
      final updatedHistory = await _speedTestService.getHistory();

      final updated = state.value ?? current;
      _updateState(updated.copyWith(
        speedTestResult: () => result,
        isRunningSpeedTest: false,
        speedHistory: updatedHistory,
      ));

      _addLog(
        'info',
        'Speed test completed: '
            '${result.downloadMbps.toStringAsFixed(1)} Mbps down, '
            '${result.uploadMbps.toStringAsFixed(1)} Mbps up, '
            '${result.latencyMs} ms latency',
      );
    } catch (e, st) {
      AppLogger.error('Speed test failed', error: e, stackTrace: st);

      final updated = state.value ?? current;
      _updateState(updated.copyWith(isRunningSpeedTest: false));
      _addLog('error', 'Speed test failed: $e');
    }
  }

  /// Runs the full connection diagnostic sequence.
  ///
  /// Updates [DiagnosticsState.isRunningDiagnostics] during execution and
  /// stores the aggregated result in [DiagnosticsState.diagnosticResult].
  /// Each step completion is logged.
  Future<void> runDiagnostics({
    DiagnosticServerTarget? serverTarget,
  }) async {
    final current = state.value;
    if (current == null || current.isRunningDiagnostics) return;

    _updateState(current.copyWith(isRunningDiagnostics: true));
    _addLog('info', 'Diagnostics started');

    try {
      final startTime = DateTime.now();
      final steps = <DiagnosticStep>[];

      await for (final step
          in _diagnosticService.runDiagnostics(serverTarget: serverTarget)) {
        steps.add(step);

        // Log each step as it completes.
        _addLog(
          step.status == DiagnosticStepStatus.failed ? 'error' : 'info',
          '${step.name}: ${step.status.name}'
              '${step.message != null ? ' - ${step.message}' : ''}',
        );

        // Update state with partial result so UI can show progress.
        final partialResult = DiagnosticResult(
          steps: List.unmodifiable(steps),
          ranAt: startTime,
          totalDuration: DateTime.now().difference(startTime),
        );

        final updated = state.value ?? current;
        _updateState(updated.copyWith(
          diagnosticResult: () => partialResult,
        ));
      }

      final totalDuration = DateTime.now().difference(startTime);
      final finalResult = DiagnosticResult(
        steps: List.unmodifiable(steps),
        ranAt: startTime,
        totalDuration: totalDuration,
      );

      final updated = state.value ?? current;
      _updateState(updated.copyWith(
        diagnosticResult: () => finalResult,
        isRunningDiagnostics: false,
      ));

      _addLog('info', 'Diagnostics completed in ${totalDuration.inSeconds}s');
    } catch (e, st) {
      AppLogger.error('Diagnostics failed', error: e, stackTrace: st);

      final updated = state.value ?? current;
      _updateState(updated.copyWith(isRunningDiagnostics: false));
      _addLog('error', 'Diagnostics failed: $e');
    }
  }

  /// Returns the speed test history sorted by timestamp descending.
  List<SpeedTestResult> getHistory() {
    final current = state.value;
    if (current == null) return [];

    final sorted = List<SpeedTestResult>.from(current.speedHistory);
    sorted.sort((a, b) => b.testedAt.compareTo(a.testedAt));
    return sorted;
  }

  /// Exports log entries as a JSON-formatted string.
  String exportLogs() {
    final current = state.value;
    if (current == null) return '[]';

    final jsonList = current.logEntries.map((e) => e.toJson()).toList();
    return const JsonEncoder.withIndent('  ').convert(jsonList);
  }

  // -- Private helpers ------------------------------------------------------

  /// Updates state without replacing the AsyncData wrapper.
  void _updateState(DiagnosticsState newState) {
    state = AsyncData(newState);
  }

  /// Appends a [LogEntry] to the current state's log entries.
  void _addLog(String level, String message) {
    final current = state.value;
    if (current == null) return;

    final entry = LogEntry(
      timestamp: DateTime.now(),
      level: level,
      message: message,
    );

    _updateState(current.copyWith(
      logEntries: [...current.logEntries, entry],
    ));
  }
}

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Whether a speed test is currently running.
final speedTestProgressProvider = Provider<bool>((ref) {
  final asyncState = ref.watch(diagnosticsProvider);
  return asyncState.value?.isRunningSpeedTest ?? false;
});

/// Current diagnostic steps from the most recent diagnostic run.
///
/// Returns an empty list if no diagnostics have been run.
final diagnosticStepsProvider = Provider<List<DiagnosticStep>>((ref) {
  final asyncState = ref.watch(diagnosticsProvider);
  return asyncState.value?.diagnosticResult?.steps ?? [];
});

/// The most recent speed test result, or null.
final latestSpeedTestProvider = Provider<SpeedTestResult?>((ref) {
  final asyncState = ref.watch(diagnosticsProvider);
  return asyncState.value?.speedTestResult;
});

/// Speed test history list, most recent first.
final speedHistoryProvider = Provider<List<SpeedTestResult>>((ref) {
  final asyncState = ref.watch(diagnosticsProvider);
  return asyncState.value?.speedHistory ?? [];
});

/// Whether diagnostics are currently running.
final isRunningDiagnosticsProvider = Provider<bool>((ref) {
  final asyncState = ref.watch(diagnosticsProvider);
  return asyncState.value?.isRunningDiagnostics ?? false;
});
