import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:flutter_test/flutter_test.dart';

/// Concrete class mixing in [CachedRepository] for testing.
class _TestRepo with CachedRepository {}

void main() {
  late _TestRepo repo;

  setUp(() {
    repo = _TestRepo();
  });

  group('CacheStrategy.cacheFirst', () {
    test('returns cached data when available', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.cacheFirst,
        fetchFromNetwork: () async => 'network',
        readFromCache: () async => 'cached',
        writeToCache: (_) async {},
      );

      expect(result.dataOrNull, 'cached');
    });

    test('fetches from network on cache miss', () async {
      bool networkCalled = false;
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.cacheFirst,
        fetchFromNetwork: () async {
          networkCalled = true;
          return 'network';
        },
        readFromCache: () async => null,
        writeToCache: (_) async {},
      );

      expect(networkCalled, isTrue);
      expect(result.dataOrNull, 'network');
    });

    test('writes to cache after network fetch', () async {
      String? written;
      await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.cacheFirst,
        fetchFromNetwork: () async => 'fresh-data',
        readFromCache: () async => null,
        writeToCache: (data) async => written = data,
      );

      expect(written, 'fresh-data');
    });

    test('returns failure when both cache and network fail', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.cacheFirst,
        fetchFromNetwork: () async => throw Exception('network down'),
        readFromCache: () async => null,
        writeToCache: (_) async {},
      );

      expect(result.isFailure, isTrue);
    });

    test('falls back to network when cache throws', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.cacheFirst,
        fetchFromNetwork: () async => 'network',
        readFromCache: () async => throw Exception('cache corrupt'),
        writeToCache: (_) async {},
      );

      expect(result.dataOrNull, 'network');
    });
  });

  group('CacheStrategy.networkFirst', () {
    test('returns network data when available', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.networkFirst,
        fetchFromNetwork: () async => 'network',
        readFromCache: () async => 'cached',
        writeToCache: (_) async {},
      );

      expect(result.dataOrNull, 'network');
    });

    test('falls back to cache on network error', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.networkFirst,
        fetchFromNetwork: () async => throw Exception('timeout'),
        readFromCache: () async => 'cached',
        writeToCache: (_) async {},
      );

      expect(result.dataOrNull, 'cached');
    });

    test('returns failure when both network and cache fail', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.networkFirst,
        fetchFromNetwork: () async => throw Exception('network'),
        readFromCache: () async => null,
        writeToCache: (_) async {},
      );

      expect(result.isFailure, isTrue);
    });

    test('writes to cache after successful network fetch', () async {
      String? written;
      await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.networkFirst,
        fetchFromNetwork: () async => 'network-data',
        readFromCache: () async => null,
        writeToCache: (data) async => written = data,
      );

      expect(written, 'network-data');
    });
  });

  group('CacheStrategy.cacheOnly', () {
    test('returns cached data', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.cacheOnly,
        fetchFromNetwork: () async => 'network',
        readFromCache: () async => 'cached',
        writeToCache: (_) async {},
      );

      expect(result.dataOrNull, 'cached');
    });

    test('returns failure on cache miss', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.cacheOnly,
        fetchFromNetwork: () async => 'network',
        readFromCache: () async => null,
        writeToCache: (_) async {},
      );

      expect(result.isFailure, isTrue);
    });
  });

  group('CacheStrategy.networkOnly', () {
    test('always fetches from network', () async {
      bool networkCalled = false;
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.networkOnly,
        fetchFromNetwork: () async {
          networkCalled = true;
          return 'network';
        },
        readFromCache: () async => 'cached',
        writeToCache: (_) async {},
      );

      expect(networkCalled, isTrue);
      expect(result.dataOrNull, 'network');
    });

    test('returns failure on network error', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.networkOnly,
        fetchFromNetwork: () async => throw Exception('offline'),
        readFromCache: () async => 'cached',
        writeToCache: (_) async {},
      );

      expect(result.isFailure, isTrue);
    });

    test('writes to cache after network fetch', () async {
      String? written;
      await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.networkOnly,
        fetchFromNetwork: () async => 'fresh',
        readFromCache: () async => null,
        writeToCache: (data) async => written = data,
      );

      expect(written, 'fresh');
    });
  });

  group('CacheStrategy.staleWhileRevalidate', () {
    test('returns cached data immediately', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.staleWhileRevalidate,
        fetchFromNetwork: () async => 'network',
        readFromCache: () async => 'stale',
        writeToCache: (_) async {},
      );

      expect(result.dataOrNull, 'stale');
    });

    test('triggers background refresh when cache exists', () async {
      String? written;
      await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.staleWhileRevalidate,
        fetchFromNetwork: () async => 'fresh',
        readFromCache: () async => 'stale',
        writeToCache: (data) async => written = data,
      );

      // Give the background refresh a tick to complete
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(written, 'fresh');
    });

    test('fetches from network synchronously on cache miss', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.staleWhileRevalidate,
        fetchFromNetwork: () async => 'network',
        readFromCache: () async => null,
        writeToCache: (_) async {},
      );

      expect(result.dataOrNull, 'network');
    });

    test('returns failure when no cache and network fails', () async {
      final result = await repo.executeWithStrategy<String>(
        strategy: CacheStrategy.staleWhileRevalidate,
        fetchFromNetwork: () async => throw Exception('down'),
        readFromCache: () async => null,
        writeToCache: (_) async {},
      );

      expect(result.isFailure, isTrue);
    });
  });

  group('CacheStrategy enum', () {
    test('has all five strategies', () {
      expect(CacheStrategy.values.length, 5);
      expect(CacheStrategy.values, contains(CacheStrategy.cacheFirst));
      expect(CacheStrategy.values, contains(CacheStrategy.networkFirst));
      expect(CacheStrategy.values, contains(CacheStrategy.cacheOnly));
      expect(CacheStrategy.values, contains(CacheStrategy.networkOnly));
      expect(
        CacheStrategy.values,
        contains(CacheStrategy.staleWhileRevalidate),
      );
    });
  });
}
