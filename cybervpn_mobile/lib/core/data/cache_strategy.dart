import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Describes how a repository should balance cache vs. network.
enum CacheStrategy {
  /// Return cached data if available; fetch from network only on cache miss.
  cacheFirst,

  /// Always fetch from network; fall back to cache on network error.
  networkFirst,

  /// Return only cached data. Never hit the network.
  cacheOnly,

  /// Always fetch from network. Never read cache (but may write to it).
  networkOnly,

  /// Return cached data immediately, then refresh from network in background.
  ///
  /// The initial call returns cached data (or fetches from network on miss).
  /// A background refresh is triggered; the caller can optionally listen for
  /// the updated data via [CachedResult.refreshStream].
  staleWhileRevalidate,
}

/// A result wrapper that includes an optional background refresh stream.
///
/// Used by [CacheStrategy.staleWhileRevalidate] to return stale data
/// immediately while providing a stream for the fresh data when it arrives.
class CachedResult<T> {
  final Result<T> data;
  final Stream<Result<T>>? refreshStream;

  const CachedResult({required this.data, this.refreshStream});
}

/// Mixin that implements cache-strategy dispatch for repository methods.
///
/// Concrete repositories mix this in and call [executeWithStrategy] to
/// get automatic cache/network logic based on the chosen [CacheStrategy].
///
/// Example:
/// ```dart
/// class ServerRepositoryImpl with CachedRepository implements ServerRepository {
///   Future<Result<List<Server>>> getServers({
///     CacheStrategy strategy = CacheStrategy.cacheFirst,
///   }) {
///     return executeWithStrategy(
///       strategy: strategy,
///       fetchFromNetwork: () => _remote.fetchServers(),
///       readFromCache: () => _local.getCachedServers(),
///       writeToCache: (data) => _local.cacheServers(data),
///     );
///   }
/// }
/// ```
mixin CachedRepository {
  /// Executes a data-fetch operation according to the given [strategy].
  ///
  /// [fetchFromNetwork] fetches fresh data from the remote source.
  /// [readFromCache] reads previously cached data (returns `null` on miss).
  /// [writeToCache] persists data to the local cache.
  Future<Result<T>> executeWithStrategy<T>({
    required CacheStrategy strategy,
    required Future<T> Function() fetchFromNetwork,
    required Future<T?> Function() readFromCache,
    required Future<void> Function(T data) writeToCache,
  }) async {
    switch (strategy) {
      case CacheStrategy.cacheFirst:
        return _cacheFirst(
          fetchFromNetwork: fetchFromNetwork,
          readFromCache: readFromCache,
          writeToCache: writeToCache,
        );

      case CacheStrategy.networkFirst:
        return _networkFirst(
          fetchFromNetwork: fetchFromNetwork,
          readFromCache: readFromCache,
          writeToCache: writeToCache,
        );

      case CacheStrategy.cacheOnly:
        return _cacheOnly(readFromCache: readFromCache);

      case CacheStrategy.networkOnly:
        return _networkOnly(
          fetchFromNetwork: fetchFromNetwork,
          writeToCache: writeToCache,
        );

      case CacheStrategy.staleWhileRevalidate:
        return _staleWhileRevalidate(
          fetchFromNetwork: fetchFromNetwork,
          readFromCache: readFromCache,
          writeToCache: writeToCache,
        );
    }
  }

  Future<Result<T>> _cacheFirst<T>({
    required Future<T> Function() fetchFromNetwork,
    required Future<T?> Function() readFromCache,
    required Future<void> Function(T data) writeToCache,
  }) async {
    try {
      final cached = await readFromCache();
      if (cached != null) return Success(cached);
    } catch (e) {
      AppLogger.debug('Cache read failed, falling back to network', error: e);
    }

    try {
      final data = await fetchFromNetwork();
      await writeToCache(data);
      return Success(data);
    } catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }

  Future<Result<T>> _networkFirst<T>({
    required Future<T> Function() fetchFromNetwork,
    required Future<T?> Function() readFromCache,
    required Future<void> Function(T data) writeToCache,
  }) async {
    try {
      final data = await fetchFromNetwork();
      await writeToCache(data);
      return Success(data);
    } catch (networkError) {
      AppLogger.debug(
        'Network fetch failed, falling back to cache',
        error: networkError,
      );

      try {
        final cached = await readFromCache();
        if (cached != null) return Success(cached);
      } catch (cacheError) {
        AppLogger.debug('Cache fallback also failed', error: cacheError);
      }

      return Failure(NetworkFailure(message: networkError.toString()));
    }
  }

  Future<Result<T>> _cacheOnly<T>({
    required Future<T?> Function() readFromCache,
  }) async {
    try {
      final cached = await readFromCache();
      if (cached != null) return Success(cached);
      return const Failure(CacheFailure(message: 'No cached data available'));
    } catch (e) {
      return Failure(CacheFailure(message: e.toString()));
    }
  }

  Future<Result<T>> _networkOnly<T>({
    required Future<T> Function() fetchFromNetwork,
    required Future<void> Function(T data) writeToCache,
  }) async {
    try {
      final data = await fetchFromNetwork();
      await writeToCache(data);
      return Success(data);
    } catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }

  Future<Result<T>> _staleWhileRevalidate<T>({
    required Future<T> Function() fetchFromNetwork,
    required Future<T?> Function() readFromCache,
    required Future<void> Function(T data) writeToCache,
  }) async {
    T? cached;
    try {
      cached = await readFromCache();
    } catch (e) {
      AppLogger.debug('Cache read failed in SWR', error: e);
    }

    if (cached != null) {
      // Fire-and-forget background refresh
      _backgroundRefresh(
        fetchFromNetwork: fetchFromNetwork,
        writeToCache: writeToCache,
      );
      return Success(cached);
    }

    // No cache: must fetch from network synchronously
    try {
      final data = await fetchFromNetwork();
      await writeToCache(data);
      return Success(data);
    } catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }

  Future<void> _backgroundRefresh<T>({
    required Future<T> Function() fetchFromNetwork,
    required Future<void> Function(T data) writeToCache,
  }) async {
    try {
      final data = await fetchFromNetwork();
      await writeToCache(data);
      AppLogger.debug('Background cache refresh completed');
    } catch (e) {
      AppLogger.debug('Background cache refresh failed', error: e);
    }
  }
}
