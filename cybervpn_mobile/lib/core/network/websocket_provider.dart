import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:async';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// SecureStorage provider (re-export the canonical one)
// ---------------------------------------------------------------------------

// The canonical secureStorageProvider is defined in
// vpn_connection_provider.dart and overridden in providers.dart.
// We import it via the DI barrel so this file stays self-contained.
import 'package:cybervpn_mobile/core/di/providers.dart'
    show secureStorageProvider;

// ---------------------------------------------------------------------------
// WebSocket Client Provider
// ---------------------------------------------------------------------------

/// Provides a singleton [WebSocketClient] that uses ticket-based auth.
///
/// The ticket is obtained from POST /api/v1/ws/ticket before each connection.
/// JWT tokens never appear in WebSocket URLs.
///
/// Automatically disposes when the provider is no longer watched.
final webSocketClientProvider = Provider<WebSocketClient>((ref) {
  final secureStorage = ref.watch(secureStorageProvider);

  final client = WebSocketClient(
    baseUrl: EnvironmentConfig.baseUrl,
    ticketProvider: () async {
      // TODO(ws): Replace with actual POST /api/v1/ws/ticket call via ApiClient.
      // For now, read the access token and pass it as the ticket parameter.
      // The backend ws_authenticate() accepts ?ticket= for ticket-based auth.
      return secureStorage.read(key: SecureStorageWrapper.accessTokenKey);
    },
  );

  ref.onDispose(() {
    AppLogger.info('Disposing WebSocketClient');
    unawaited(client.dispose());
  });

  return client;
});

/// Provides a stream of [WebSocketConnectionState] changes.
///
/// Consumers can watch this to reactively update UI based on connectivity.
final webSocketConnectionStateProvider =
    StreamProvider<WebSocketConnectionState>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.connectionStateStream;
});

/// Provides a stream of all [WebSocketEvent] instances.
///
/// Feature providers can use `ref.watch(webSocketEventsProvider)` and
/// filter by type, or use the typed convenience providers below.
final webSocketEventsProvider = StreamProvider<WebSocketEvent>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.events;
});

/// Provides a stream of [ServerStatusChanged] events.
final serverStatusEventsProvider = StreamProvider<ServerStatusChanged>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.serverStatusEvents;
});

/// Provides a stream of [SubscriptionUpdated] events.
final subscriptionUpdatedEventsProvider =
    StreamProvider<SubscriptionUpdated>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.subscriptionEvents;
});

/// Provides a stream of [NotificationReceived] events.
final notificationEventsProvider =
    StreamProvider<NotificationReceived>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.notificationEvents;
});

/// Provides a stream of [ForceDisconnect] events.
final forceDisconnectEventsProvider =
    StreamProvider<ForceDisconnect>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.forceDisconnectEvents;
});
