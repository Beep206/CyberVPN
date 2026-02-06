import 'dart:async';

import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/ping_service.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

// ---------------------------------------------------------------------------
// Mock ServerRepository
// ---------------------------------------------------------------------------

class MockServerRepository implements ServerRepository {
  List<ServerEntity> _servers = [];

  void seed(List<ServerEntity> servers) {
    _servers = List.from(servers);
  }

  @override
  Future<Result<List<ServerEntity>>> getServers() async {
    return Success(List.from(_servers));
  }

  @override
  Future<Result<void>> toggleFavorite(String serverId) async {
    return const Success<void>(null);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock PingService
// ---------------------------------------------------------------------------

class MockPingService implements PingService {
  @override
  Future<Map<String, int>> pingAllConcurrent(List<ServerEntity> servers) async {
    return {};
  }

  @override
  void dispose() {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock WebSocketClient
// ---------------------------------------------------------------------------

class MockWebSocketClient implements WebSocketClient {
  final StreamController<ServerStatusChanged> _serverStatusController =
      StreamController<ServerStatusChanged>.broadcast();

  @override
  Stream<ServerStatusChanged> get serverStatusEvents =>
      _serverStatusController.stream;

  void emitServerStatusChanged(ServerStatusChanged event) {
    _serverStatusController.add(event);
  }

  @override
  Future<void> dispose() async {
    await _serverStatusController.close();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

ServerEntity _makeServer({
  required String id,
  String name = 'Test Server',
  bool isAvailable = true,
}) {
  return ServerEntity(
    id: id,
    name: name,
    countryCode: 'US',
    countryName: 'United States',
    city: 'New York',
    address: '1.2.3.4',
    port: 443,
    protocol: 'vless',
    isAvailable: isAvailable,
  );
}

/// Creates a [ProviderContainer] with all mocks wired up.
ProviderContainer createContainer({
  required MockServerRepository repo,
  required MockPingService pingService,
  required MockWebSocketClient wsClient,
  required SharedPreferences prefs,
}) {
  return ProviderContainer(
    overrides: [
      serverRepositoryProvider.overrideWithValue(repo),
      pingServiceProvider.overrideWithValue(pingService),
      webSocketClientProvider.overrideWithValue(wsClient),
      sharedPreferencesProvider.overrideWithValue(prefs),
    ],
  );
}

/// Waits for the [serverListProvider] to finish loading.
Future<ServerListState> waitForState(ProviderContainer container) async {
  final sub = container.listen(serverListProvider, (_, _) {});
  await container.read(serverListProvider.future);
  sub.close();
  return container.read(serverListProvider).requireValue;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('ServerListProvider - WebSocket Integration', () {
    late MockServerRepository repo;
    late MockPingService pingService;
    late MockWebSocketClient wsClient;
    late SharedPreferences prefs;
    late ProviderContainer container;

    setUp(() async {
      repo = MockServerRepository();
      pingService = MockPingService();
      wsClient = MockWebSocketClient();
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
    });

    tearDown(() {
      container.dispose();
    });

    test('server_status_changed event updates server status in list', () async {
      // Seed repository with servers.
      repo.seed([
        _makeServer(id: 'server-1', name: 'Server 1', isAvailable: true),
        _makeServer(id: 'server-2', name: 'Server 2', isAvailable: true),
      ]);

      container = createContainer(
        repo: repo,
        pingService: pingService,
        wsClient: wsClient,
        prefs: prefs,
      );

      // Wait for initial state to load.
      var state = await waitForState(container);
      expect(state.servers, hasLength(2));
      expect(state.servers[0].isAvailable, isTrue);
      expect(state.servers[1].isAvailable, isTrue);

      // Emit server_status_changed event for server-1 to 'offline'.
      wsClient.emitServerStatusChanged(
        const ServerStatusChanged(
          serverId: 'server-1',
          status: 'offline',
        ),
      );

      // Give the stream a tick to process.
      await Future<void>.delayed(Duration.zero);

      // Verify server-1 is now marked as unavailable.
      state = container.read(serverListProvider).requireValue;
      expect(state.servers, hasLength(2));
      expect(state.servers[0].id, 'server-1');
      expect(state.servers[0].isAvailable, isFalse);
      expect(state.servers[1].isAvailable, isTrue);
    });

    test('server_status_changed event with "online" status marks server available', () async {
      // Seed repository with an offline server.
      repo.seed([
        _makeServer(id: 'server-1', name: 'Server 1', isAvailable: false),
      ]);

      container = createContainer(
        repo: repo,
        pingService: pingService,
        wsClient: wsClient,
        prefs: prefs,
      );

      var state = await waitForState(container);
      expect(state.servers[0].isAvailable, isFalse);

      // Emit server_status_changed event for server-1 to 'online'.
      wsClient.emitServerStatusChanged(
        const ServerStatusChanged(
          serverId: 'server-1',
          status: 'online',
        ),
      );

      await Future<void>.delayed(Duration.zero);

      state = container.read(serverListProvider).requireValue;
      expect(state.servers[0].isAvailable, isTrue);
    });

    test('server_status_changed event for unknown server is ignored', () async {
      // Seed repository with one server.
      repo.seed([
        _makeServer(id: 'server-1', name: 'Server 1', isAvailable: true),
      ]);

      container = createContainer(
        repo: repo,
        pingService: pingService,
        wsClient: wsClient,
        prefs: prefs,
      );

      var state = await waitForState(container);
      expect(state.servers, hasLength(1));

      // Emit server_status_changed event for a non-existent server.
      wsClient.emitServerStatusChanged(
        const ServerStatusChanged(
          serverId: 'unknown-server',
          status: 'offline',
        ),
      );

      await Future<void>.delayed(Duration.zero);

      // Verify state is unchanged.
      state = container.read(serverListProvider).requireValue;
      expect(state.servers, hasLength(1));
      expect(state.servers[0].id, 'server-1');
      expect(state.servers[0].isAvailable, isTrue);
    });

    test('server_status_changed event with "maintenance" status marks server unavailable', () async {
      repo.seed([
        _makeServer(id: 'server-1', name: 'Server 1', isAvailable: true),
      ]);

      container = createContainer(
        repo: repo,
        pingService: pingService,
        wsClient: wsClient,
        prefs: prefs,
      );

      await waitForState(container);

      // Emit maintenance status.
      wsClient.emitServerStatusChanged(
        const ServerStatusChanged(
          serverId: 'server-1',
          status: 'maintenance',
        ),
      );

      await Future<void>.delayed(Duration.zero);

      final state = container.read(serverListProvider).requireValue;
      expect(state.servers[0].isAvailable, isFalse);
    });
  });
}
