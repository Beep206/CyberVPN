import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as ws_status;

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Connection State
// ---------------------------------------------------------------------------

/// Represents the current state of the WebSocket connection.
enum WebSocketConnectionState {
  /// Not connected and not attempting to connect.
  disconnected,

  /// Actively establishing a connection.
  connecting,

  /// Connection is open and ready for messages.
  connected,

  /// Lost connection and attempting to re-establish.
  reconnecting,
}

// ---------------------------------------------------------------------------
// WebSocket Events
// ---------------------------------------------------------------------------

/// Base class for all typed WebSocket events.
sealed class WebSocketEvent {
  const WebSocketEvent();

  /// Parse a raw JSON map into a typed [WebSocketEvent].
  ///
  /// Returns `null` if the `type` field is unrecognized.
  static WebSocketEvent? fromJson(Map<String, dynamic> json) {
    final type = json['type'] as String?;
    if (type == null) return null;

    try {
      return switch (type) {
        'server_status_changed' => ServerStatusChanged.fromJson(json),
        'subscription_updated' => SubscriptionUpdated.fromJson(json),
        'notification_received' => NotificationReceived.fromJson(json),
        'force_disconnect' => ForceDisconnect.fromJson(json),
        _ => null,
      };
    } catch (e, st) {
      AppLogger.warning(
        'Failed to parse WebSocket event of type "$type"',
        error: e,
        stackTrace: st,
        category: 'websocket',
      );
      return null;
    }
  }
}

/// A server's status has changed (e.g. online -> offline).
class ServerStatusChanged extends WebSocketEvent {
  final String serverId;
  final String status;
  final Map<String, dynamic> data;

  const ServerStatusChanged({
    required this.serverId,
    required this.status,
    this.data = const {},
  });

  factory ServerStatusChanged.fromJson(Map<String, dynamic> json) {
    final payload = json['data'] as Map<String, dynamic>? ?? json;
    return ServerStatusChanged(
      serverId: payload['server_id'] as String? ?? '',
      status: payload['status'] as String? ?? '',
      data: payload,
    );
  }

  @override
  String toString() =>
      'ServerStatusChanged(serverId: $serverId, status: $status)';
}

/// The user's subscription has been updated.
class SubscriptionUpdated extends WebSocketEvent {
  final String subscriptionId;
  final String status;
  final Map<String, dynamic> data;

  const SubscriptionUpdated({
    required this.subscriptionId,
    required this.status,
    this.data = const {},
  });

  factory SubscriptionUpdated.fromJson(Map<String, dynamic> json) {
    final payload = json['data'] as Map<String, dynamic>? ?? json;
    return SubscriptionUpdated(
      subscriptionId: payload['subscription_id'] as String? ?? '',
      status: payload['status'] as String? ?? '',
      data: payload,
    );
  }

  @override
  String toString() =>
      'SubscriptionUpdated(subscriptionId: $subscriptionId, status: $status)';
}

/// A new notification has arrived.
class NotificationReceived extends WebSocketEvent {
  final String title;
  final String body;
  final Map<String, dynamic> data;

  const NotificationReceived({
    required this.title,
    required this.body,
    this.data = const {},
  });

  factory NotificationReceived.fromJson(Map<String, dynamic> json) {
    final payload = json['data'] as Map<String, dynamic>? ?? json;
    return NotificationReceived(
      title: payload['title'] as String? ?? '',
      body: payload['body'] as String? ?? '',
      data: payload,
    );
  }

  @override
  String toString() => 'NotificationReceived(title: $title)';
}

/// The server is forcing this client to disconnect (e.g. account suspended).
class ForceDisconnect extends WebSocketEvent {
  final String reason;

  const ForceDisconnect({this.reason = ''});

  factory ForceDisconnect.fromJson(Map<String, dynamic> json) {
    final payload = json['data'] as Map<String, dynamic>? ?? json;
    return ForceDisconnect(
      reason: payload['reason'] as String? ?? '',
    );
  }

  @override
  String toString() => 'ForceDisconnect(reason: $reason)';
}

// ---------------------------------------------------------------------------
// WebSocket Client
// ---------------------------------------------------------------------------

/// A WebSocket client that connects to the CyberVPN notification endpoint
/// with automatic reconnection using exponential backoff.
///
/// Uses ticket-based authentication: the client first requests a single-use
/// ticket via POST /api/v1/ws/ticket, then connects with `?ticket=<uuid>`.
/// JWT tokens never appear in WebSocket URLs.
///
/// Usage:
/// ```dart
/// final client = WebSocketClient(
///   baseUrl: 'https://api.cybervpn.com',
///   ticketProvider: () async => apiClient.requestWsTicket(),
/// );
///
/// client.events.listen((event) {
///   switch (event) {
///     case ServerStatusChanged e: // handle
///     case SubscriptionUpdated e: // handle
///     case NotificationReceived e: // handle
///     case ForceDisconnect e: // handle
///   }
/// });
///
/// await client.connect();
/// ```
class WebSocketClient {
  /// The HTTP(S) base URL of the API server.
  final String baseUrl;

  /// Async callback that provides a single-use WebSocket ticket.
  ///
  /// The ticket is obtained from POST /api/v1/ws/ticket and is valid for
  /// 30 seconds. Returning `null` means authentication is unavailable.
  ///
  /// For backwards compatibility, [tokenProvider] is accepted as an alias
  /// but the value is used as a ticket parameter in the URL.
  final Future<String?> Function() ticketProvider;

  /// The WebSocket endpoint path (appended to [baseUrl]).
  final String path;

  // ── Reconnection parameters ──────────────────────────────────────────

  /// Initial reconnection delay.
  static const Duration _initialBackoff = Duration(seconds: 1);

  /// Maximum reconnection delay.
  static const Duration _maxBackoff = Duration(seconds: 30);

  /// Backoff multiplier per attempt.
  static const int _backoffMultiplier = 2;

  // ── Internal state ───────────────────────────────────────────────────

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _channelSubscription;
  Timer? _reconnectTimer;
  int _reconnectAttempt = 0;
  bool _intentionalClose = false;

  /// Optional [HttpClient] for certificate pinning on WebSocket TLS.
  final HttpClient? _httpClient;

  final StreamController<WebSocketEvent> _eventController =
      StreamController<WebSocketEvent>.broadcast();

  final StreamController<WebSocketConnectionState> _stateController =
      StreamController<WebSocketConnectionState>.broadcast();

  WebSocketConnectionState _connectionState =
      WebSocketConnectionState.disconnected;

  // ── Constructor ──────────────────────────────────────────────────────

  /// Completer used to deduplicate concurrent connect() calls.
  /// When non-null, a connection attempt is already in progress.
  Completer<void>? _connectCompleter;

  WebSocketClient({
    required this.baseUrl,
    required this.ticketProvider,
    this.path = '/ws/notifications',
    HttpClient? httpClient,
  }) : _httpClient = httpClient;

  // ── Public API ───────────────────────────────────────────────────────

  /// Stream of typed WebSocket events.
  Stream<WebSocketEvent> get events => _eventController.stream;

  /// Convenience stream that emits only [ServerStatusChanged] events.
  Stream<ServerStatusChanged> get serverStatusEvents =>
      events.where((e) => e is ServerStatusChanged).cast<ServerStatusChanged>();

  /// Convenience stream that emits only [SubscriptionUpdated] events.
  Stream<SubscriptionUpdated> get subscriptionEvents =>
      events.where((e) => e is SubscriptionUpdated).cast<SubscriptionUpdated>();

  /// Convenience stream that emits only [NotificationReceived] events.
  Stream<NotificationReceived> get notificationEvents =>
      events
          .where((e) => e is NotificationReceived)
          .cast<NotificationReceived>();

  /// Convenience stream that emits only [ForceDisconnect] events.
  Stream<ForceDisconnect> get forceDisconnectEvents =>
      events.where((e) => e is ForceDisconnect).cast<ForceDisconnect>();

  /// Stream of connection state changes.
  Stream<WebSocketConnectionState> get connectionStateStream =>
      _stateController.stream;

  /// The current connection state.
  WebSocketConnectionState get connectionState => _connectionState;

  /// Connect to the WebSocket server.
  ///
  /// If already connected or a connection attempt is in progress, returns
  /// the existing future to prevent duplicate connections.
  Future<void> connect() async {
    if (_connectionState == WebSocketConnectionState.connected) {
      return;
    }

    // If a connect() call is already in flight, await it instead of
    // starting a second connection.
    if (_connectCompleter != null) {
      return _connectCompleter!.future;
    }

    _connectCompleter = Completer<void>();
    _intentionalClose = false;

    try {
      await _doConnect();
      _connectCompleter?.complete();
    } catch (e) {
      _connectCompleter?.completeError(e);
    } finally {
      _connectCompleter = null;
    }
  }

  /// Gracefully disconnect and stop any reconnection attempts.
  Future<void> disconnect() async {
    _intentionalClose = true;
    _cancelReconnect();
    await _closeChannel();
    _setConnectionState(WebSocketConnectionState.disconnected);
    AppLogger.info('WebSocket disconnected intentionally');
  }

  /// Release all resources. Call on logout or widget disposal.
  Future<void> dispose() async {
    await disconnect();
    await _eventController.close();
    await _stateController.close();
  }

  // ── Connection Logic ─────────────────────────────────────────────────

  Future<void> _doConnect() async {
    _setConnectionState(
      _reconnectAttempt > 0
          ? WebSocketConnectionState.reconnecting
          : WebSocketConnectionState.connecting,
    );

    final ticket = await ticketProvider();
    if (ticket == null || ticket.isEmpty) {
      AppLogger.warning('WebSocket: no auth ticket available, aborting connect');
      _setConnectionState(WebSocketConnectionState.disconnected);
      return;
    }

    final wsUrl = _buildWsUrl(ticket);
    AppLogger.debug('WebSocket connecting to: $wsUrl');

    try {
      if (_httpClient != null) {
        _channel = IOWebSocketChannel.connect(
          wsUrl,
          customClient: _httpClient,
        );
      } else {
        _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      }
      await _channel!.ready;

      _reconnectAttempt = 0;
      _setConnectionState(WebSocketConnectionState.connected);
      AppLogger.info('WebSocket connected');

      _channelSubscription = _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
        cancelOnError: false,
      );
    } catch (e, st) {
      AppLogger.error('WebSocket connection failed', error: e, stackTrace: st);
      _scheduleReconnect();
    }
  }

  /// Converts the HTTP(S) base URL to a WS(S) URL and appends the ticket.
  String _buildWsUrl(String ticket) {
    var url = baseUrl;

    // Convert http(s) scheme to ws(s).
    if (url.startsWith('https://')) {
      url = 'wss://${url.substring(8)}';
    } else if (url.startsWith('http://')) {
      url = 'ws://${url.substring(7)}';
    }

    // Remove trailing slash.
    if (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }

    return '$url$path?ticket=${Uri.encodeComponent(ticket)}';
  }

  // ── Message Handling ─────────────────────────────────────────────────

  void _onMessage(dynamic raw) {
    if (_eventController.isClosed) return;

    try {
      final Map<String, dynamic> json;
      if (raw is String) {
        json = jsonDecode(raw) as Map<String, dynamic>;
      } else {
        AppLogger.warning('WebSocket: received non-string message, ignoring');
        return;
      }

      final event = WebSocketEvent.fromJson(json);
      if (event == null) {
        AppLogger.debug(
            'WebSocket: unknown message type "${json['type']}", ignoring');
        return;
      }

      // Handle force-disconnect specially: emit event then close.
      if (event is ForceDisconnect) {
        _eventController.add(event);
        AppLogger.warning(
            'WebSocket: force disconnect received: ${event.reason}');
        _intentionalClose = true; // Do not reconnect after force disconnect.
        unawaited(_closeChannel());
        _setConnectionState(WebSocketConnectionState.disconnected);
        return;
      }

      _eventController.add(event);
    } catch (e, st) {
      AppLogger.error(
        'WebSocket: failed to parse message',
        error: e,
        stackTrace: st,
      );
    }
  }

  void _onError(Object error, StackTrace stackTrace) {
    AppLogger.error(
      'WebSocket stream error',
      error: error,
      stackTrace: stackTrace,
    );
  }

  void _onDone() {
    AppLogger.info('WebSocket stream closed');
    if (!_intentionalClose) {
      _scheduleReconnect();
    }
  }

  // ── Reconnection ────────────────────────────────────────────────────

  void _scheduleReconnect() {
    if (_intentionalClose) return;

    _cancelReconnect();

    final delay = _calculateBackoff();
    _setConnectionState(WebSocketConnectionState.reconnecting);

    AppLogger.info(
      'WebSocket: scheduling reconnect attempt ${_reconnectAttempt + 1} '
      'in ${delay.inMilliseconds}ms',
    );

    _reconnectTimer = Timer(delay, () {
      _reconnectAttempt++;
      unawaited(_doConnect());
    });
  }

  static final _random = math.Random();

  Duration _calculateBackoff() {
    final seconds = _initialBackoff.inSeconds *
        math.pow(_backoffMultiplier, _reconnectAttempt).toInt();
    final capped = math.min(seconds, _maxBackoff.inSeconds);
    // Add 0-50% jitter to prevent thundering herd on mass reconnect.
    final jitter = (capped * _random.nextDouble() * 0.5).toInt();
    return Duration(seconds: capped + jitter);
  }

  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  // ── Cleanup helpers ──────────────────────────────────────────────────

  Future<void> _closeChannel() async {
    await _channelSubscription?.cancel();
    _channelSubscription = null;

    try {
      await _channel?.sink.close(ws_status.goingAway);
    } catch (e) {
      // Closing an already-closed channel can throw; ignore.
    }
    _channel = null;
  }

  void _setConnectionState(WebSocketConnectionState newState) {
    if (_connectionState == newState) return;
    _connectionState = newState;
    if (!_stateController.isClosed) {
      _stateController.add(newState);
    }
  }
}
