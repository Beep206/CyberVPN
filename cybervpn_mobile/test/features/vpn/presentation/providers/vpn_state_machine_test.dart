import 'dart:async';

import 'package:cybervpn_mobile/core/analytics/noop_analytics.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
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
  final StreamController<ConnectionStateEntity> stateController =
      StreamController<ConnectionStateEntity>.broadcast();

  bool _isConnected = false;
  VpnConfigEntity? _lastConfig;
  bool shouldFail = false;

  @override
  Stream<ConnectionStateEntity> get connectionStateStream =>
      stateController.stream;

  @override
  Future<Result<bool>> get isConnected async => Success(_isConnected);

  @override
  Future<Result<VpnConfigEntity?>> getLastConfig() async =>
      Success(_lastConfig);

  @override
  Future<Result<void>> connect(VpnConfigEntity config) async {
    if (shouldFail) throw Exception('Connection failed');
    _isConnected = true;
    _lastConfig = config;
    return const Success<void>(null);
  }

  @override
  Future<Result<void>> disconnect() async {
    _isConnected = false;
    return const Success<void>(null);
  }

  void dispose() => stateController.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockNetworkInfo implements NetworkInfo {
  final StreamController<bool> connectivityController =
      StreamController<bool>.broadcast();
  bool _isConnected = true;

  @override
  Stream<bool> get onConnectivityChanged => connectivityController.stream;

  @override
  Future<bool> get isConnected async => _isConnected;

  void setConnected(bool value) => _isConnected = value;

  void dispose() => connectivityController.close();

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
  Future<void> delete({required String key}) async => _storage.remove(key);

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
  final StreamController<ForceDisconnect> forceDisconnectController =
      StreamController<ForceDisconnect>.broadcast();

  @override
  Stream<ForceDisconnect> get forceDisconnectEvents =>
      forceDisconnectController.stream;

  @override
  Future<void> dispose() async => forceDisconnectController.close();

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
  @override
  Future<void> incrementConnectionCount() async {}

  @override
  bool shouldShowReview() => false;

  @override
  Map<String, dynamic> getMetrics() => {};

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

ServerEntity _server({String id = 'srv-1'}) => ServerEntity(
      id: id,
      name: 'Test Server',
      countryCode: 'US',
      countryName: 'United States',
      city: 'New York',
      address: '1.2.3.4',
      port: 443,
      protocol: 'vless',
      isAvailable: true,
    );

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
      disconnectVpnUseCaseProvider.overrideWithValue(DisconnectVpnUseCase(repo)),
      vpnSettingsProvider.overrideWith((ref) => vpnSettings),
      deviceRegistrationServiceProvider.overrideWithValue(deviceRegistration),
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

  ProviderContainer buildContainer({VpnSettings? vpnSettings}) {
    container = _createContainer(
      repo: repo,
      networkInfo: networkInfo,
      storage: storage,
      autoReconnect: autoReconnect,
      killSwitch: killSwitch,
      wsClient: wsClient,
      deviceRegistration: deviceRegistration,
      reviewService: reviewService,
      vpnSettings: vpnSettings ?? const VpnSettings(),
    );
    return container;
  }

  group('VPN state machine — initial state', () {
    test('starts in VpnDisconnected when no prior connection', () async {
      buildContainer();
      final state = await _waitForState(container);
      expect(state, isA<VpnDisconnected>());
    });

    test('convenience getters reflect correct state', () async {
      buildContainer();
      final state = await _waitForState(container);
      expect(state.isDisconnected, isTrue);
      expect(state.isConnected, isFalse);
      expect(state.isConnecting, isFalse);
      expect(state.isReconnecting, isFalse);
      expect(state.isError, isFalse);
      expect(state.server, isNull);
    });
  });

  group('VPN state machine — disconnect', () {
    test('disconnect stops auto-reconnect', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_server());
      expect(autoReconnect.isStarted, isTrue);

      await notifier.disconnect();
      expect(autoReconnect.isStarted, isFalse);
    });

    test('disconnect disables kill switch', () async {
      buildContainer(vpnSettings: const VpnSettings(killSwitch: true));
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_server());
      expect(killSwitch.enabled, isTrue);

      await notifier.disconnect();
      expect(killSwitch.enabled, isFalse);
    });

    test('disconnect clears persisted connection', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_server());
      expect(await storage.read(key: 'last_connected_server'), isNotNull);

      await notifier.disconnect();
      expect(await storage.read(key: 'last_connected_server'), isNull);
    });

    test('disconnect is no-op when already disconnected', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Should not throw or change state
      await notifier.disconnect();
      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state, isA<VpnDisconnected>());
    });
  });

  group('VPN state machine — network change / reconnect', () {
    test('network loss while connected transitions to VpnReconnecting', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_server());
      expect(container.read(vpnConnectionProvider).requireValue, isA<VpnConnected>());

      await notifier.handleNetworkChange(false);
      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state, isA<VpnReconnecting>());
      expect((state as VpnReconnecting).attempt, 1);
      expect(state.server?.id, 'srv-1');
    });

    test('network loss while disconnected is a no-op', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.handleNetworkChange(false);
      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state, isA<VpnDisconnected>());
    });
  });

  group('VPN state machine — force disconnect', () {
    test('force disconnect event disconnects VPN and shows error', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_server());
      expect(container.read(vpnConnectionProvider).requireValue, isA<VpnConnected>());

      // Simulate force disconnect event via the WebSocket stream
      wsClient.forceDisconnectController
          .add(const ForceDisconnect(reason: 'Account suspended'));

      // Let the event propagate
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state, isA<VpnError>());
      expect((state as VpnError).message, contains('Account suspended'));
    });
  });

  group('VPN state machine — connection errors', () {
    test('connect failure transitions to VpnError', () async {
      buildContainer();
      await _waitForState(container);
      repo.shouldFail = true;

      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(_server());

      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state, isA<VpnError>());
      expect((state as VpnError).message, contains('Connection failed'));
    });

    test('connect failure stops auto-reconnect', () async {
      buildContainer();
      await _waitForState(container);
      repo.shouldFail = true;

      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(_server());

      expect(autoReconnect.isStarted, isFalse);
    });

    test('connect failure disables kill switch', () async {
      buildContainer(vpnSettings: const VpnSettings(killSwitch: true));
      await _waitForState(container);
      repo.shouldFail = true;

      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(_server());

      expect(killSwitch.enabled, isFalse);
    });
  });

  group('VPN state machine — repository stream events', () {
    test('external disconnect event transitions to VpnDisconnected', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_server());

      // Simulate external disconnect from the VPN engine
      repo.stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.disconnected,
      ));

      await Future<void>.delayed(const Duration(milliseconds: 50));
      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state, isA<VpnDisconnected>());
    });

    test('error state from repository stream transitions to VpnError', () async {
      buildContainer();
      await _waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(_server());

      repo.stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.error,
        errorMessage: 'Tunnel crashed',
      ));

      await Future<void>.delayed(const Duration(milliseconds: 50));
      final state = container.read(vpnConnectionProvider).requireValue;
      expect(state, isA<VpnError>());
      expect((state as VpnError).message, 'Tunnel crashed');
    });
  });

  group('VPN state machine — derived providers', () {
    test('isConnectedProvider reflects connection state', () async {
      buildContainer();
      await _waitForState(container);

      expect(container.read(isConnectedProvider), isFalse);

      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(_server());

      expect(container.read(isConnectedProvider), isTrue);

      await notifier.disconnect();
      expect(container.read(isConnectedProvider), isFalse);
    });

    test('currentServerProvider reflects connected server', () async {
      buildContainer();
      await _waitForState(container);

      expect(container.read(currentServerProvider), isNull);

      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(_server(id: 'test-srv'));

      expect(container.read(currentServerProvider)?.id, 'test-srv');

      await notifier.disconnect();
      expect(container.read(currentServerProvider), isNull);
    });

    test('activeProtocolProvider reflects connected protocol', () async {
      buildContainer();
      await _waitForState(container);

      expect(container.read(activeProtocolProvider), isNull);

      final notifier = container.read(vpnConnectionProvider.notifier);
      await notifier.connect(_server());

      expect(container.read(activeProtocolProvider), VpnProtocol.vless);

      await notifier.disconnect();
      expect(container.read(activeProtocolProvider), isNull);
    });
  });
}
