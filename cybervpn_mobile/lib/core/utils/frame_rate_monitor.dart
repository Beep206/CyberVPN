import 'package:flutter/scheduler.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Monitors frame rendering performance during animation sequences.
///
/// Captures [FrameTiming] data from the Flutter engine and reports dropped
/// frames (build + raster > 16.67ms budget) when the monitoring session ends.
///
/// Usage:
/// ```dart
/// final monitor = FrameRateMonitor('ConnectButton.transition');
/// monitor.start();
/// // ... animation plays ...
/// monitor.stop(); // logs frame stats
/// ```
class FrameRateMonitor {
  FrameRateMonitor(this.label);

  /// Human-readable label for log output (e.g. 'ConnectButton.transition').
  final String label;

  final List<FrameTiming> _timings = [];
  TimingsCallback? _callback;
  bool _active = false;

  /// Begins capturing frame timings from the Flutter engine.
  void start() {
    if (_active) return;
    _active = true;
    _timings.clear();
    _callback = _timings.addAll;
    SchedulerBinding.instance.addTimingsCallback(_callback!);
  }

  /// Stops capturing and logs a summary.
  ///
  /// Returns a [FrameRateReport] with aggregated metrics.
  FrameRateReport stop() {
    if (!_active || _callback == null) {
      return FrameRateReport.empty(label);
    }
    _active = false;
    SchedulerBinding.instance.removeTimingsCallback(_callback!);
    _callback = null;

    final report = FrameRateReport.fromTimings(label, _timings);
    _log(report);
    _timings.clear();
    return report;
  }

  void _log(FrameRateReport report) {
    final logFn = report.droppedFrames > 0 ? AppLogger.warning : AppLogger.info;
    logFn(
      '[$label] ${report.totalFrames} frames, '
      '${report.droppedFrames} dropped '
      '(avg ${report.avgFrameMs.toStringAsFixed(1)}ms, '
      'p99 ${report.p99FrameMs.toStringAsFixed(1)}ms)',
      category: 'perf.frames',
    );
  }
}

/// Aggregated frame-rate metrics for a monitoring session.
class FrameRateReport {
  const FrameRateReport({
    required this.label,
    required this.totalFrames,
    required this.droppedFrames,
    required this.avgFrameMs,
    required this.p99FrameMs,
    required this.maxFrameMs,
  });

  factory FrameRateReport.empty(String label) => FrameRateReport(
        label: label,
        totalFrames: 0,
        droppedFrames: 0,
        avgFrameMs: 0,
        p99FrameMs: 0,
        maxFrameMs: 0,
      );

  factory FrameRateReport.fromTimings(
    String label,
    List<FrameTiming> timings,
  ) {
    if (timings.isEmpty) return FrameRateReport.empty(label);

    // Total frame time = build + rasterize.
    final durations = timings.map((t) {
      final buildUs = t.buildDuration.inMicroseconds;
      final rasterUs = t.rasterDuration.inMicroseconds;
      return (buildUs + rasterUs) / 1000.0; // ms
    }).toList()
      ..sort();

    const frameBudgetMs = 16.667; // 60 fps
    final dropped = durations.where((ms) => ms > frameBudgetMs).length;
    final avg = durations.reduce((a, b) => a + b) / durations.length;
    final p99Index = ((durations.length - 1) * 0.99).round();
    final p99 = durations[p99Index];
    final max = durations.last;

    return FrameRateReport(
      label: label,
      totalFrames: durations.length,
      droppedFrames: dropped,
      avgFrameMs: avg,
      p99FrameMs: p99,
      maxFrameMs: max,
    );
  }

  final String label;
  final int totalFrames;
  final int droppedFrames;
  final double avgFrameMs;
  final double p99FrameMs;
  final double maxFrameMs;
}
