import 'dart:async';

import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/kill_switch_service.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/auto_reconnect.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/connect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/domain/usecases/disconnect_vpn.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock VpnRepository
// ---------------------------------------------------------------------------

class MockVpnRepository implements VpnRepository {
  final StreamController<ConnectionStateEntity> _stateController =
      StreamController<ConnectionStateEntity>.broadcast();

  bool _isConnected = false;
  VpnConfigEntity? _lastConfig;

  @override
  Stream<ConnectionStateEntity> get connectionStateStream =>
      _stateController.stream;

  @override
  Future<Result<bool>> get isConnected async => Success(_isConnected);

  @override
  Future<Result<VpnConfigEntity?>> getLastConfig() async => Success(_lastConfig);

  @override
  Future<Result<void>> connect(VpnConfigEntity config) async {
    _isConnected = true;
    _lastConfig = config;
    return const Success<void>(null);
  }

  @override
  Future<Result<void>> disconnect() async {
    _isConnected = false;
    _lastConfig = null;
    return const Success<void>(null);
  }

  void dispose() {
    _stateController.close();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock NetworkInfo
// ---------------------------------------------------------------------------

class MockNetworkInfo implements NetworkInfo {
  final StreamController<bool> _connectivityController =
      StreamController<bool>.broadcast();

  @override
  Stream<bool> get onConnectivityChanged => _connectivityController.stream;

  @override
  Future<bool> get isConnected async => true;

  void dispose() {
    _connectivityController.close();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock SecureStorage
// ---------------------------------------------------------------------------

class MockSecureStorage implements SecureStorageWrapper {
  final Map<String, String> _storage = {};

  @override
  Future<String?> read({required String key}) async => _storage[key];

  @override
  Future<void> write({required String key, required String value}) async {
    _storage[key] = value;
  }

  @override
  Future<void> delete({required String key}) async {
    _storage.remove(key);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock AutoReconnectService
// ---------------------------------------------------------------------------

class MockAutoReconnectService implements AutoReconnectService {
  bool isStarted = false;

  @override
  void start(VpnConfigEntity config) {
    isStarted = true;
  }

  @override
  void stop() {
    isStarted = false;
  }

  @override
  void dispose() {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock KillSwitchService
// ---------------------------------------------------------------------------

class MockKillSwitchService implements KillSwitchService {
  bool _isEnabled = false;

  @override
  Future<void> enable() async {
    _isEnabled = true;
  }

  @override
  Future<void> disable() async {
    _isEnabled = false;
  }

  @override
  Future<bool> isEnabled() async => _isEnabled;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock WebSocketClient
// ---------------------------------------------------------------------------

class MockWebSocketClient implements WebSocketClient {
  final StreamController<ForceDisconnect> _forceDisconnectController =
      StreamController<ForceDisconnect>.broadcast();

  @override
  Stream<ForceDisconnect> get forceDisconnectEvents =>
      _forceDisconnectController.stream;

  void emitForceDisconnect(ForceDisconnect event) {
    _forceDisconnectController.add(event);
  }

  @override
  Future<void> dispose() async {
    await _forceDisconnectController.close();
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
    isAvailable: true,
  );
}

/// Creates a [ProviderContainer] with all mocks wired up.
ProviderContainer createContainer({
  required MockVpnRepository repo,
  required MockNetworkInfo networkInfo,
  required MockSecureStorage storage,
  required MockAutoReconnectService autoReconnect,
  required MockKillSwitchService killSwitch,
  required MockWebSocketClient wsClient,
}) {
  return ProviderContainer(
    overrides: [
      vpnRepositoryProvider.overrideWithValue(repo),
      networkInfoProvider.overrideWithValue(networkInfo),
      secureStorageProvider.overrideWithValue(storage),
      autoReconnectServiceProvider.overrideWithValue(autoReconnect),
      killSwitchServiceProvider.overrideWithValue(killSwitch),
      webSocketClientProvider.overrideWithValue(wsClient),
      connectVpnUseCaseProvider.overrideWithValue(ConnectVpnUseCase(repo)),
      disconnectVpnUseCaseProvider.overrideWithValue(DisconnectVpnUseCase(repo)),
      vpnSettingsProvider.overrideWith((ref) => const VpnSettings()),
    ],
  );
}

/// Waits for the [vpnConnectionProvider] to finish loading.
Future<VpnConnectionState> waitForState(ProviderContainer container) async {
  final sub = container.listen(vpnConnectionProvider, (_, _) {});
  await container.read(vpnConnectionProvider.future);
  sub.close();
  return container.read(vpnConnectionProvider).requireValue;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('VpnConnectionProvider - WebSocket Integration', () {
    late MockVpnRepository repo;
    late MockNetworkInfo networkInfo;
    late MockSecureStorage storage;
    late MockAutoReconnectService autoReconnect;
    late MockKillSwitchService killSwitch;
    late MockWebSocketClient wsClient;
    late ProviderContainer container;

    setUp(() {
      repo = MockVpnRepository();
      networkInfo = MockNetworkInfo();
      storage = MockSecureStorage();
      autoReconnect = MockAutoReconnectService();
      killSwitch = MockKillSwitchService();
      wsClient = MockWebSocketClient();
    });

    tearDown(() {
      container.dispose();
      repo.dispose();
      networkInfo.dispose();
    });

    test('force_disconnect event disconnects VPN immediately', () async {
      container = createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
      );

      var state = await waitForState(container);
      expect(state.isDisconnected, isTrue);

      // Connect to a server.
      final server = _makeServer(id: 'server-1');
      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(server);

      state = container.read(vpnConnectionProvider).requireValue;
      expect(state.isConnected, isTrue);

      // Emit force_disconnect event.
      wsClient.emitForceDisconnect(
        const ForceDisconnect(reason: 'Account suspended'),
      );

      // Give the stream a tick to process.
      await Future<void>.delayed(Duration.zero);

      // Verify VPN is disconnected.
      state = container.read(vpnConnectionProvider).requireValue;
      expect(state.isDisconnected || state.isError, isTrue);

      // If error state, verify the reason is included.
      if (state is VpnError) {
        expect(state.message, contains('Account suspended'));
      }
    });

    test('force_disconnect event with empty reason still disconnects', () async {
      container = createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
      );

      await waitForState(container);

      // Connect to a server.
      final server = _makeServer(id: 'server-1');
      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(server);

      // Emit force_disconnect event with empty reason.
      wsClient.emitForceDisconnect(
        const ForceDisconnect(reason: ''),
      );

      await Future<void>.delayed(Duration.zero);

      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state.isDisconnected || state.isError, isTrue);
    });

    test('force_disconnect event when already disconnected is handled gracefully', () async {
      container = createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
      );

      var state = await waitForState(container);
      expect(state.isDisconnected, isTrue);

      // Emit force_disconnect event while already disconnected.
      wsClient.emitForceDisconnect(
        const ForceDisconnect(reason: 'Already disconnected'),
      );

      await Future<void>.delayed(Duration.zero);

      // Verify state remains stable (no crash).
      state = container.read(vpnConnectionProvider).requireValue;
      expect(state.isDisconnected || state.isError, isTrue);
    });
  });
}
