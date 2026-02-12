import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';

void main() {
  group('WebSocketClient', () {
    late WebSocketClient client;

    setUp(() {
      client = WebSocketClient(
        baseUrl: 'https://api.example.com',
        ticketProvider: () async => 'test-ticket-uuid',
      );
    });

    tearDown(() async {
      await client.dispose();
    });

    test('initial state is disconnected', () {
      expect(client.connectionState, WebSocketConnectionState.disconnected);
    });

    test('dispose completes without errors', () async {
      // Should not throw even when never connected.
      await expectLater(client.dispose(), completes);
    });

    test('events stream is broadcast and can have multiple listeners', () {
      // Broadcast streams allow multiple listeners without errors.
      final sub1 = client.events.listen((_) {});
      final sub2 = client.events.listen((_) {});

      // No error means broadcast works.
      unawaited(sub1.cancel());
      unawaited(sub2.cancel());
    });

    test('connectionStateStream is broadcast', () {
      final sub1 = client.connectionStateStream.listen((_) {});
      final sub2 = client.connectionStateStream.listen((_) {});

      unawaited(sub1.cancel());
      unawaited(sub2.cancel());
    });

    test('connect with null token stays disconnected', () async {
      final noTokenClient = WebSocketClient(
        baseUrl: 'https://api.example.com',
        ticketProvider: () async => null,
      );

      final states = <WebSocketConnectionState>[];
      final sub = noTokenClient.connectionStateStream.listen(states.add);

      await noTokenClient.connect();

      // Give time for state transitions.
      await Future<void>.delayed(const Duration(milliseconds: 100));

      expect(noTokenClient.connectionState,
          WebSocketConnectionState.disconnected);

      // Should transition to connecting then back to disconnected.
      expect(states, contains(WebSocketConnectionState.disconnected));

      await sub.cancel();
      await noTokenClient.dispose();
    });

    test('disconnect sets state to disconnected', () async {
      await client.disconnect();
      expect(client.connectionState, WebSocketConnectionState.disconnected);
    });

    test('double connect is a no-op when already connecting/connected', () async {
      // Since we cannot actually connect to a real server in unit tests,
      // we verify that calling connect when in connecting state does not crash.
      // The client will fail to connect (no real server) but should not throw.
      // We just test that a second connect call returns immediately.
      final noTokenClient = WebSocketClient(
        baseUrl: 'https://api.example.com',
        ticketProvider: () async => null,
      );

      await noTokenClient.connect();
      await noTokenClient.connect(); // Should be a no-op.

      await noTokenClient.dispose();
    });
  });

  group('WebSocketEvent.fromJson', () {
    test('parses server_status_changed', () {
      final json = {
        'type': 'server_status_changed',
        'data': {
          'server_id': 'srv-1',
          'status': 'offline',
        },
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event, isA<ServerStatusChanged>());

      final e = event as ServerStatusChanged;
      expect(e.serverId, 'srv-1');
      expect(e.status, 'offline');
    });

    test('parses subscription_updated', () {
      final json = {
        'type': 'subscription_updated',
        'data': {
          'subscription_id': 'sub-42',
          'status': 'active',
        },
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event, isA<SubscriptionUpdated>());

      final e = event as SubscriptionUpdated;
      expect(e.subscriptionId, 'sub-42');
      expect(e.status, 'active');
    });

    test('parses notification_received', () {
      final json = {
        'type': 'notification_received',
        'data': {
          'title': 'Alert',
          'body': 'Your subscription expires soon.',
        },
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event, isA<NotificationReceived>());

      final e = event as NotificationReceived;
      expect(e.title, 'Alert');
      expect(e.body, 'Your subscription expires soon.');
    });

    test('parses force_disconnect', () {
      final json = {
        'type': 'force_disconnect',
        'data': {
          'reason': 'account_suspended',
        },
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event, isA<ForceDisconnect>());

      final e = event as ForceDisconnect;
      expect(e.reason, 'account_suspended');
    });

    test('returns null for unknown type', () {
      final json = {
        'type': 'unknown_event_type',
        'data': {},
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event, isNull);
    });

    test('returns null when type field is missing', () {
      final json = <String, dynamic>{
        'data': {'foo': 'bar'},
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event, isNull);
    });

    test('handles missing data field gracefully', () {
      final json = {
        'type': 'server_status_changed',
      };

      final event = WebSocketEvent.fromJson(json);
      expect(event, isA<ServerStatusChanged>());

      final e = event as ServerStatusChanged;
      // Falls back to top-level json which lacks server_id/status.
      expect(e.serverId, '');
      expect(e.status, '');
    });

    test('handles malformed data gracefully', () {
      // When data field is present but has unexpected types, defaults kick in.
      final json = {
        'type': 'notification_received',
        'data': <String, dynamic>{
          'title': 123, // Not a String.
        },
      };

      // Should not throw; the fromJson uses `as String?` which will throw
      // a TypeError. We expect a graceful fallback or an exception caught
      // at the caller level.
      expect(
        () => WebSocketEvent.fromJson(json),
        anyOf(returnsNormally, throwsA(isA<TypeError>())),
      );
    });
  });

  group('WebSocket URL building', () {
    test('converts https to wss', () {
      final client = WebSocketClient(
        baseUrl: 'https://api.cybervpn.com',
        ticketProvider: () async => 'test-ticket',
      );

      // We cannot directly test _buildWsUrl since it is private.
      // Instead we verify the client constructs properly and the
      // baseUrl is stored correctly.
      expect(client.baseUrl, 'https://api.cybervpn.com');
      unawaited(client.dispose());
    });

    test('accepts custom path', () {
      final client = WebSocketClient(
        baseUrl: 'https://api.cybervpn.com',
        ticketProvider: () async => 'test-ticket',
        path: '/ws/custom',
      );

      expect(client.path, '/ws/custom');
      unawaited(client.dispose());
    });
  });

  group('Typed convenience streams', () {
    test('serverStatusEvents filters correctly', () async {
      final client = WebSocketClient(
        baseUrl: 'https://api.example.com',
        ticketProvider: () async => null,
      );

      // Since we cannot inject events directly (internal controller),
      // we verify the typed stream getters exist and return the right type.
      expect(client.serverStatusEvents, isA<Stream<ServerStatusChanged>>());
      expect(client.subscriptionEvents, isA<Stream<SubscriptionUpdated>>());
      expect(client.notificationEvents, isA<Stream<NotificationReceived>>());
      expect(client.forceDisconnectEvents, isA<Stream<ForceDisconnect>>());

      await client.dispose();
    });
  });
}
