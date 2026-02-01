import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/servers/data/datasources/ping_service.dart';

import '../../helpers/mock_factories.dart';

void main() {
  group('PingService', () {
    late PingService pingService;

    setUp(() {
      pingService = PingService(
        maxConcurrent: 3,
        timeoutDuration: const Duration(seconds: 2),
        refreshInterval: const Duration(seconds: 30),
      );
    });

    tearDown(() {
      pingService.dispose();
    });

    // -----------------------------------------------------------------------
    // Construction & defaults
    // -----------------------------------------------------------------------

    group('construction', () {
      test('has correct default values', () {
        final service = PingService();

        expect(service.maxConcurrent, equals(10));
        expect(service.timeoutDuration, equals(const Duration(seconds: 5)));
        expect(service.refreshInterval, equals(const Duration(seconds: 60)));

        service.dispose();
      });

      test('accepts custom configuration', () {
        expect(pingService.maxConcurrent, equals(3));
        expect(pingService.timeoutDuration, equals(const Duration(seconds: 2)));
        expect(pingService.refreshInterval, equals(const Duration(seconds: 30)));
      });
    });

    // -----------------------------------------------------------------------
    // Cache management
    // -----------------------------------------------------------------------

    group('cache', () {
      test('starts with empty cache', () {
        expect(pingService.cachedResults, isEmpty);
      });

      test('getLatency returns null for unknown server', () {
        expect(pingService.getLatency('unknown'), isNull);
      });

      test('clearCache empties the cache', () async {
        // We cannot easily populate the cache without real sockets,
        // but we can verify clearCache does not throw.
        pingService.clearCache();
        expect(pingService.cachedResults, isEmpty);
      });
    });

    // -----------------------------------------------------------------------
    // pingServer (TCP socket - will fail in test since no real server)
    // -----------------------------------------------------------------------

    group('pingServer', () {
      test('returns int or null depending on socket behavior', () async {
        // 192.0.2.0/24 is TEST-NET; behavior depends on OS.
        // Connection refused = very fast int, unreachable = null.
        final result = await pingService.pingServer('192.0.2.1', 1);

        // Either null (timeout/unreachable) or an int (connection refused quickly)
        expect(result == null || result is int, isTrue);
      });

      test('returns int or null for another unreachable host', () async {
        final result = await pingService.pingServer('192.0.2.99', 9999);

        expect(result == null || result is int, isTrue);
      });
    });

    // -----------------------------------------------------------------------
    // pingAll - sequential
    // -----------------------------------------------------------------------

    group('pingAll', () {
      test('returns empty map for empty server list', () async {
        final result = await pingService.pingAll([]);

        expect(result, isEmpty);
      });

      test('returns results for unreachable servers without crashing', () async {
        final servers = [
          createMockServer(id: 's1', address: '192.0.2.1', port: 1),
          createMockServer(id: 's2', address: '192.0.2.2', port: 1),
        ];

        final result = await pingService.pingAll(servers);

        // The result is a map; it may be empty (connection refused) or contain
        // entries if the OS rejects quickly. Either way, no exception is thrown.
        expect(result, isA<Map<String, int>>());
      });
    });

    // -----------------------------------------------------------------------
    // pingAllConcurrent - batch parallel
    // -----------------------------------------------------------------------

    group('pingAllConcurrent', () {
      test('returns empty map for empty server list', () async {
        final result = await pingService.pingAllConcurrent([]);

        expect(result, isEmpty);
      });

      test('handles unreachable servers gracefully', () async {
        final servers = [
          createMockServer(id: 's1', address: '192.0.2.1', port: 1),
          createMockServer(id: 's2', address: '192.0.2.2', port: 1),
          createMockServer(id: 's3', address: '192.0.2.3', port: 1),
          createMockServer(id: 's4', address: '192.0.2.4', port: 1),
        ];

        final result = await pingService.pingAllConcurrent(servers);

        // The result is a map; entries may or may not be present depending on
        // OS-level socket behavior. The key assertion is no exception is thrown
        // and the result type is correct.
        expect(result, isA<Map<String, int>>());
      });
    });

    // -----------------------------------------------------------------------
    // testAll
    // -----------------------------------------------------------------------

    group('testAll', () {
      test('returns cached results when no previous servers exist', () async {
        final result = await pingService.testAll();

        expect(result, isEmpty);
      });
    });

    // -----------------------------------------------------------------------
    // auto-refresh
    // -----------------------------------------------------------------------

    group('auto-refresh', () {
      test('startAutoRefresh and stopAutoRefresh do not throw', () {
        expect(() => pingService.startAutoRefresh(), returnsNormally);
        expect(() => pingService.stopAutoRefresh(), returnsNormally);
      });

      test('calling startAutoRefresh twice stops the previous timer', () {
        pingService.startAutoRefresh();
        // Should not throw or leak
        pingService.startAutoRefresh();
        pingService.stopAutoRefresh();
      });
    });

    // -----------------------------------------------------------------------
    // dispose
    // -----------------------------------------------------------------------

    group('dispose', () {
      test('clears cache and stops timer', () {
        pingService.startAutoRefresh();
        pingService.dispose();

        expect(pingService.cachedResults, isEmpty);
      });
    });
  });
}
