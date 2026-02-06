import 'dart:async';

import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/analytics/noop_analytics.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/services/device_registration_service.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/review/data/services/review_service.dart';
import 'package:cybervpn_mobile/features/review/presentation/providers/review_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
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
// Mocks
// ---------------------------------------------------------------------------

class _MockVpnRepository implements VpnRepository {
  final StreamController<ConnectionStateEntity> _stateController =
      StreamController<ConnectionStateEntity>.broadcast();

  bool _isConnected = false;
  VpnConfigEntity? _lastConfig;
  VpnConfigEntity? lastConnectConfig; // tracks what was passed to connect()

  @override
  Stream<ConnectionStateEntity> get connectionStateStream =>
      _stateController.stream;

  @override
  Future<Result<bool>> get isConnected async => Success(_isConnected);

  @override
  Future<Result<VpnConfigEntity?>> getLastConfig() async =>
      Success(_lastConfig);

  @override
  Future<Result<void>> connect(VpnConfigEntity config) async {
    _isConnected = true;
    _lastConfig = config;
    lastConnectConfig = config;
    return const Success<void>(null);
  }

  @override
  Future<Result<void>> disconnect() async {
    _isConnected = false;
    _lastConfig = null;
    return const Success<void>(null);
  }

  void dispose() => _stateController.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockNetworkInfo implements NetworkInfo {
  final StreamController<bool> _ctrl =
      StreamController<bool>.broadcast();

  @override
  Stream<bool> get onConnectivityChanged => _ctrl.stream;

  @override
  Future<bool> get isConnected async => true;

  void dispose() => _ctrl.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockSecureStorage implements SecureStorageWrapper {
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

class _MockAutoReconnect implements AutoReconnectService {
  bool isStarted = false;

  @override
  void start(VpnConfigEntity config) => isStarted = true;

  @override
  void stop() => isStarted = false;

  @override
  void dispose() {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockKillSwitch implements KillSwitchService {
  bool enabled = false;

  @override
  Future<void> enable() async => enabled = true;

  @override
  Future<void> disable() async => enabled = false;

  @override
  Future<bool> isEnabled() async => enabled;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockWebSocketClient implements WebSocketClient {
  final StreamController<ForceDisconnect> _ctrl =
      StreamController<ForceDisconnect>.broadcast();

  @override
  Stream<ForceDisconnect> get forceDisconnectEvents => _ctrl.stream;

  @override
  Future<void> dispose() async => _ctrl.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockDeviceRegistration implements DeviceRegistrationService {
  @override
  Future<Device?> registerCurrentDevice() async => null;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockReviewService implements ReviewService {
  int connectionCount = 0;

  @override
  Future<void> incrementConnectionCount() async => connectionCount++;

  @override
  bool shouldShowReview() => false;

  @override
  Map<String, dynamic> getMetrics() => {'connectionCount': connectionCount};

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

ServerEntity _makeServer({
  required String id,
  String name = 'Test Server',
  String address = '1.2.3.4',
  int port = 443,
  String protocol = 'vless',
}) {
  return ServerEntity(
    id: id,
    name: name,
    countryCode: 'US',
    countryName: 'United States',
    city: 'New York',
    address: address,
    port: port,
    protocol: protocol,
    isAvailable: true,
  );
}

ImportedConfig _makeImportedConfig({
  required String id,
  String name = 'Custom Config',
  String serverAddress = '5.6.7.8',
  int port = 8443,
  String protocol = 'vless',
}) {
  return ImportedConfig(
    id: id,
    name: name,
    rawUri: 'vless://test@$serverAddress:$port',
    protocol: protocol,
    serverAddress: serverAddress,
    port: port,
    source: ImportSource.clipboard,
    importedAt: DateTime(2026, 1, 1),
    isReachable: true,
  );
}

ProviderContainer _createContainer({
  required _MockVpnRepository repo,
  required _MockNetworkInfo networkInfo,
  required _MockSecureStorage storage,
  required _MockAutoReconnect autoReconnect,
  required _MockKillSwitch killSwitch,
  required _MockWebSocketClient wsClient,
  required _MockDeviceRegistration deviceRegistration,
  required _MockReviewService reviewService,
  VpnSettings vpnSettings = const VpnSettings(),
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
      disconnectVpnUseCaseProvider
          .overrideWithValue(DisconnectVpnUseCase(repo)),
      vpnSettingsProvider.overrideWith((ref) => vpnSettings),
      deviceRegistrationServiceProvider
          .overrideWithValue(deviceRegistration),
      reviewServiceProvider.overrideWithValue(reviewService),
      analyticsProvider.overrideWithValue(const NoopAnalytics()),
    ],
  );
}

Future<VpnConnectionState> _waitForState(ProviderContainer container) async {
  final sub = container.listen(vpnConnectionProvider, (_, _) {});
  await container.read(vpnConnectionProvider.future);
  sub.close();
  return container.read(vpnConnectionProvider).requireValue;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late _MockVpnRepository repo;
  late _MockNetworkInfo networkInfo;
  late _MockSecureStorage storage;
  late _MockAutoReconnect autoReconnect;
  late _MockKillSwitch killSwitch;
  late _MockWebSocketClient wsClient;
  late _MockDeviceRegistration deviceRegistration;
  late _MockReviewService reviewService;
  late ProviderContainer container;

  setUp(() {
    repo = _MockVpnRepository();
    networkInfo = _MockNetworkInfo();
    storage = _MockSecureStorage();
    autoReconnect = _MockAutoReconnect();
    killSwitch = _MockKillSwitch();
    wsClient = _MockWebSocketClient();
    deviceRegistration = _MockDeviceRegistration();
    reviewService = _MockReviewService();
  });

  tearDown(() {
    container.dispose();
    repo.dispose();
    networkInfo.dispose();
  });

  group('connect() and connectFromCustomServer() shared behavior', () {
    test('connect() transitions through Connecting → Connected', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      final initialState = await _waitForState(container);
      expect(initialState.isDisconnected, isTrue);

      final server = _makeServer(id: 'server-1');
      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(server);

      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state.isConnected, isTrue);
      expect(state, isA<VpnConnected>());

      final connected = state as VpnConnected;
      expect(connected.server.id, 'server-1');
      expect(connected.protocol, VpnProtocol.vless);
    });

    test('connectFromCustomServer() transitions through Connecting → Connected',
        () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);

      final imported = _makeImportedConfig(id: 'custom-1');
      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connectFromCustomServer(imported);

      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state.isConnected, isTrue);

      final connected = state as VpnConnected;
      expect(connected.server.id, 'custom-1');
      expect(connected.protocol, VpnProtocol.vless);
    });

    test('both paths start auto-reconnect service', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // connect()
      await notifier.connect(_makeServer(id: 's1'));
      expect(autoReconnect.isStarted, isTrue);

      // Reset
      autoReconnect.isStarted = false;
      await notifier.disconnect();

      // connectFromCustomServer()
      await notifier.connectFromCustomServer(
        _makeImportedConfig(id: 'c1'),
      );
      expect(autoReconnect.isStarted, isTrue);
    });

    test('both paths persist last connection to storage', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // connect()
      await notifier.connect(_makeServer(id: 's1'));
      final stored1 = await storage.read(key: 'last_connected_server');
      expect(stored1, isNotNull);
      expect(stored1, contains('"s1"'));

      await notifier.disconnect();

      // connectFromCustomServer()
      await notifier.connectFromCustomServer(
        _makeImportedConfig(id: 'c1'),
      );
      final stored2 = await storage.read(key: 'last_connected_server');
      expect(stored2, isNotNull);
      expect(stored2, contains('"c1"'));
    });

    test('both paths increment review connection count', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      expect(reviewService.connectionCount, 0);

      await notifier.connect(_makeServer(id: 's1'));
      // Give async _handleReviewPrompt a tick to run
      await Future<void>.delayed(Duration.zero);
      expect(reviewService.connectionCount, 1);

      await notifier.disconnect();

      await notifier.connectFromCustomServer(
        _makeImportedConfig(id: 'c1'),
      );
      await Future<void>.delayed(Duration.zero);
      expect(reviewService.connectionCount, 2);
    });

    test('both paths enable kill switch when setting is on', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
        vpnSettings: const VpnSettings(killSwitch: true),
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      expect(killSwitch.enabled, isFalse);

      await notifier.connect(_makeServer(id: 's1'));
      expect(killSwitch.enabled, isTrue);

      killSwitch.enabled = false;
      await notifier.disconnect();

      await notifier.connectFromCustomServer(
        _makeImportedConfig(id: 'c1'),
      );
      expect(killSwitch.enabled, isTrue);
    });

    test('both paths do not enable kill switch when setting is off', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
        vpnSettings: const VpnSettings(killSwitch: false),
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_makeServer(id: 's1'));
      expect(killSwitch.enabled, isFalse);

      await notifier.disconnect();

      await notifier.connectFromCustomServer(
        _makeImportedConfig(id: 'c1'),
      );
      expect(killSwitch.enabled, isFalse);
    });

    test('connect() is no-op when already connected', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_makeServer(id: 's1'));
      expect(
        container.read(vpnConnectionProvider).requireValue.isConnected,
        isTrue,
      );

      // Second connect should be a no-op
      await notifier.connect(_makeServer(id: 's2'));
      final connected =
          container.read(vpnConnectionProvider).requireValue as VpnConnected;
      expect(connected.server.id, 's1'); // still the first server
    });

    test('connectFromCustomServer() is no-op when already connected', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_makeServer(id: 's1'));

      await notifier.connectFromCustomServer(
        _makeImportedConfig(id: 'c1'),
      );

      final connected =
          container.read(vpnConnectionProvider).requireValue as VpnConnected;
      expect(connected.server.id, 's1'); // no-op, still first server
    });

    test('connect() passes correct config to repository', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      final server = _makeServer(
        id: 'srv-1',
        address: '10.0.0.1',
        port: 8080,
      );
      await notifier.connect(server);

      expect(repo.lastConnectConfig, isNotNull);
      expect(repo.lastConnectConfig!.id, 'srv-1');
      expect(repo.lastConnectConfig!.serverAddress, '10.0.0.1');
      expect(repo.lastConnectConfig!.port, 8080);
      expect(repo.lastConnectConfig!.protocol, VpnProtocol.vless);
      expect(repo.lastConnectConfig!.configData, ''); // empty for normal server
    });

    test('connectFromCustomServer() passes rawUri as configData', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      final imported = _makeImportedConfig(
        id: 'custom-1',
        serverAddress: '9.8.7.6',
        port: 9999,
      );
      await notifier.connectFromCustomServer(imported);

      expect(repo.lastConnectConfig, isNotNull);
      expect(repo.lastConnectConfig!.id, 'custom-1');
      expect(repo.lastConnectConfig!.serverAddress, '9.8.7.6');
      expect(repo.lastConnectConfig!.port, 9999);
      expect(repo.lastConnectConfig!.configData, contains('vless://'));
    });

    test('disconnect() transitions to Disconnected from either path', () async {
      container = _createContainer(
        repo: repo,
        networkInfo: networkInfo,
        storage: storage,
        autoReconnect: autoReconnect,
        killSwitch: killSwitch,
        wsClient: wsClient,
        deviceRegistration: deviceRegistration,
        reviewService: reviewService,
      );

      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Connect via normal path, then disconnect
      await notifier.connect(_makeServer(id: 's1'));
      expect(
        container.read(vpnConnectionProvider).requireValue.isConnected,
        isTrue,
      );

      await notifier.disconnect();
      expect(
        container.read(vpnConnectionProvider).requireValue.isDisconnected,
        isTrue,
      );

      // Connect via custom path, then disconnect
      await notifier.connectFromCustomServer(
        _makeImportedConfig(id: 'c1'),
      );
      expect(
        container.read(vpnConnectionProvider).requireValue.isConnected,
        isTrue,
      );

      await notifier.disconnect();
      expect(
        container.read(vpnConnectionProvider).requireValue.isDisconnected,
        isTrue,
      );
    });
  });
}
