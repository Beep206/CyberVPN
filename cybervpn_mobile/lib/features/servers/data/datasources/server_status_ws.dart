import 'dart:async';

import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Server Status Update Model
// ---------------------------------------------------------------------------

/// Represents a real-time server status update received via WebSocket.
///
/// Maps the raw [ServerStatusChanged] event to a domain-friendly structure
/// used by the server list and status providers.
class ServerStatusUpdate {
  /// The unique server identifier.
  final String serverId;

  /// The raw status string from the backend (e.g. 'online', 'offline',
  /// 'maintenance').
  final String status;

  /// Whether the server is available for connections.
  final bool isAvailable;

  /// Optional load percentage (0.0 - 100.0) if provided by the backend.
  final double? load;

  /// Optional current user count if provided by the backend.
  final int? currentUsers;

  /// UTC timestamp of when this update was received.
  final DateTime receivedAt;

  const ServerStatusUpdate({
    required this.serverId,
    required this.status,
    required this.isAvailable,
    this.load,
    this.currentUsers,
    required this.receivedAt,
  });

  /// Creates a [ServerStatusUpdate] from a raw [ServerStatusChanged] event.
  factory ServerStatusUpdate.fromEvent(ServerStatusChanged event) {
    final isAvailable = event.status == 'online';

    // Extract optional fields from the event data map.
    final load = event.data['load'] is num
        ? (event.data['load'] as num).toDouble()
        : null;
    final currentUsers = event.data['current_users'] is int
        ? event.data['current_users'] as int
        : null;

    return ServerStatusUpdate(
      serverId: event.serverId,
      status: event.status,
      isAvailable: isAvailable,
      load: load,
      currentUsers: currentUsers,
      receivedAt: DateTime.now().toUtc(),
    );
  }

  @override
  String toString() =>
      'ServerStatusUpdate(serverId: $serverId, status: $status, '
      'isAvailable: $isAvailable, load: $load)';
}

// ---------------------------------------------------------------------------
// Server Status WebSocket Data Source
// ---------------------------------------------------------------------------

/// Abstraction over the WebSocket connection for server status updates.
///
/// Decouples the server feature from the raw WebSocket implementation,
/// following Clean Architecture principles. The data layer uses this
/// interface; the infrastructure layer provides the concrete implementation
/// wired to [WebSocketClient].
abstract class ServerStatusWebSocketDataSource {
  /// Stream of real-time server status updates.
  Stream<ServerStatusUpdate> get statusUpdates;

  /// The most recent status for each server, keyed by server ID.
  ///
  /// This cache is useful for UI components that need the latest known
  /// status without waiting for the next WebSocket event.
  Map<String, ServerStatusUpdate> get latestStatuses;

  /// Returns the latest known status for a specific server, or `null`
  /// if no update has been received for that server.
  ServerStatusUpdate? getLatestStatus(String serverId);

  /// Initiates the WebSocket connection for receiving server status events.
  ///
  /// Calling this when already connected is a no-op.
  Future<void> connect();

  /// Gracefully disconnects from the WebSocket server.
  Future<void> disconnect();

  /// Releases all resources. Call on logout or app shutdown.
  void dispose();
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

/// Concrete implementation of [ServerStatusWebSocketDataSource] backed by
/// the shared [WebSocketClient].
///
/// Listens to [WebSocketClient.serverStatusEvents] and transforms them
/// into [ServerStatusUpdate] instances. Maintains an in-memory cache of
/// the latest status per server for synchronous lookups.
class ServerStatusWebSocketDataSourceImpl
    implements ServerStatusWebSocketDataSource {
  final WebSocketClient _wsClient;

  StreamSubscription<ServerStatusChanged>? _subscription;
  final StreamController<ServerStatusUpdate> _updateController =
      StreamController<ServerStatusUpdate>.broadcast();

  /// In-memory cache of the most recent status per server ID.
  final Map<String, ServerStatusUpdate> _statusCache = {};

  /// Maximum number of servers to cache. Prevents unbounded memory growth
  /// if the backend sends updates for a very large number of servers.
  static const int _maxCacheSize = 500;

  ServerStatusWebSocketDataSourceImpl({required WebSocketClient wsClient})
      : _wsClient = wsClient {
    _startListening();
  }

  @override
  Stream<ServerStatusUpdate> get statusUpdates => _updateController.stream;

  @override
  Map<String, ServerStatusUpdate> get latestStatuses =>
      Map.unmodifiable(_statusCache);

  @override
  ServerStatusUpdate? getLatestStatus(String serverId) =>
      _statusCache[serverId];

  @override
  Future<void> connect() async {
    await _wsClient.connect();
  }

  @override
  Future<void> disconnect() async {
    await _wsClient.disconnect();
  }

  @override
  void dispose() {
    unawaited(_subscription?.cancel());
    _subscription = null;
    unawaited(_updateController.close());
    _statusCache.clear();
  }

  // ---- Private ----

  void _startListening() {
    _subscription = _wsClient.serverStatusEvents.listen(
      _onServerStatusEvent,
      onError: (Object error, StackTrace stackTrace) {
        AppLogger.error(
          'ServerStatusWS: stream error',
          error: error,
          stackTrace: stackTrace,
        );
      },
    );
  }

  void _onServerStatusEvent(ServerStatusChanged event) {
    if (_updateController.isClosed) return;

    try {
      final update = ServerStatusUpdate.fromEvent(event);

      // Update the cache, evicting oldest entry if at capacity.
      if (_statusCache.length >= _maxCacheSize &&
          !_statusCache.containsKey(update.serverId)) {
        _statusCache.remove(_statusCache.keys.first);
      }
      _statusCache[update.serverId] = update;

      _updateController.add(update);

      AppLogger.debug(
        'ServerStatusWS: $update',
        category: 'server_status',
      );
    } catch (e, st) {
      AppLogger.error(
        'ServerStatusWS: failed to process event',
        error: e,
        stackTrace: st,
      );
    }
  }
}
