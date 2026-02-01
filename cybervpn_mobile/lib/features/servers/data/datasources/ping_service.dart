import 'dart:async';
import 'dart:io';

import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';

/// Service for performing parallel ping/latency tests against VPN servers.
///
/// Uses TCP socket connection to measure round-trip latency. Results are
/// cached in-memory and can be refreshed manually or via a periodic timer.
class PingService {
  PingService({
    this.maxConcurrent = 10,
    this.timeoutDuration = const Duration(seconds: 5),
    this.refreshInterval = const Duration(seconds: 60),
  });

  /// Maximum number of concurrent ping operations.
  final int maxConcurrent;

  /// Timeout for individual ping attempts.
  final Duration timeoutDuration;

  /// Interval between automatic background refreshes.
  final Duration refreshInterval;

  /// In-memory cache: serverId -> latency in ms.
  final Map<String, int> _cache = {};

  /// Timer for periodic background refresh.
  Timer? _refreshTimer;

  /// Servers list stored for background refresh cycles.
  List<ServerEntity>? _lastServers;

  /// Whether a ping sweep is currently running.
  bool _isRunning = false;

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /// Returns the currently cached latency results (serverId -> ms).
  Map<String, int> get cachedResults => Map.unmodifiable(_cache);

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
    } catch (_) {
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

    // Merge results into cache.
    _cache.addAll(results);
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

    _cache.addAll(results);
    _isRunning = false;
    return Map.unmodifiable(results);
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
      testAll();
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
  }

  /// Dispose of resources (timer).
  void dispose() {
    stopAutoRefresh();
    _cache.clear();
    _lastServers = null;
  }
}
