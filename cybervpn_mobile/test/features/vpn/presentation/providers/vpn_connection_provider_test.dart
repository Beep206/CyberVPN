import 'dart:async';
import 'dart:convert';

import 'package:cybervpn_mobile/core/analytics/noop_analytics.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/security/device_integrity.dart';
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
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_state.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// =============================================================================
// Mocks
// =============================================================================

class MockVpnRepository implements VpnRepository {
  final StreamController<ConnectionStateEntity> stateController =
      StreamController<ConnectionStateEntity>.broadcast();

  bool isConnectedValue = false;
  VpnConfigEntity? lastConfig;
  bool shouldFail = false;
  int connectCallCount = 0;
  int disconnectCallCount = 0;

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
    connectCallCount++;
    if (shouldFail) throw Exception('Connection failed');
    isConnectedValue = true;
    lastConfig = config;
    return const Success<void>(null);
  }

  @override
  Future<Result<void>> disconnect() async {
    disconnectCallCount++;
    if (shouldFail) throw Exception('Disconnect failed');
    isConnectedValue = false;
    return const Success<void>(null);
  }

  @override
  Future<Result<void>> saveConfig(VpnConfigEntity config) async =>
      const Success(null);

  void dispose() => stateController.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class MockNetworkInfo implements NetworkInfo {
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

class MockSecureStorage implements SecureStorageWrapper {
  final Map<String, String> store = {};

  @override
  Future<String?> read({required String key}) async => store[key];

  @override
  Future<void> write({required String key, required String value}) async {
    store[key] = value;
  }

  @override
  Future<void> delete({required String key}) async => store.remove(key);

  @override
  Future<void> deleteAll() async => store.clear();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class MockAutoReconnect implements AutoReconnectService {
  bool isStarted = false;
  VpnConfigEntity? lastConfig;

  @override
  void start(VpnConfigEntity config) {
    isStarted = true;
    lastConfig = config;
  }

  @override
  void stop() => isStarted = false;

  @override
  void dispose() {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class MockKillSwitch implements KillSwitchService {
  bool enabled = false;
  int enableCallCount = 0;
  int disableCallCount = 0;

  @override
  Future<void> enable() async {
    enableCallCount++;
    enabled = true;
  }

  @override
  Future<void> disable() async {
    disableCallCount++;
    enabled = false;
  }

  @override
  Future<bool> isEnabled() async => enabled;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class MockWebSocketClient implements WebSocketClient {
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

class MockDeviceRegistration implements DeviceRegistrationService {
  int registerCallCount = 0;

  @override
  Future<Device?> registerCurrentDevice() async {
    registerCallCount++;
    return null;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class MockReviewService implements ReviewService {
  int incrementCallCount = 0;

  @override
  Future<void> incrementConnectionCount() async => incrementCallCount++;

  @override
  bool shouldShowReview() => false;

  @override
  Map<String, dynamic> getMetrics() => {};

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class MockDeviceIntegrityChecker implements DeviceIntegrityChecker {
  bool shouldBlock = false;

  @override
  Future<bool> shouldBlockVpn() async => shouldBlock;

  @override
  Future<bool> isDeviceRooted() async => shouldBlock;

  @override
  bool get isBlockingEnabled => shouldBlock;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// =============================================================================
// Test Helpers
// =============================================================================

ServerEntity testServer({
  String id = 'srv-1',
  String name = 'Test Server',
  String countryCode = 'US',
  String city = 'New York',
  bool isAvailable = true,
  bool isPremium = false,
}) =>
    ServerEntity(
      id: id,
      name: name,
      countryCode: countryCode,
      countryName: 'United States',
      city: city,
      address: '1.2.3.4',
      port: 443,
      protocol: 'vless',
      isAvailable: isAvailable,
      isPremium: isPremium,
    );

VpnConfigEntity testVpnConfig({
  String id = 'cfg-1',
  String name = 'Test Config',
  String serverAddress = '1.2.3.4',
  int port = 443,
  VpnProtocol protocol = VpnProtocol.vless,
  String configData = 'vless://test-config-data',
}) =>
    VpnConfigEntity(
      id: id,
      name: name,
      serverAddress: serverAddress,
      port: port,
      protocol: protocol,
      configData: configData,
    );

/// Holds all mock instances for a single test to simplify access.
class TestMocks {
  final MockVpnRepository repo;
  final MockNetworkInfo networkInfo;
  final MockSecureStorage storage;
  final MockAutoReconnect autoReconnect;
  final MockKillSwitch killSwitch;
  final MockWebSocketClient wsClient;
  final MockDeviceRegistration deviceRegistration;
  final MockReviewService reviewService;
  final MockDeviceIntegrityChecker integrityChecker;

  TestMocks()
      : repo = MockVpnRepository(),
        networkInfo = MockNetworkInfo(),
        storage = MockSecureStorage(),
        autoReconnect = MockAutoReconnect(),
        killSwitch = MockKillSwitch(),
        wsClient = MockWebSocketClient(),
        deviceRegistration = MockDeviceRegistration(),
        reviewService = MockReviewService(),
        integrityChecker = MockDeviceIntegrityChecker();

  void dispose() {
    repo.dispose();
    networkInfo.dispose();
  }
}

/// A fake authenticated user for tests.
const _testUser = UserEntity(
  id: 'user-1',
  email: 'test@example.com',
  isEmailVerified: true,
);

ProviderContainer createContainer({
  required TestMocks mocks,
  VpnSettings vpnSettings = const VpnSettings(),
  bool isAuthenticated = false,
}) {
  return ProviderContainer(
    overrides: [
      vpnRepositoryProvider.overrideWithValue(mocks.repo),
      networkInfoProvider.overrideWithValue(mocks.networkInfo),
      secureStorageProvider.overrideWithValue(mocks.storage),
      autoReconnectServiceProvider.overrideWithValue(mocks.autoReconnect),
      killSwitchServiceProvider.overrideWithValue(mocks.killSwitch),
      webSocketClientProvider.overrideWithValue(mocks.wsClient),
      connectVpnUseCaseProvider
          .overrideWithValue(ConnectVpnUseCase(mocks.repo)),
      disconnectVpnUseCaseProvider
          .overrideWithValue(DisconnectVpnUseCase(mocks.repo)),
      vpnSettingsProvider.overrideWith((ref) => vpnSettings),
      deviceRegistrationServiceProvider
          .overrideWithValue(mocks.deviceRegistration),
      reviewServiceProvider.overrideWithValue(mocks.reviewService),
      analyticsProvider.overrideWithValue(const NoopAnalytics()),
      deviceIntegrityCheckerProvider
          .overrideWithValue(mocks.integrityChecker),
      if (isAuthenticated)
        authProvider.overrideWith(
          () => _FakeAuthNotifier(AuthAuthenticated(_testUser)),
        ),
    ],
  );
}

/// Fake auth notifier that returns a pre-set state.
class _FakeAuthNotifier extends AsyncNotifier<AuthState>
    implements AuthNotifier {
  final AuthState _state;
  _FakeAuthNotifier(this._state);

  @override
  Future<AuthState> build() async => _state;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// Waits for the vpnConnectionProvider to settle (non-loading).
Future<VpnConnectionState> waitForState(ProviderContainer container) async {
  // Wait for the async notifier to initialize.
  await container.read(vpnConnectionProvider.future);
  return container.read(vpnConnectionProvider).value!;
}

/// Seeds the mock secure storage with a last-connected server JSON.
void seedLastServer(MockSecureStorage storage, ServerEntity server) {
  storage.store['last_connected_server'] = jsonEncode(server.toJson());
  storage.store['last_connected_protocol'] = 'vless';
}

// =============================================================================
// Tests
// =============================================================================

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late TestMocks mocks;

  setUp(() {
    mocks = TestMocks();
  });

  tearDown(() {
    mocks.dispose();
  });

  // ── Initialization ─────────────────────────────────────────────────────────

  group('initialization', () {
    test('starts in VpnDisconnected when no prior connection', () async {
      final container = createContainer(mocks: mocks);
      final state = await waitForState(container);
      expect(state, isA<VpnDisconnected>());
      container.dispose();
    });

    test('starts in VpnConnected when engine reports connected + last config exists', () async {
      mocks.repo.isConnectedValue = true;
      mocks.repo.lastConfig = testVpnConfig();
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(mocks: mocks);
      final state = await waitForState(container);
      expect(state, isA<VpnConnected>());
      container.dispose();
    });
  });

  // ── Connect ────────────────────────────────────────────────────────────────

  group('connect()', () {
    test('transitions Disconnected → Connecting → Connected on success', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);
      final server = testServer();

      await notifier.connect(server);
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnConnected>());
      expect(mocks.repo.connectCallCount, equals(1));
      container.dispose();
    });

    test('no-ops when already connected', () async {
      mocks.repo.isConnectedValue = true;
      mocks.repo.lastConfig = testVpnConfig();
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer(id: 'srv-2'));
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Should not have called connect again.
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });

    test('transitions to VpnError on connection failure', () async {
      mocks.repo.shouldFail = true;
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      container.dispose();
    });
  });

  // ── Disconnect ─────────────────────────────────────────────────────────────

  group('disconnect()', () {
    test('transitions Connected → Disconnecting → Disconnected', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Connect first.
      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());

      // Disconnect.
      await notifier.disconnect();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnDisconnected>());
      expect(mocks.repo.disconnectCallCount, equals(1));
      container.dispose();
    });
  });

  // ── Auto-connect on launch ─────────────────────────────────────────────────

  group('auto-connect on launch', () {
    test('connects when enabled + authenticated + last server available', () async {
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(autoConnectOnLaunch: true),
        isAuthenticated: true,
      );

      // Force auth provider to settle so vpnConnectionProvider sees
      // AuthAuthenticated (not AsyncLoading) when it calls ref.read().
      await container.read(authProvider.future);

      await waitForState(container);
      // Give auto-connect time to run (unawaited).
      await Future<void>.delayed(const Duration(milliseconds: 200));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnConnected>());
      expect(mocks.repo.connectCallCount, equals(1));
      container.dispose();
    });

    test('skips when no network', () async {
      mocks.networkInfo.isConnectedValue = false;
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(autoConnectOnLaunch: true),
        isAuthenticated: true,
      );

      await container.read(authProvider.future);
      await waitForState(container);
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnDisconnected>());
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });

    test('skips when no last server saved', () async {
      // Don't seed any server.
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(autoConnectOnLaunch: true),
        isAuthenticated: true,
      );

      await container.read(authProvider.future);
      await waitForState(container);
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnDisconnected>());
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });

    test('skips when saved server is unavailable', () async {
      seedLastServer(mocks.storage, testServer(isAvailable: false));

      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(autoConnectOnLaunch: true),
        isAuthenticated: true,
      );

      await container.read(authProvider.future);
      await waitForState(container);
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnDisconnected>());
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });

    test('skips when autoConnectOnLaunch is disabled', () async {
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(autoConnectOnLaunch: false),
        isAuthenticated: true,
      );

      await container.read(authProvider.future);
      await waitForState(container);
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnDisconnected>());
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });
  });

  // ── Connect with kill switch / DNS / rooted device ─────────────────────────

  group('connect() side-effects', () {
    test('enables kill switch when killSwitch setting is on', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(killSwitch: true),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(mocks.killSwitch.enableCallCount, equals(1));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('skips kill switch when killSwitch setting is off', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(killSwitch: false),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(mocks.killSwitch.enableCallCount, equals(0));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('blocks connection on rooted device when enforcement enabled', () async {
      mocks.integrityChecker.shouldBlock = true;

      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });

    test('persists last server and protocol to secure storage', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final stored = mocks.storage.store['last_connected_server'];
      expect(stored, isNotNull);
      expect(stored, contains('"id":"srv-1"'));
      expect(mocks.storage.store['last_connected_protocol'], equals('vless'));
      container.dispose();
    });

    test('starts auto-reconnect service on successful connect', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(mocks.autoReconnect.isStarted, isTrue);
      container.dispose();
    });

    test('triggers device registration on connect', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 100));

      expect(mocks.deviceRegistration.registerCallCount, equals(1));
      container.dispose();
    });

    test('disables kill switch on connection failure', () async {
      mocks.repo.shouldFail = true;
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(killSwitch: true),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      // Kill switch is enabled before connect, then disabled on failure.
      expect(mocks.killSwitch.enableCallCount, equals(1));
      expect(mocks.killSwitch.disableCallCount, equals(1));
      container.dispose();
    });
  });

  // ── handleNetworkChange() ─────────────────────────────────────────────────

  group('handleNetworkChange()', () {
    test('network lost while connected → VpnReconnecting', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Connect first.
      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());

      // Simulate network loss.
      await notifier.handleNetworkChange(false);

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnReconnecting>());
      expect((state as VpnReconnecting).attempt, equals(1));
      container.dispose();
    });

    test('network restored while reconnecting → state unchanged (auto-reconnect handles)', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Connect, then lose network.
      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      await notifier.handleNetworkChange(false);
      expect(container.read(vpnConnectionProvider).value, isA<VpnReconnecting>());

      // Network restored — state stays reconnecting (auto-reconnect manages tunnel).
      await notifier.handleNetworkChange(true);

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnReconnecting>());
      container.dispose();
    });

    test('network change while disconnected → no state change', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnected>());

      await notifier.handleNetworkChange(false);
      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnected>());

      await notifier.handleNetworkChange(true);
      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnected>());
      container.dispose();
    });

    test('network loss while not connected → stays disconnected', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnected>());

      // Network loss while disconnected should not trigger reconnecting.
      await notifier.handleNetworkChange(false);

      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnected>());
      container.dispose();
    });
  });

  // ── connectFromCustomServer() ─────────────────────────────────────────────

  group('connectFromCustomServer()', () {
    ImportedConfig testImportedConfig({
      String id = 'custom-1',
      String name = 'Custom Server',
      String rawUri = 'vless://custom-config-data',
      String protocol = 'vless',
      String serverAddress = '10.0.0.1',
      int port = 443,
    }) =>
        ImportedConfig(
          id: id,
          name: name,
          rawUri: rawUri,
          protocol: protocol,
          serverAddress: serverAddress,
          port: port,
          source: ImportSource.manual,
          importedAt: DateTime.now(),
        );

    test('transitions Disconnected → Connecting → Connected on success', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connectFromCustomServer(testImportedConfig());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnConnected>());
      expect(mocks.repo.connectCallCount, equals(1));
      container.dispose();
    });

    test('creates pseudo server with countryCode XX and Custom country', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connectFromCustomServer(testImportedConfig());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value as VpnConnected;
      expect(state.server.countryCode, equals('XX'));
      expect(state.server.countryName, equals('Custom'));
      expect(state.server.city, equals('10.0.0.1'));
      container.dispose();
    });

    test('no-ops when already connected', () async {
      mocks.repo.isConnectedValue = true;
      mocks.repo.lastConfig = testVpnConfig();
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connectFromCustomServer(testImportedConfig());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });

    test('transitions to VpnError on failure', () async {
      mocks.repo.shouldFail = true;
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connectFromCustomServer(testImportedConfig());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      container.dispose();
    });

    test('blocks on rooted device', () async {
      mocks.integrityChecker.shouldBlock = true;
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connectFromCustomServer(testImportedConfig());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });
  });

  // ── disconnect() failure ─────────────────────────────────────────────────

  group('disconnect() failure', () {
    test('transitions to VpnError when disconnect throws', () async {
      final failRepo = MockVpnRepository();
      failRepo.isConnectedValue = false;
      final failMocks = TestMocks();
      // Replace repo with one that fails on disconnect.
      final container = ProviderContainer(
        overrides: [
          vpnRepositoryProvider.overrideWithValue(failRepo),
          networkInfoProvider.overrideWithValue(failMocks.networkInfo),
          secureStorageProvider.overrideWithValue(failMocks.storage),
          autoReconnectServiceProvider.overrideWithValue(failMocks.autoReconnect),
          killSwitchServiceProvider.overrideWithValue(failMocks.killSwitch),
          webSocketClientProvider.overrideWithValue(failMocks.wsClient),
          connectVpnUseCaseProvider
              .overrideWithValue(ConnectVpnUseCase(failRepo)),
          disconnectVpnUseCaseProvider
              .overrideWithValue(DisconnectVpnUseCase(failRepo)),
          vpnSettingsProvider.overrideWith((ref) => const VpnSettings()),
          deviceRegistrationServiceProvider
              .overrideWithValue(failMocks.deviceRegistration),
          reviewServiceProvider.overrideWithValue(failMocks.reviewService),
          analyticsProvider.overrideWithValue(const NoopAnalytics()),
          deviceIntegrityCheckerProvider
              .overrideWithValue(failMocks.integrityChecker),
        ],
      );

      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Connect first.
      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());

      // Make disconnect fail.
      failRepo.disconnectCallCount = 0;
      // Override disconnect to throw.
      failRepo.shouldFail = true;

      await notifier.disconnect();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Should transition to VpnError since disconnect failed.
      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      container.dispose();
      failMocks.dispose();
    });
  });

  // ── Repository state stream ─────────────────────────────────────────────

  group('repository state stream', () {
    test('connected event transitions to VpnConnected', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Connect to set a server in state.
      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());

      // Emit a connected event from repository stream.
      mocks.repo.stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.connected,
      ));
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('disconnected event transitions to VpnDisconnected', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Emit unexpected disconnect from repository.
      mocks.repo.stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.disconnected,
      ));
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnected>());
      expect(mocks.autoReconnect.isStarted, isFalse);
      container.dispose();
    });

    test('error event transitions to VpnError', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);

      mocks.repo.stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.error,
        errorMessage: 'tunnel died',
      ));
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      expect((state as VpnError).message, contains('tunnel died'));
      container.dispose();
    });

    test('connecting event transitions to VpnConnecting', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);

      mocks.repo.stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.connecting,
      ));
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnecting>());
      container.dispose();
    });

    test('disconnecting event transitions to VpnDisconnecting', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);

      mocks.repo.stateController.add(const ConnectionStateEntity(
        status: VpnConnectionStatus.disconnecting,
      ));
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnecting>());
      container.dispose();
    });

    test('stream error transitions to VpnError', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);

      mocks.repo.stateController.addError('stream failed');
      await Future<void>.delayed(const Duration(milliseconds: 50));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      container.dispose();
    });
  });

  // ── WebSocket force_disconnect ──────────────────────────────────────────

  group('WebSocket force_disconnect', () {
    test('force disconnect transitions connected to VpnError with reason', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      // Connect first.
      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());

      // Emit force disconnect event.
      mocks.wsClient.forceDisconnectController.add(
        const ForceDisconnect(reason: 'Session expired'),
      );
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      expect((state as VpnError).message, contains('Session expired'));
      container.dispose();
    });

    test('force disconnect with empty reason uses default message', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      mocks.wsClient.forceDisconnectController.add(
        const ForceDisconnect(reason: ''),
      );
      await Future<void>.delayed(const Duration(milliseconds: 100));

      final state = container.read(vpnConnectionProvider).value;
      expect(state, isA<VpnError>());
      expect((state as VpnError).message, equals('Disconnected by server'));
      container.dispose();
    });
  });

  // ── connectToLastOrRecommended() ────────────────────────────────────────

  group('connectToLastOrRecommended()', () {
    test('connects to last server when available', () async {
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connectToLastOrRecommended();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      expect(mocks.repo.connectCallCount, equals(1));
      container.dispose();
    });

    test('falls back to recommended server when no last server', () async {
      // No last server, but provide a recommended server.
      final recommended = testServer(id: 'recommended-1', name: 'Recommended');
      final container = ProviderContainer(
        overrides: [
          vpnRepositoryProvider.overrideWithValue(mocks.repo),
          networkInfoProvider.overrideWithValue(mocks.networkInfo),
          secureStorageProvider.overrideWithValue(mocks.storage),
          autoReconnectServiceProvider.overrideWithValue(mocks.autoReconnect),
          killSwitchServiceProvider.overrideWithValue(mocks.killSwitch),
          webSocketClientProvider.overrideWithValue(mocks.wsClient),
          connectVpnUseCaseProvider
              .overrideWithValue(ConnectVpnUseCase(mocks.repo)),
          disconnectVpnUseCaseProvider
              .overrideWithValue(DisconnectVpnUseCase(mocks.repo)),
          vpnSettingsProvider.overrideWith((ref) => const VpnSettings()),
          deviceRegistrationServiceProvider
              .overrideWithValue(mocks.deviceRegistration),
          reviewServiceProvider.overrideWithValue(mocks.reviewService),
          analyticsProvider.overrideWithValue(const NoopAnalytics()),
          deviceIntegrityCheckerProvider
              .overrideWithValue(mocks.integrityChecker),
          recommendedServerProvider.overrideWithValue(recommended),
        ],
      );

      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connectToLastOrRecommended();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('throws when no server available', () async {
      final container = ProviderContainer(
        overrides: [
          vpnRepositoryProvider.overrideWithValue(mocks.repo),
          networkInfoProvider.overrideWithValue(mocks.networkInfo),
          secureStorageProvider.overrideWithValue(mocks.storage),
          autoReconnectServiceProvider.overrideWithValue(mocks.autoReconnect),
          killSwitchServiceProvider.overrideWithValue(mocks.killSwitch),
          webSocketClientProvider.overrideWithValue(mocks.wsClient),
          connectVpnUseCaseProvider
              .overrideWithValue(ConnectVpnUseCase(mocks.repo)),
          disconnectVpnUseCaseProvider
              .overrideWithValue(DisconnectVpnUseCase(mocks.repo)),
          vpnSettingsProvider.overrideWith((ref) => const VpnSettings()),
          deviceRegistrationServiceProvider
              .overrideWithValue(mocks.deviceRegistration),
          reviewServiceProvider.overrideWithValue(mocks.reviewService),
          analyticsProvider.overrideWithValue(const NoopAnalytics()),
          deviceIntegrityCheckerProvider
              .overrideWithValue(mocks.integrityChecker),
          recommendedServerProvider.overrideWithValue(null),
        ],
      );

      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      expect(
        () => notifier.connectToLastOrRecommended(),
        throwsException,
      );
      container.dispose();
    });

    test('no-ops when already connected', () async {
      mocks.repo.isConnectedValue = true;
      mocks.repo.lastConfig = testVpnConfig();
      seedLastServer(mocks.storage, testServer());

      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());

      await notifier.connectToLastOrRecommended();
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Should not have connected again.
      expect(mocks.repo.connectCallCount, equals(0));
      container.dispose();
    });
  });

  // ── applyKillSwitchSetting() ────────────────────────────────────────────

  group('applyKillSwitchSetting()', () {
    test('enables kill switch when connected and setting is true', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());

      mocks.killSwitch.enableCallCount = 0;
      await notifier.applyKillSwitchSetting(true);
      expect(mocks.killSwitch.enableCallCount, equals(1));
      container.dispose();
    });

    test('disables kill switch when connected and setting is false', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      mocks.killSwitch.disableCallCount = 0;
      await notifier.applyKillSwitchSetting(false);
      expect(mocks.killSwitch.disableCallCount, equals(1));
      container.dispose();
    });

    test('no-ops when not connected', () async {
      final container = createContainer(mocks: mocks);
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);
      expect(container.read(vpnConnectionProvider).value, isA<VpnDisconnected>());

      await notifier.applyKillSwitchSetting(true);
      expect(mocks.killSwitch.enableCallCount, equals(0));
      container.dispose();
    });
  });

  // ── Protocol/DNS resolution via connect settings ────────────────────────

  group('protocol and DNS resolution', () {
    test('connect with vlessReality preferred protocol', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(
          preferredProtocol: PreferredProtocol.vlessReality,
        ),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('connect with cloudflare DNS provider', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(
          dnsProvider: DnsProvider.cloudflare,
        ),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('connect with google DNS provider', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(
          dnsProvider: DnsProvider.google,
        ),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('connect with quad9 DNS provider', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(
          dnsProvider: DnsProvider.quad9,
        ),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('connect with custom DNS provider', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(
          dnsProvider: DnsProvider.custom,
          customDns: '8.8.4.4',
        ),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });

    test('connect with custom DNS provider but no value falls back to default', () async {
      final container = createContainer(
        mocks: mocks,
        vpnSettings: const VpnSettings(
          dnsProvider: DnsProvider.custom,
        ),
      );
      await waitForState(container);
      final notifier = container.read(vpnConnectionProvider.notifier);

      await notifier.connect(testServer());
      await Future<void>.delayed(const Duration(milliseconds: 50));

      expect(container.read(vpnConnectionProvider).value, isA<VpnConnected>());
      container.dispose();
    });
  });
}
