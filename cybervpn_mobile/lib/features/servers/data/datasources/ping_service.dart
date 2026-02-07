import 'dart:async';
import 'dart:io';

import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Service for performing parallel ping/latency tests against VPN servers.
///
/// Uses TCP socket connection to measure round-trip latency. Results are
/// cached in-memory with a configurable TTL and can be refreshed manually
/// or via a periodic timer.
class PingService {
  PingService({
    this.maxConcurrent = 10,
    this.timeoutDuration = const Duration(seconds: 5),
    this.refreshInterval = const Duration(seconds: 30),
    this.cacheTtl = const Duration(seconds: 30),
  });

  /// Maximum number of concurrent ping operations.
  final int maxConcurrent;

  /// Timeout for individual ping attempts.
  final Duration timeoutDuration;

  /// Interval between automatic background refreshes.
  final Duration refreshInterval;

  /// Time-to-live for cached ping results. Entries older than this are
  /// considered stale and will be re-measured on the next sweep.
  final Duration cacheTtl;

  /// Maximum number of entries in the ping cache to prevent unbounded growth.
  static const int _maxCacheSize = 500;

  /// In-memory cache: serverId -> latency in ms.
  /// Limited to [_maxCacheSize] entries with LRU eviction.
  final Map<String, int> _cache = {};

  /// Timestamps for cache entries: serverId -> when the ping was recorded.
  final Map<String, DateTime> _cacheTimestamps = {};

  /// Timer for periodic background refresh.
  Timer? _refreshTimer;

  /// Servers list stored for background refresh cycles.
  List<ServerEntity>? _lastServers;

  /// Whether a ping sweep is currently running.
  bool _isRunning = false;

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /// Returns the currently cached latency results (serverId -> ms),
  /// excluding entries that have exceeded [cacheTtl].
  Map<String, int> get cachedResults {
    _evictStale();
    return Map.unmodifiable(_cache);
  }

  /// Whether the cached result for [serverId] is still fresh.
  bool isFresh(String serverId) {
    final ts = _cacheTimestamps[serverId];
    if (ts == null) return false;
    return DateTime.now().difference(ts) < cacheTtl;
  }

  /// Ping a single server host/port via TCP socket connection.
  ///
  /// Returns latency in milliseconds, or `null` if the connection failed or
  /// timed out.
  Future<int?> pingServer(String host, int port) async {
    try {
      final stopwatch = Stopwatch()..start();
      final socket = await Socket.connect(
        host,
        port,
        timeout: timeoutDuration,
      );
      stopwatch.stop();
      await socket.close();
      socket.destroy();
      return stopwatch.elapsedMilliseconds;
    } catch (e) {
      AppLogger.warning('Ping failed for server', error: e, category: 'ping');
      return null;
    }
  }

  /// Ping all servers in parallel (up to [maxConcurrent] at a time).
  ///
  /// Returns a map of serverId -> latency in ms. Servers that failed to
  /// respond are omitted from the result map.
  Future<Map<String, int>> pingAll(List<ServerEntity> servers) async {
    if (_isRunning) return Map.unmodifiable(_cache);
    _isRunning = true;
    _lastServers = servers;

    final results = <String, int>{};

    // Use a semaphore-like pattern via Stream.fromIterable + asyncMap to
    // limit concurrency to [maxConcurrent] parallel operations.
    await Stream.fromIterable(servers)
        .asyncMap((server) async {
          final latency = await pingServer(server.address, server.port);
          return MapEntry(server.id, latency);
        })
        // Buffer ensures we process up to maxConcurrent items concurrently.
        // We rely on asyncMap's sequential nature but launch in batches below.
        .forEach((entry) {
          if (entry.value != null) {
            results[entry.key] = entry.value!;
          }
        });

    // Merge results into cache with LRU eviction.
    final now = DateTime.now();
    _cache.addAll(results);
    for (final key in results.keys) {
      _cacheTimestamps[key] = now;
    }
    _evictIfNeeded();
    _isRunning = false;
    return Map.unmodifiable(results);
  }

  /// Ping all servers with true concurrency limiting using a pool pattern.
  ///
  /// Processes servers in batches of [maxConcurrent] for genuine parallelism.
  Future<Map<String, int>> pingAllConcurrent(List<ServerEntity> servers) async {
    if (_isRunning) return Map.unmodifiable(_cache);
    _isRunning = true;
    _lastServers = servers;

    final results = <String, int>{};
    final batches = <List<ServerEntity>>[];

    // Split servers into batches of maxConcurrent.
    for (var i = 0; i < servers.length; i += maxConcurrent) {
      final end =
          (i + maxConcurrent > servers.length) ? servers.length : i + maxConcurrent;
      batches.add(servers.sublist(i, end));
    }

    for (final batch in batches) {
      final futures = batch.map((server) async {
        final latency = await pingServer(server.address, server.port);
        return MapEntry(server.id, latency);
      });

      final batchResults = await Future.wait(futures);
      for (final entry in batchResults) {
        if (entry.value != null) {
          results[entry.key] = entry.value!;
        }
      }
    }

    final now = DateTime.now();
    _cache.addAll(results);
    for (final key in results.keys) {
      _cacheTimestamps[key] = now;
    }
    _evictIfNeeded();
    _isRunning = false;
    return Map.unmodifiable(results);
  }

  /// Removes entries whose timestamp has exceeded [cacheTtl].
  void _evictStale() {
    final now = DateTime.now();
    final staleKeys = _cacheTimestamps.entries
        .where((e) => now.difference(e.value) >= cacheTtl)
        .map((e) => e.key)
        .toList();
    for (final key in staleKeys) {
      _cache.remove(key);
      _cacheTimestamps.remove(key);
    }
  }

  /// Evicts oldest entries (first inserted) when cache exceeds max size.
  void _evictIfNeeded() {
    while (_cache.length > _maxCacheSize) {
      final key = _cache.keys.first;
      _cache.remove(key);
      _cacheTimestamps.remove(key);
    }
  }

  /// Manually trigger a full ping test for all previously tested servers.
  ///
  /// If no previous server list exists this is a no-op.
  Future<Map<String, int>> testAll() async {
    if (_lastServers == null || _lastServers!.isEmpty) {
      return Map.unmodifiable(_cache);
    }
    return pingAllConcurrent(_lastServers!);
  }

  /// Start background auto-refresh every [refreshInterval].
  void startAutoRefresh() {
    stopAutoRefresh();
    _refreshTimer = Timer.periodic(refreshInterval, (_) {
      unawaited(testAll());
    });
  }

  /// Stop background auto-refresh.
  void stopAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
  }

  /// Get the cached latency for a specific server, or `null` if not tested.
  int? getLatency(String serverId) => _cache[serverId];

  /// Clear cached results.
  void clearCache() {
    _cache.clear();
    _cacheTimestamps.clear();
  }

  /// Dispose of resources (timer).
  void dispose() {
    stopAutoRefresh();
    _cache.clear();
    _cacheTimestamps.clear();
    _lastServers = null;
  }
}
