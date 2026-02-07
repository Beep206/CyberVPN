import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Progress model
// ---------------------------------------------------------------------------

/// Phase of the speed test currently executing.
enum SpeedTestPhase { download, upload, latency, idle }

/// Progress update emitted during a speed test run.
class SpeedTestProgress {
  const SpeedTestProgress({
    required this.phase,
    required this.progressFraction,
    required this.currentSpeedMbps,
    this.currentLatencyMs,
    this.pingCount,
  });

  /// Which phase is running.
  final SpeedTestPhase phase;

  /// Progress from 0.0 to 1.0 within the current phase.
  final double progressFraction;

  /// Instantaneous speed measurement in Mbps (0 for latency phase).
  final double currentSpeedMbps;

  /// Current running average latency (latency phase only).
  final int? currentLatencyMs;

  /// Number of pings completed so far (latency phase only).
  final int? pingCount;
}

// ---------------------------------------------------------------------------
// Speed Test Service
// ---------------------------------------------------------------------------

/// Service that measures download speed, upload speed, latency, and jitter.
///
/// Download: fetches data from a CDN endpoint, measuring throughput over a
/// configurable duration (default 10 s).
///
/// Upload: POSTs random data to a test endpoint, measuring throughput over
/// the same duration.
///
/// Latency: performs a series of HTTP HEAD requests and averages the RTTs.
///
/// Jitter: computes the standard deviation of the individual ping RTTs.
///
/// Results are persisted to [SharedPreferences] as a rolling history of
/// the last [maxHistorySize] entries.
class SpeedTestService {
  SpeedTestService({
    required Dio dio,
    required SharedPreferences sharedPreferences,
    this.downloadUrl = _defaultDownloadUrl,
    this.uploadUrl = _defaultUploadUrl,
    this.pingUrl = _defaultPingUrl,
    this.testDuration = const Duration(seconds: 10),
    this.pingCount = 10,
    this.pingTimeout = const Duration(seconds: 5),
    this.maxHistorySize = 20,
  })  : _dio = dio,
        _prefs = sharedPreferences;

  // ── Default endpoints ────────────────────────────────────────────────

  /// Cloudflare speed-test endpoint that returns random bytes.
  static const _defaultDownloadUrl =
      'https://speed.cloudflare.com/__down?bytes=104857600'; // 100 MB

  /// Cloudflare upload endpoint.
  static const _defaultUploadUrl = 'https://speed.cloudflare.com/__up';

  /// Reliable endpoint for latency pings.
  static const _defaultPingUrl = 'https://1.1.1.1/cdn-cgi/trace';

  /// SharedPreferences key for persisted history.
  static const _historyKey = 'speed_test_history';

  // ── Dependencies ─────────────────────────────────────────────────────

  final Dio _dio;
  final SharedPreferences _prefs;

  // ── Configuration ────────────────────────────────────────────────────

  /// URL used for the download throughput test.
  final String downloadUrl;

  /// URL used for the upload throughput test.
  final String uploadUrl;

  /// URL used for latency pings.
  final String pingUrl;

  /// Duration of the download / upload measurement window.
  final Duration testDuration;

  /// Number of pings to perform for latency / jitter measurement.
  final int pingCount;

  /// Maximum time to wait for a single ping response.
  final Duration pingTimeout;

  /// Maximum number of results to keep in history.
  final int maxHistorySize;

  // ── State ────────────────────────────────────────────────────────────

  bool _isRunning = false;

  /// Whether a speed test is currently in progress.
  bool get isRunning => _isRunning;

  // ====================================================================
  // Public API
  // ====================================================================

  /// Runs a full speed test (download, upload, latency + jitter) and returns
  /// the result.
  ///
  /// Progress updates are emitted on [onProgress] if provided.
  /// The result is automatically saved to the history.
  Future<SpeedTestResult> runSpeedTest({
    bool vpnActive = false,
    String? serverName,
    StreamController<SpeedTestProgress>? progressController,
  }) async {
    if (_isRunning) {
      throw StateError('A speed test is already running.');
    }
    _isRunning = true;

    try {
      // 1. Download
      final downloadMbps = await _measureDownload(progressController);

      // 2. Upload
      final uploadMbps = await _measureUpload(progressController);

      // 3. Latency + Jitter
      final latencyResult = await _measureLatency(progressController);

      final result = SpeedTestResult(
        downloadMbps: downloadMbps,
        uploadMbps: uploadMbps,
        latencyMs: latencyResult.averageMs,
        jitterMs: latencyResult.jitterMs,
        testedAt: DateTime.now(),
        vpnActive: vpnActive,
        serverName: serverName,
      );

      // 4. Persist
      await saveResult(result);

      return result;
    } finally {
      _isRunning = false;
    }
  }

  // ====================================================================
  // Download measurement
  // ====================================================================

  /// Fetches [downloadUrl] for up to [testDuration], measuring throughput.
  ///
  /// Returns speed in Mbps.
  Future<double> _measureDownload(
    StreamController<SpeedTestProgress>? progressController,
  ) async {
    final stopwatch = Stopwatch()..start();
    int totalBytes = 0;
    final durationMs = testDuration.inMilliseconds;

    try {
      final response = await _dio.get<ResponseBody>(
        downloadUrl,
        options: Options(
          responseType: ResponseType.stream,
          receiveTimeout: testDuration + const Duration(seconds: 5),
        ),
      );

      final stream = response.data?.stream;
      if (stream == null) return 0;

      await for (final chunk in stream) {
        totalBytes += chunk.length;
        final elapsedMs = stopwatch.elapsedMilliseconds;

        // Emit progress approximately every second.
        if (progressController != null && !progressController.isClosed) {
          final currentMbps = _bytesToMbps(totalBytes, elapsedMs);
          progressController.add(SpeedTestProgress(
            phase: SpeedTestPhase.download,
            progressFraction: (elapsedMs / durationMs).clamp(0.0, 1.0),
            currentSpeedMbps: currentMbps,
          ));
        }

        if (elapsedMs >= durationMs) break;
      }
    } on DioException {
      // Network error during download -- return whatever we measured.
    } finally {
      stopwatch.stop();
    }

    return _bytesToMbps(totalBytes, stopwatch.elapsedMilliseconds);
  }

  // ====================================================================
  // Upload measurement
  // ====================================================================

  /// POSTs random data to [uploadUrl] for up to [testDuration], measuring
  /// throughput.
  ///
  /// Returns speed in Mbps.
  Future<double> _measureUpload(
    StreamController<SpeedTestProgress>? progressController,
  ) async {
    // Generate a 1 MB payload of random data that we will send repeatedly.
    const chunkSize = 1024 * 1024; // 1 MB
    final payload = _generateRandomBytes(chunkSize);
    final stopwatch = Stopwatch()..start();
    int totalBytes = 0;
    final durationMs = testDuration.inMilliseconds;

    try {
      while (stopwatch.elapsedMilliseconds < durationMs) {
        await _dio.post<void>(
          uploadUrl,
          data: Stream.fromIterable([payload]),
          options: Options(
            contentType: 'application/octet-stream',
            sendTimeout: testDuration + const Duration(seconds: 5),
          ),
        );
        totalBytes += chunkSize;

        if (progressController != null && !progressController.isClosed) {
          final elapsedMs = stopwatch.elapsedMilliseconds;
          progressController.add(SpeedTestProgress(
            phase: SpeedTestPhase.upload,
            progressFraction: (elapsedMs / durationMs).clamp(0.0, 1.0),
            currentSpeedMbps: _bytesToMbps(totalBytes, elapsedMs),
          ));
        }
      }
    } on DioException {
      // Network error during upload -- return whatever we measured.
    } finally {
      stopwatch.stop();
    }

    return _bytesToMbps(totalBytes, stopwatch.elapsedMilliseconds);
  }

  // ====================================================================
  // Latency & jitter measurement
  // ====================================================================

  /// Performs [pingCount] HTTP HEAD requests and returns the average latency
  /// and the jitter (standard deviation) across all pings.
  Future<_LatencyResult> _measureLatency(
    StreamController<SpeedTestProgress>? progressController,
  ) async {
    final pings = <int>[];

    for (var i = 0; i < pingCount; i++) {
      final rtt = await _singlePing();
      if (rtt != null) {
        pings.add(rtt);
      }

      if (progressController != null && !progressController.isClosed) {
        final avgSoFar =
            pings.isEmpty ? 0 : pings.reduce((a, b) => a + b) ~/ pings.length;
        progressController.add(SpeedTestProgress(
          phase: SpeedTestPhase.latency,
          progressFraction: (i + 1) / pingCount,
          currentSpeedMbps: 0,
          currentLatencyMs: avgSoFar,
          pingCount: i + 1,
        ));
      }
    }

    if (pings.isEmpty) {
      return const _LatencyResult(averageMs: 0, jitterMs: 0);
    }

    final averageMs = pings.reduce((a, b) => a + b) ~/ pings.length;
    final jitterMs = _calculateJitter(pings);

    return _LatencyResult(averageMs: averageMs, jitterMs: jitterMs);
  }

  /// Performs a single HTTP HEAD request and returns RTT in milliseconds,
  /// or `null` on failure.
  Future<int?> _singlePing() async {
    try {
      final stopwatch = Stopwatch()..start();
      await _dio.head<void>(
        pingUrl,
        options: Options(receiveTimeout: pingTimeout),
      );
      stopwatch.stop();
      return stopwatch.elapsedMilliseconds;
    } on DioException {
      return null;
    }
  }

  /// Computes the population standard deviation of [values] (jitter).
  ///
  /// Formula: sqrt( sum((x - mean)^2) / n )
  static int _calculateJitter(List<int> values) {
    if (values.length < 2) return 0;
    final mean = values.reduce((a, b) => a + b) / values.length;
    final sumSquaredDiff = values.fold<double>(
      0,
      (sum, v) => sum + (v - mean) * (v - mean),
    );
    return sqrt(sumSquaredDiff / values.length).round();
  }

  // ====================================================================
  // Persistence
  // ====================================================================

  /// Saves [result] to the history, maintaining at most [maxHistorySize]
  /// entries (oldest entries are removed first).
  Future<void> saveResult(SpeedTestResult result) async {
    final history = await getHistory();
    history.insert(0, result);

    // Trim to max size.
    while (history.length > maxHistorySize) {
      history.removeLast();
    }

    final jsonList = history.map(_resultToJson).toList();
    await _prefs.setString(_historyKey, jsonEncode(jsonList));
  }

  /// Returns the stored speed test history sorted by timestamp descending
  /// (most recent first).
  Future<List<SpeedTestResult>> getHistory() async {
    final raw = _prefs.getString(_historyKey);
    if (raw == null || raw.isEmpty) return [];

    try {
      final List<dynamic> jsonList = jsonDecode(raw) as List<dynamic>;
      return jsonList
          .map((e) => _resultFromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      // Corrupt data -- wipe and return empty.
      AppLogger.warning('Corrupt speed test history data, clearing', error: e, category: 'diagnostics');
      await _prefs.remove(_historyKey);
      return [];
    }
  }

  /// Clears all stored speed test history.
  Future<void> clearHistory() async {
    await _prefs.remove(_historyKey);
  }

  // ====================================================================
  // JSON serialization helpers
  // ====================================================================

  static Map<String, dynamic> _resultToJson(SpeedTestResult r) => {
        'downloadMbps': r.downloadMbps,
        'uploadMbps': r.uploadMbps,
        'latencyMs': r.latencyMs,
        'jitterMs': r.jitterMs,
        'testedAt': r.testedAt.toIso8601String(),
        'vpnActive': r.vpnActive,
        'serverName': r.serverName,
      };

  static SpeedTestResult _resultFromJson(Map<String, dynamic> json) =>
      SpeedTestResult(
        downloadMbps: (json['downloadMbps'] as num).toDouble(),
        uploadMbps: (json['uploadMbps'] as num).toDouble(),
        latencyMs: json['latencyMs'] as int,
        jitterMs: json['jitterMs'] as int,
        testedAt: DateTime.parse(json['testedAt'] as String),
        vpnActive: json['vpnActive'] as bool,
        serverName: json['serverName'] as String?,
      );

  // ====================================================================
  // Utilities
  // ====================================================================

  /// Converts bytes transferred over elapsed milliseconds to Mbps.
  static double _bytesToMbps(int bytes, int elapsedMs) {
    if (elapsedMs <= 0) return 0;
    // bits = bytes * 8, megabits = bits / 1_000_000, seconds = ms / 1000
    return (bytes * 8) / (elapsedMs * 1000);
  }

  /// Generates a [Uint8List] of [size] random bytes.
  static Uint8List _generateRandomBytes(int size) {
    final random = Random();
    return Uint8List.fromList(
      List<int>.generate(size, (_) => random.nextInt(256)),
    );
  }
}

// ---------------------------------------------------------------------------
// Internal helper
// ---------------------------------------------------------------------------

class _LatencyResult {
  const _LatencyResult({required this.averageMs, required this.jitterMs});
  final int averageMs;
  final int jitterMs;
}
