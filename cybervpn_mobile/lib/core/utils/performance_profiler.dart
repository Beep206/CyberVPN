import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Performance profiler for measuring operation durations.
///
/// Use this to profile critical operations and ensure they meet
/// performance targets (e.g., auth check < 200ms).
///
/// Example:
/// ```dart
/// final profiler = PerformanceProfiler('auth.check');
/// profiler.start();
/// // ... do work ...
/// profiler.checkpoint('token_read');
/// // ... more work ...
/// profiler.stop();
/// ```
class PerformanceProfiler {
  final String operationName;
  final List<_Checkpoint> _checkpoints = [];
  DateTime? _startTime;
  DateTime? _endTime;

  /// Performance target in milliseconds. Operations exceeding this
  /// will be logged as warnings.
  final int targetMs;

  PerformanceProfiler(
    this.operationName, {
    this.targetMs = 200,
  });

  /// Starts the profiler timer.
  void start() {
    _startTime = DateTime.now();
    _checkpoints.clear();
  }

  /// Records a checkpoint with the given [name].
  void checkpoint(String name) {
    if (_startTime == null) {
      AppLogger.warning(
        'PerformanceProfiler.checkpoint called before start()',
        category: 'perf',
      );
      return;
    }
    _checkpoints.add(_Checkpoint(
      name: name,
      timestamp: DateTime.now(),
    ));
  }

  /// Stops the profiler and logs the results.
  ///
  /// Returns the total duration in milliseconds.
  int stop() {
    _endTime = DateTime.now();

    if (_startTime == null) {
      AppLogger.warning(
        'PerformanceProfiler.stop called before start()',
        category: 'perf',
      );
      return 0;
    }

    final totalMs = _endTime!.difference(_startTime!).inMilliseconds;
    final exceededTarget = totalMs > targetMs;

    // Build checkpoint breakdown
    final buffer = StringBuffer();
    buffer.writeln('[$operationName] Total: ${totalMs}ms (target: ${targetMs}ms)');

    DateTime? previousTime = _startTime;
    for (final checkpoint in _checkpoints) {
      final deltaMs = checkpoint.timestamp.difference(previousTime!).inMilliseconds;
      buffer.writeln('  - ${checkpoint.name}: ${deltaMs}ms');
      previousTime = checkpoint.timestamp;
    }

    if (_checkpoints.isNotEmpty) {
      final finalDelta = _endTime!.difference(previousTime!).inMilliseconds;
      buffer.writeln('  - final: ${finalDelta}ms');
    }

    // Log based on whether target was met
    if (exceededTarget) {
      AppLogger.warning(
        buffer.toString(),
        category: 'perf.$operationName',
      );
    } else {
      AppLogger.info(
        buffer.toString(),
        category: 'perf.$operationName',
      );
    }

    return totalMs;
  }

  /// Returns the elapsed time in milliseconds since start, or 0 if not started.
  int get elapsedMs {
    if (_startTime == null) return 0;
    return DateTime.now().difference(_startTime!).inMilliseconds;
  }
}

class _Checkpoint {
  final String name;
  final DateTime timestamp;

  _Checkpoint({
    required this.name,
    required this.timestamp,
  });
}

/// Global performance profiler instances for commonly profiled operations.
class AppProfilers {
  AppProfilers._();

  /// Auth check profiler (target: 200ms)
  static PerformanceProfiler authCheck() =>
      PerformanceProfiler('auth.check', targetMs: 200);

  /// Biometric check profiler (target: 100ms)
  static PerformanceProfiler biometricCheck() =>
      PerformanceProfiler('biometric.check', targetMs: 100);

  /// Secure storage read profiler (target: 50ms)
  static PerformanceProfiler secureStorageRead() =>
      PerformanceProfiler('secure_storage.read', targetMs: 50);

  /// App startup profiler (target: 500ms)
  static PerformanceProfiler appStartup() =>
      PerformanceProfiler('app.startup', targetMs: 500);
}
