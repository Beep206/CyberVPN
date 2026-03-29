import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:async';
import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/security/certificate_pinner.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// SecureStorage provider (re-export the canonical one)
// ---------------------------------------------------------------------------

// The canonical secureStorageProvider is defined in
// vpn_connection_provider.dart and overridden in providers.dart.
// We import it via the DI barrel so this file stays self-contained.
import 'package:cybervpn_mobile/core/di/providers.dart'
    show apiClientProvider, secureStorageProvider;

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
  final apiClient = ref.watch(apiClientProvider);
  final secureStorage = ref.watch(secureStorageProvider);

  // Apply same SHA-256 cert pinning to WebSocket TLS as HTTP (Dio).
  final fingerprints = EnvironmentConfig.certificateFingerprints;
  final pinnedHttpClient = fingerprints.isNotEmpty
      ? CertificatePinner(pinnedFingerprints: fingerprints).createHttpClient()
      : null;

  final client = WebSocketClient(
    baseUrl: EnvironmentConfig.baseUrl,
    ticketProvider: () => _requestWsTicket(apiClient, secureStorage),
    httpClient: pinnedHttpClient,
  );

  ref.onDispose(() {
    AppLogger.info('Disposing WebSocketClient');
    unawaited(client.dispose());
  });

  return client;
});

/// Requests a single-use WebSocket ticket from the backend.
///
/// Calls POST /api/v1/ws/ticket with the user's JWT. Returns `null` when the
/// user is effectively signed out or the backend rejects the current session.
/// Transient failures are rethrown so the caller can apply reconnect backoff.
@visibleForTesting
Future<String?> requestWebSocketTicket(
  ApiClient apiClient,
  SecureStorageWrapper secureStorage,
) async {
  final accessToken = await secureStorage.getAccessToken();
  if (accessToken == null || accessToken.isEmpty) {
    AppLogger.info(
      'Skipping WebSocket ticket request because no access token is available',
      category: 'websocket',
    );
    return null;
  }

  try {
    final response = await apiClient.post<Map<String, dynamic>>(
      ApiConstants.wsTicket,
    );
    final data = response.data;
    if (data != null && data['ticket'] is String) {
      return data['ticket'] as String;
    }

    throw StateError('WebSocket ticket response did not include a ticket');
  } on AuthException catch (e, st) {
    AppLogger.warning(
      'WebSocket ticket request rejected by auth state',
      error: e,
      stackTrace: st,
      category: 'websocket',
    );
    return null;
  }
}

Future<String?> _requestWsTicket(
  ApiClient apiClient,
  SecureStorageWrapper secureStorage,
) {
  return requestWebSocketTicket(apiClient, secureStorage);
}

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
final subscriptionUpdatedEventsProvider = StreamProvider<SubscriptionUpdated>((
  ref,
) {
  final client = ref.watch(webSocketClientProvider);
  return client.subscriptionEvents;
});

/// Provides a stream of [NotificationReceived] events.
final notificationEventsProvider = StreamProvider<NotificationReceived>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.notificationEvents;
});

/// Provides a stream of [ForceDisconnect] events.
final forceDisconnectEventsProvider = StreamProvider<ForceDisconnect>((ref) {
  final client = ref.watch(webSocketClientProvider);
  return client.forceDisconnectEvents;
});
