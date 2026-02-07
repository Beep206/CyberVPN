import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_status_ws.dart';

// ---------------------------------------------------------------------------
// Server Status Data Source Provider
// ---------------------------------------------------------------------------

/// Provides a singleton [ServerStatusWebSocketDataSource] backed by the
/// shared [WebSocketClient].
///
/// The data source starts listening to WebSocket server status events
/// immediately upon creation and caches the latest status per server.
///
/// Override in tests with a mock to inject controlled status updates.
final serverStatusWsDataSourceProvider =
    Provider<ServerStatusWebSocketDataSource>((ref) {
  final wsClient = ref.watch(webSocketClientProvider);

  final dataSource = ServerStatusWebSocketDataSourceImpl(
    wsClient: wsClient,
  );

  ref.onDispose(() {
    AppLogger.info('Disposing ServerStatusWebSocketDataSource');
    dataSource.dispose();
  });

  return dataSource;
});

// ---------------------------------------------------------------------------
// Server Status Stream Provider
// ---------------------------------------------------------------------------

/// Provides a stream of [ServerStatusUpdate] events from the WebSocket.
///
/// UI components can watch this provider to react to real-time server
/// status changes. Each emission represents a single server changing state.
///
/// Example usage in a widget:
/// ```dart
/// final statusAsync = ref.watch(serverStatusStreamProvider);
/// statusAsync.when(
///   data: (update) => Text('${update.serverId}: ${update.status}'),
///   loading: () => const CircularProgressIndicator(),
///   error: (e, st) => Text('Error: $e'),
/// );
/// ```
final serverStatusStreamProvider =
    StreamProvider<ServerStatusUpdate>((ref) {
  final dataSource = ref.watch(serverStatusWsDataSourceProvider);
  return dataSource.statusUpdates;
});

// ---------------------------------------------------------------------------
// Server Status Map Provider
// ---------------------------------------------------------------------------

/// Provides a reactive map of server ID to the latest [ServerStatusUpdate].
///
/// This provider rebuilds whenever a new [ServerStatusUpdate] arrives,
/// giving downstream providers and widgets access to the complete
/// snapshot of known server statuses.
///
/// The map is a read-only view of the data source's internal cache.
///
/// Example usage:
/// ```dart
/// final statusMap = ref.watch(serverStatusMapProvider);
/// final isOnline = statusMap['server-123']?.isAvailable ?? true;
/// ```
final serverStatusMapProvider =
    Provider<Map<String, ServerStatusUpdate>>((ref) {
  // Watching the stream provider ensures we rebuild whenever a new event
  // arrives, keeping the map in sync.
  ref.watch(serverStatusStreamProvider);

  final dataSource = ref.watch(serverStatusWsDataSourceProvider);
  return dataSource.latestStatuses;
});

// ---------------------------------------------------------------------------
// Per-Server Status Provider
// ---------------------------------------------------------------------------

/// Provides the latest [ServerStatusUpdate] for a specific server.
///
/// Returns `null` if no WebSocket update has been received for the
/// given [serverId] yet. In that case, the server list's initial
/// `isAvailable` field from the REST API should be used as the source
/// of truth.
///
/// Example usage:
/// ```dart
/// final status = ref.watch(serverStatusByIdProvider('server-123'));
/// final isOnline = status?.isAvailable ?? server.isAvailable;
/// ```
final serverStatusByIdProvider =
    Provider.family<ServerStatusUpdate?, String>((ref, serverId) {
  final statusMap = ref.watch(serverStatusMapProvider);
  return statusMap[serverId];
});

// ---------------------------------------------------------------------------
// WebSocket Connection State Provider (re-exported convenience)
// ---------------------------------------------------------------------------

/// Provides the current [WebSocketConnectionState] as a synchronous value.
///
/// Useful for UI elements that need to display a connectivity indicator
/// (e.g. a colored dot showing whether real-time updates are active).
///
/// Falls back to [WebSocketConnectionState.disconnected] if the stream
/// has not emitted yet.
final wsConnectionStatusProvider = Provider<WebSocketConnectionState>((ref) {
  final asyncState = ref.watch(webSocketConnectionStateProvider);
  return asyncState.value ?? WebSocketConnectionState.disconnected;
});

// ---------------------------------------------------------------------------
// Aggregate Stats Providers
// ---------------------------------------------------------------------------

/// The total number of servers currently reported as online via WebSocket.
///
/// Returns 0 if no status updates have been received yet.
final onlineServerCountProvider = Provider<int>((ref) {
  final statusMap = ref.watch(serverStatusMapProvider);
  return statusMap.values.where((s) => s.isAvailable).length;
});
