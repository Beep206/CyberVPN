import 'dart:async';

import 'package:flutter/scheduler.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

enum StartupPhase { critical, firstFrame, deferred }

class StartupMilestone {
  const StartupMilestone({
    required this.label,
    required this.phase,
    required this.elapsed,
  });

  final String label;
  final StartupPhase phase;
  final Duration elapsed;
}

class StartupMetrics {
  StartupMetrics({this.slowStepThreshold = const Duration(milliseconds: 100)})
    : _totalStopwatch = Stopwatch()..start();

  final Duration slowStepThreshold;
  final Stopwatch _totalStopwatch;
  final List<StartupMilestone> _milestones = <StartupMilestone>[];

  TimingsCallback? _timingsCallback;
  bool _firstFrameRecorded = false;

  List<StartupMilestone> get milestones =>
      List<StartupMilestone>.unmodifiable(_milestones);

  Duration get totalElapsed => _totalStopwatch.elapsed;

  Future<T> measureAsync<T>(
    String label,
    Future<T> Function() action, {
    StartupPhase phase = StartupPhase.critical,
  }) async {
    final stopwatch = Stopwatch()..start();
    final result = await action();
    stopwatch.stop();
    _recordMilestone(label, stopwatch.elapsed, phase: phase);
    return result;
  }

  void recordEvent(String label, {StartupPhase phase = StartupPhase.critical}) {
    _recordMilestone(
      label,
      _totalStopwatch.elapsed,
      phase: phase,
      absolute: true,
    );
  }

  void attachFirstFrameListener() {
    if (_timingsCallback != null || _firstFrameRecorded) {
      return;
    }

    _timingsCallback = (List<FrameTiming> timings) {
      if (_firstFrameRecorded || timings.isEmpty) {
        return;
      }

      final firstFrame = timings.first;
      _firstFrameRecorded = true;

      final totalFrame = firstFrame.buildDuration + firstFrame.rasterDuration;
      _recordMilestone(
        'First frame rendered',
        totalFrame,
        phase: StartupPhase.firstFrame,
      );

      AppLogger.info(
        'First frame metrics: build=${firstFrame.buildDuration.inMilliseconds}ms '
        'raster=${firstFrame.rasterDuration.inMilliseconds}ms '
        'vsyncOverhead=${firstFrame.vsyncOverhead.inMilliseconds}ms',
        category: 'startup',
      );

      dispose();
    };

    SchedulerBinding.instance.addTimingsCallback(_timingsCallback!);
  }

  void logBootstrapComplete({String? modeLabel}) {
    final modeSuffix = modeLabel == null ? '' : ' ($modeLabel)';
    AppLogger.info(
      'Bootstrap complete in ${_totalStopwatch.elapsedMilliseconds}ms '
      '(${_milestones.length} milestones)$modeSuffix',
      category: 'startup',
    );
  }

  void dispose() {
    if (_timingsCallback == null) {
      return;
    }

    SchedulerBinding.instance.removeTimingsCallback(_timingsCallback!);
    _timingsCallback = null;
  }

  void _recordMilestone(
    String label,
    Duration elapsed, {
    required StartupPhase phase,
    bool absolute = false,
  }) {
    final milestone = StartupMilestone(
      label: label,
      phase: phase,
      elapsed: elapsed,
    );
    _milestones.add(milestone);

    final logMessage = absolute
        ? 'Startup event "$label" at ${elapsed.inMilliseconds}ms '
              '[${phase.name}]'
        : 'Startup step "$label" took ${elapsed.inMilliseconds}ms '
              '[${phase.name}]';

    final log = elapsed > slowStepThreshold
        ? AppLogger.warning
        : AppLogger.info;
    log(logMessage, category: 'startup');
  }
}
