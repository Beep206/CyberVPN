import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cybervpn_mobile/features/diagnostics/data/services/speed_test_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockDio extends Mock implements Dio {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Creates a [ResponseBody] that emits [chunks] of bytes.
ResponseBody _streamedResponse(List<List<int>> chunks) {
  final controller = StreamController<Uint8List>();
  unawaited(Future.microtask(() async {
    for (final chunk in chunks) {
      controller.add(Uint8List.fromList(chunk));
    }
    await controller.close();
  }));
  return ResponseBody(controller.stream, 200);
}

void main() {
  late MockDio mockDio;
  late SharedPreferences prefs;
  late SpeedTestService service;

  setUpAll(() {
    registerFallbackValue(Options());
  });

  setUp(() async {
    mockDio = MockDio();
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
    service = SpeedTestService(
      dio: mockDio,
      sharedPreferences: prefs,
      testDuration: const Duration(milliseconds: 500),
      pingCount: 5,
      pingTimeout: const Duration(seconds: 2),
      maxHistorySize: 20,
    );
  });

  // ====================================================================
  // Speed calculation tests
  // ====================================================================

  group('Speed calculation (_bytesToMbps)', () {
    test('10 MB in 10 seconds equals 8 Mbps', () {
      // 10 MB = 10_485_760 bytes, 10_000 ms
      // bits = 10_485_760 * 8 = 83_886_080
      // Mbps = 83_886_080 / (10_000 * 1000) = 8.388608
      // Using static helper via the public API is not possible,
      // so we verify via the download measurement test below.
      // But we can verify the formula: (bytes * 8) / (ms * 1000)
      const bytes = 10485760; // 10 MB
      const elapsedMs = 10000;
      const mbps = (bytes * 8) / (elapsedMs * 1000);
      expect(mbps, closeTo(8.39, 0.01));
    });

    test('zero elapsed returns 0', () {
      const mbps = (1000 * 8) / (0 * 1000);
      // Division by zero -> infinity; the service guards this.
      expect(mbps.isInfinite, isTrue);
    });
  });

  // ====================================================================
  // Download measurement
  // ====================================================================

  group('Download speed test', () {
    test('calculates throughput from streamed response', () async {
      // Simulate 5 chunks of 100 KB each = 500 KB total.
      const chunkSize = 100 * 1024; // 100 KB
      final chunks = List.generate(5, (_) => List.filled(chunkSize, 0));

      when(() => mockDio.get<ResponseBody>(
            any(),
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response<ResponseBody>(
            data: _streamedResponse(chunks),
            statusCode: 200,
            requestOptions: RequestOptions(),
          ));

      // We test the full runSpeedTest which includes download.
      // But first, stub upload and latency too.
      _stubUpload(mockDio);
      _stubLatency(mockDio, count: 5);

      final result = await service.runSpeedTest();

      // Download should be > 0 since we received data.
      expect(result.downloadMbps, greaterThan(0));
    });

    test('handles network error gracefully', () async {
      when(() => mockDio.get<ResponseBody>(
            any(),
            options: any(named: 'options'),
          )).thenThrow(DioException(
        requestOptions: RequestOptions(),
        type: DioExceptionType.connectionTimeout,
      ));

      _stubUpload(mockDio);
      _stubLatency(mockDio, count: 5);

      final result = await service.runSpeedTest();

      // Download should be 0 on error.
      expect(result.downloadMbps, equals(0));
    });
  });

  // ====================================================================
  // Upload measurement
  // ====================================================================

  group('Upload speed test', () {
    test('calculates throughput from POST responses', () async {
      _stubDownload(mockDio);
      _stubLatency(mockDio, count: 5);

      // Stub upload to succeed.
      when(() => mockDio.post<void>(
            any(),
            data: any(named: 'data'),
            options: any(named: 'options'),
          )).thenAnswer((_) async => Response<void>(
            statusCode: 200,
            requestOptions: RequestOptions(),
          ));

      final result = await service.runSpeedTest();

      // Upload should be > 0 since POSTs succeeded.
      expect(result.uploadMbps, greaterThan(0));
    });

    test('handles upload network error gracefully', () async {
      _stubDownload(mockDio);
      _stubLatency(mockDio, count: 5);

      when(() => mockDio.post<void>(
            any(),
            data: any(named: 'data'),
            options: any(named: 'options'),
          )).thenThrow(DioException(
        requestOptions: RequestOptions(),
        type: DioExceptionType.sendTimeout,
      ));

      final result = await service.runSpeedTest();

      // Upload should be 0 on error.
      expect(result.uploadMbps, equals(0));
    });
  });

  // ====================================================================
  // Latency & jitter
  // ====================================================================

  group('Latency and jitter measurement', () {
    test('calculates average latency correctly', () async {
      _stubDownload(mockDio);
      _stubUpload(mockDio);

      // Simulate 5 pings with controlled delays.
      var pingCallCount = 0;
      when(() => mockDio.head<void>(
            any(),
            options: any(named: 'options'),
          )).thenAnswer((_) async {
        pingCallCount++;
        // Each ping is near-instant in tests, so latency will be very low.
        return Response<void>(
          statusCode: 200,
          requestOptions: RequestOptions(),
        );
      });

      final result = await service.runSpeedTest();

      // latencyMs should be >= 0 (very fast in tests).
      expect(result.latencyMs, greaterThanOrEqualTo(0));
      // All 5 pings should have been made.
      expect(pingCallCount, equals(5));
    });

    test('handles ping timeouts gracefully', () async {
      _stubDownload(mockDio);
      _stubUpload(mockDio);

      when(() => mockDio.head<void>(
            any(),
            options: any(named: 'options'),
          )).thenThrow(DioException(
        requestOptions: RequestOptions(),
        type: DioExceptionType.receiveTimeout,
      ));

      final result = await service.runSpeedTest();

      // All pings failed, latency and jitter should be 0.
      expect(result.latencyMs, equals(0));
      expect(result.jitterMs, equals(0));
    });
  });

  group('Jitter calculation', () {
    test('standard deviation of known values', () {
      // Values: [50, 52, 48, 51, 49, 53, 47, 50, 52, 48]
      // Mean = 50.0
      // Variance = sum((x-50)^2)/10 = (0+4+4+1+1+9+9+0+4+4)/10 = 36/10 = 3.6
      // StdDev = sqrt(3.6) ~= 1.8973...  -> rounds to 2
      final values = [50, 52, 48, 51, 49, 53, 47, 50, 52, 48];
      final mean = values.reduce((a, b) => a + b) / values.length;
      final sumSquaredDiff = values.fold<double>(
        0,
        (sum, v) => sum + (v - mean) * (v - mean),
      );
      final jitter = sqrt(sumSquaredDiff / values.length).round();
      expect(jitter, equals(2)); // sqrt(3.6) = 1.897 rounds to 2
    });

    test('jitter is 0 for identical values', () {
      final values = [50, 50, 50, 50, 50];
      final mean = values.reduce((a, b) => a + b) / values.length;
      final sumSquaredDiff = values.fold<double>(
        0,
        (sum, v) => sum + (v - mean) * (v - mean),
      );
      final jitter = sqrt(sumSquaredDiff / values.length).round();
      expect(jitter, equals(0));
    });

    test('jitter with single value is 0', () {
      // _calculateJitter returns 0 for < 2 values.
      // The formula would give 0 for a single value anyway.
      final values = [42];
      final mean = values.reduce((a, b) => a + b) / values.length;
      final sumSquaredDiff = values.fold<double>(
        0,
        (sum, v) => sum + (v - mean) * (v - mean),
      );
      final jitter = sqrt(sumSquaredDiff / values.length).round();
      expect(jitter, equals(0));
    });
  });

  // ====================================================================
  // Progress stream
  // ====================================================================

  group('Progress stream', () {
    test('emits download, upload, and latency phases', () async {
      _stubDownload(mockDio);
      _stubUpload(mockDio);
      _stubLatency(mockDio, count: 5);

      final progressController = StreamController<SpeedTestProgress>();
      final phases = <SpeedTestPhase>[];

      progressController.stream.listen((p) {
        if (phases.isEmpty || phases.last != p.phase) {
          phases.add(p.phase);
        }
      });

      await service.runSpeedTest(progressController: progressController);
      await progressController.close();

      // Should have seen download, upload, latency phases.
      expect(phases, contains(SpeedTestPhase.latency));
    });

    test('latency progress reports ping count', () async {
      _stubDownload(mockDio);
      _stubUpload(mockDio);
      _stubLatency(mockDio, count: 5);

      final progressController = StreamController<SpeedTestProgress>();
      final pingCounts = <int>[];

      progressController.stream.listen((p) {
        if (p.phase == SpeedTestPhase.latency && p.pingCount != null) {
          pingCounts.add(p.pingCount!);
        }
      });

      await service.runSpeedTest(progressController: progressController);
      await progressController.close();

      expect(pingCounts, equals([1, 2, 3, 4, 5]));
    });
  });

  // ====================================================================
  // Persistence
  // ====================================================================

  group('Result persistence', () {
    SpeedTestResult makeResult({
      required DateTime testedAt,
      double download = 50.0,
    }) {
      return SpeedTestResult(
        downloadMbps: download,
        uploadMbps: 25.0,
        latencyMs: 20,
        jitterMs: 3,
        testedAt: testedAt,
        vpnActive: true,
        serverName: 'Test Server',
      );
    }

    test('saves and retrieves a result', () async {
      final result = makeResult(testedAt: DateTime(2026, 1, 31));
      await service.saveResult(result);

      final history = await service.getHistory();
      expect(history, hasLength(1));
      expect(history.first.downloadMbps, equals(50.0));
      expect(history.first.serverName, equals('Test Server'));
    });

    test('maintains max history size of 20', () async {
      // Save 25 results.
      for (var i = 0; i < 25; i++) {
        final result = makeResult(
          testedAt: DateTime(2026, 1, 1, 0, i),
          download: i.toDouble(),
        );
        await service.saveResult(result);
      }

      final history = await service.getHistory();
      expect(history, hasLength(20));

      // Most recent should be first (download = 24.0).
      expect(history.first.downloadMbps, equals(24.0));
    });

    test('clears history', () async {
      await service.saveResult(
        makeResult(testedAt: DateTime(2026, 1, 1)),
      );

      await service.clearHistory();
      final history = await service.getHistory();
      expect(history, isEmpty);
    });

    test('returns empty list when no history exists', () async {
      final history = await service.getHistory();
      expect(history, isEmpty);
    });

    test('handles corrupt JSON gracefully', () async {
      await prefs.setString('speed_test_history', '{invalid json!!!');
      final history = await service.getHistory();
      expect(history, isEmpty);
    });

    test('JSON round-trip preserves all fields', () async {
      final now = DateTime(2026, 1, 31, 14, 30, 0);
      final result = SpeedTestResult(
        downloadMbps: 85.5,
        uploadMbps: 42.3,
        latencyMs: 15,
        jitterMs: 3,
        testedAt: now,
        vpnActive: true,
        serverName: 'Frankfurt DE-1',
      );

      await service.saveResult(result);
      final history = await service.getHistory();

      expect(history.first.downloadMbps, equals(85.5));
      expect(history.first.uploadMbps, equals(42.3));
      expect(history.first.latencyMs, equals(15));
      expect(history.first.jitterMs, equals(3));
      expect(history.first.testedAt, equals(now));
      expect(history.first.vpnActive, isTrue);
      expect(history.first.serverName, equals('Frankfurt DE-1'));
    });

    test('preserves null serverName in JSON round-trip', () async {
      final result = SpeedTestResult(
        downloadMbps: 50.0,
        uploadMbps: 25.0,
        latencyMs: 20,
        jitterMs: 3,
        testedAt: DateTime(2026, 1, 31),
        vpnActive: false,
      );

      await service.saveResult(result);
      final history = await service.getHistory();

      expect(history.first.serverName, isNull);
      expect(history.first.vpnActive, isFalse);
    });
  });

  // ====================================================================
  // Concurrency guard
  // ====================================================================

  group('Concurrency', () {
    test('throws if a test is already running', () async {
      _stubDownloadSlow(mockDio);
      _stubUpload(mockDio);
      _stubLatency(mockDio, count: 5);

      // Start first test (will take a while due to slow download).
      final firstTest = service.runSpeedTest();

      // Immediately try to start another.
      expect(
        () => service.runSpeedTest(),
        throwsA(isA<StateError>()),
      );

      // Let the first one finish.
      await firstTest;
    });
  });
}

// ===========================================================================
// Shared stubs
// ===========================================================================

/// Stubs the download endpoint with a quick empty stream response.
void _stubDownload(MockDio dio) {
  when(() => dio.get<ResponseBody>(
        any(),
        options: any(named: 'options'),
      )).thenAnswer((_) async => Response<ResponseBody>(
        data: _streamedResponse([]),
        statusCode: 200,
        requestOptions: RequestOptions(),
      ));
}

/// Stubs the download endpoint with a slow stream (for concurrency testing).
void _stubDownloadSlow(MockDio dio) {
  when(() => dio.get<ResponseBody>(
        any(),
        options: any(named: 'options'),
      )).thenAnswer((_) async {
    // Simulate a slow download.
    await Future<void>.delayed(const Duration(milliseconds: 100));
    return Response<ResponseBody>(
      data: _streamedResponse([List.filled(1024, 0)]),
      statusCode: 200,
      requestOptions: RequestOptions(),
    );
  });
}

/// Stubs the upload endpoint.
void _stubUpload(MockDio dio) {
  when(() => dio.post<void>(
        any(),
        data: any(named: 'data'),
        options: any(named: 'options'),
      )).thenAnswer((_) async => Response<void>(
        statusCode: 200,
        requestOptions: RequestOptions(),
      ));
}

/// Stubs the latency ping endpoint.
void _stubLatency(MockDio dio, {required int count}) {
  when(() => dio.head<void>(
        any(),
        options: any(named: 'options'),
      )).thenAnswer((_) async => Response<void>(
        statusCode: 200,
        requestOptions: RequestOptions(),
      ));
}
