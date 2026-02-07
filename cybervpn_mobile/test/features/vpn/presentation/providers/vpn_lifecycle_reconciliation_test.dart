import 'dart:async';
import 'dart:convert';

import 'package:cybervpn_mobile/core/analytics/noop_analytics.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/services/device_registration_service.dart';
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
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mocks (same pattern as vpn_state_machine_test.dart)
// ---------------------------------------------------------------------------

class _MockVpnRepository implements VpnRepository {
  final StreamController<ConnectionStateEntity> stateController =
      StreamController<ConnectionStateEntity>.broadcast();

  bool isConnectedValue = false;
  VpnConfigEntity? lastConfig;
  bool shouldFail = false;

  @override
  Stream<ConnectionStateEntity> get connectionStateStream =>
      stateController.stream;

  @override
  Future<Result<bool>> get isConnected async => Success(isConnectedValue);

  @override
  Future<Result<VpnConfigEntity?>> getLastConfig() async =>
      Success(lastConfig);

  @override
  Future<Result<void>> connect(VpnConfigEntity config) async {
    if (shouldFail) throw Exception('Connection failed');
    isConnectedValue = true;
    lastConfig = config;
    return const Success<void>(null);
  }

  @override
  Future<Result<void>> disconnect() async {
    isConnectedValue = false;
    return const Success<void>(null);
  }

  void dispose() => stateController.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockNetworkInfo implements NetworkInfo {
  final StreamController<bool> connectivityController =
      StreamController<bool>.broadcast();
  bool isConnectedValue = true;

  @override
  Stream<bool> get onConnectivityChanged => connectivityController.stream;

  @override
  Future<bool> get isConnected async => isConnectedValue;

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

ServerEntity _testServer({String id = 'srv-1', bool isAvailable = true}) =>
    ServerEntity(
      id: id,
      name: 'Test Server',
      countryCode: 'US',
      countryName: 'United States',
      city: 'New York',
      address: '1.2.3.4',
      port: 443,
      protocol: 'vless',
      isAvailable: isAvailable,
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

/// Pre-seed secure storage with a saved server so build() can restore it.
Future<void> _seedLastServer(
  _MockSecureStorage storage,
  ServerEntity server,
) async {
  await storage.write(
    key: 'last_connected_server',
    value: jsonEncode(server.toJson()),
  );
  await storage.write(key: 'last_connected_protocol', value: 'vless');
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

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

  group('VPN lifecycle reconciliation on app resume', () {
    test('no-op when state is VpnDisconnected', () async {
      buildContainer();
      final state = await _waitForState(container);
      expect(state, isA<VpnDisconnected>());

      // Simulate app resume — the observer should not change state.
      TestWidgetsFlutterBinding.instance
          .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final stateAfter = container.read(vpnConnectionProvider).requireValue;
      expect(stateAfter, isA<VpnDisconnected>());
    });

    test(
        'transitions to VpnDisconnected when engine is disconnected and '
        'autoConnect is off', () async {
      final server = _testServer();
      repo.isConnectedValue = true;
      repo.lastConfig = VpnConfigEntity(
        id: server.id,
        name: server.name,
        serverAddress: server.address,
        port: server.port,
        protocol: VpnProtocol.vless,
        configData: '',
      );
      await _seedLastServer(storage, server);

      // Build container — initial state should be VpnConnected because
      // repo.isConnected returns true.
      buildContainer(vpnSettings: const VpnSettings(autoConnectOnLaunch: false));
      final initialState = await _waitForState(container);
      expect(initialState, isA<VpnConnected>());

      // Simulate engine dying while app was in background.
      repo.isConnectedValue = false;

      // Simulate app resume.
      TestWidgetsFlutterBinding.instance
          .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await Future<void>.delayed(const Duration(milliseconds: 200));

      final stateAfter = container.read(vpnConnectionProvider).requireValue;
      expect(stateAfter, isA<VpnDisconnected>());
    });

    test(
        'attempts reconnect when engine is disconnected and '
        'autoConnect is on', () async {
      final server = _testServer();
      repo.isConnectedValue = true;
      repo.lastConfig = VpnConfigEntity(
        id: server.id,
        name: server.name,
        serverAddress: server.address,
        port: server.port,
        protocol: VpnProtocol.vless,
        configData: '',
      );
      await _seedLastServer(storage, server);

      buildContainer(
        vpnSettings: const VpnSettings(autoConnectOnLaunch: true),
      );
      final initialState = await _waitForState(container);
      expect(initialState, isA<VpnConnected>());

      // Engine dies while backgrounded, but connect will succeed.
      repo.isConnectedValue = false;

      // Trigger resume.
      TestWidgetsFlutterBinding.instance
          .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await Future<void>.delayed(const Duration(milliseconds: 300));

      // After reconnect attempt, the state should return to VpnConnected
      // because the mock connect succeeds.
      final stateAfter = container.read(vpnConnectionProvider).requireValue;
      expect(stateAfter, isA<VpnConnected>());
    });

    test(
        'transitions to VpnError when reconnect fails and '
        'autoConnect is on', () async {
      final server = _testServer();
      repo.isConnectedValue = true;
      repo.lastConfig = VpnConfigEntity(
        id: server.id,
        name: server.name,
        serverAddress: server.address,
        port: server.port,
        protocol: VpnProtocol.vless,
        configData: '',
      );
      await _seedLastServer(storage, server);

      buildContainer(
        vpnSettings: const VpnSettings(autoConnectOnLaunch: true),
      );
      final initialState = await _waitForState(container);
      expect(initialState, isA<VpnConnected>());

      // Engine dies and reconnect will fail.
      repo.isConnectedValue = false;
      repo.shouldFail = true;

      // Trigger resume.
      TestWidgetsFlutterBinding.instance
          .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await Future<void>.delayed(const Duration(milliseconds: 300));

      // The notifier's connect() catches the error and sets VpnError
      // (not VpnDisconnected) so the UI can display an error message.
      final stateAfter = container.read(vpnConnectionProvider).requireValue;
      expect(stateAfter, isA<VpnError>());
    });

    test('stays VpnConnected when engine is still connected on resume',
        () async {
      final server = _testServer();
      repo.isConnectedValue = true;
      repo.lastConfig = VpnConfigEntity(
        id: server.id,
        name: server.name,
        serverAddress: server.address,
        port: server.port,
        protocol: VpnProtocol.vless,
        configData: '',
      );
      await _seedLastServer(storage, server);

      buildContainer();
      final initialState = await _waitForState(container);
      expect(initialState, isA<VpnConnected>());

      // Engine is still running on resume.
      // repo.isConnectedValue is already true.

      TestWidgetsFlutterBinding.instance
          .handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await Future<void>.delayed(const Duration(milliseconds: 200));

      final stateAfter = container.read(vpnConnectionProvider).requireValue;
      expect(stateAfter, isA<VpnConnected>());
    });
  });
}
