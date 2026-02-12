import 'dart:async';
import 'dart:convert';

import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_engine_datasource.dart';
import 'package:cybervpn_mobile/features/vpn/data/repositories/vpn_repository_impl.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:flutter_v2ray_plus/flutter_v2ray.dart' show VlessStatus;
import 'package:flutter_test/flutter_test.dart';

// =============================================================================
// Mocks
// =============================================================================

class _MockVpnEngine implements VpnEngineDatasource {
  bool initialized = false;
  bool connected = false;
  bool shouldFailConnect = false;
  bool shouldFailDisconnect = false;
  int initializeCallCount = 0;
  int connectCallCount = 0;

  final StreamController<VlessStatus> _statusController =
      StreamController<VlessStatus>.broadcast();

  @override
  Future<void> initialize({
    required String providerBundleIdentifier,
    required String groupIdentifier,
    String notificationIconResourceType = 'mipmap',
    String notificationIconResourceName = 'ic_launcher',
  }) async {
    initializeCallCount++;
    initialized = true;
  }

  @override
  Future<void> connect(String config, {String? remark, List<String>? blockedApps}) async {
    connectCallCount++;
    if (shouldFailConnect) throw Exception('Engine connect failed');
    connected = true;
  }

  @override
  Future<void> disconnect() async {
    if (shouldFailDisconnect) throw Exception('Engine disconnect failed');
    connected = false;
  }

  @override
  bool get isConnected => connected;

  @override
  Stream<VlessStatus> get statusStream => _statusController.stream;

  void emitStatus(VlessStatus status) => _statusController.add(status);
  @override
  void dispose() => _statusController.close();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockLocalStorage implements LocalStorageWrapper {
  final Map<String, dynamic> _store = {};

  @override
  Future<void> setString(String key, String value) async => _store[key] = value;

  @override
  Future<String?> getString(String key) async => _store[key] as String?;

  @override
  Future<void> setBool(String key, bool value) async => _store[key] = value;

  @override
  Future<bool?> getBool(String key) async => _store[key] as bool?;

  @override
  Future<void> remove(String key) async => _store.remove(key);

  @override
  Future<void> clear() async => _store.clear();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MockSecureStorage implements SecureStorageWrapper {
  final Map<String, String> _store = {};

  @override
  Future<String?> read({required String key}) async => _store[key];

  @override
  Future<void> write({required String key, required String value}) async {
    _store[key] = value;
  }

  @override
  Future<void> delete({required String key}) async => _store.remove(key);

  @override
  Future<void> deleteAll() async => _store.clear();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// =============================================================================
// Helpers
// =============================================================================

VpnConfigEntity _testConfig({
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

// =============================================================================
// Tests
// =============================================================================

void main() {
  late _MockVpnEngine engine;
  late _MockLocalStorage localStorage;
  late _MockSecureStorage secureStorage;
  late VpnRepositoryImpl repo;

  setUp(() {
    engine = _MockVpnEngine();
    localStorage = _MockLocalStorage();
    secureStorage = _MockSecureStorage();
    repo = VpnRepositoryImpl(
      engine: engine,
      localStorage: localStorage,
      secureStorage: secureStorage,
    );
  });

  // ── saveConfig / getLastConfig ─────────────────────────────────────────────

  group('saveConfig + getLastConfig', () {
    test('saveConfig splits metadata (SharedPrefs) and data (SecureStorage)', () async {
      final config = _testConfig();
      final result = await repo.saveConfig(config);
      expect(result, isA<Success<void>>());

      // Metadata in SharedPreferences.
      final metaJson = await localStorage.getString('last_vpn_config_meta');
      expect(metaJson, isNotNull);
      final meta = jsonDecode(metaJson!) as Map<String, dynamic>;
      expect(meta['id'], equals('cfg-1'));
      expect(meta['name'], equals('Test Config'));
      expect(meta['serverAddress'], equals('1.2.3.4'));
      expect(meta['port'], equals(443));
      expect(meta['protocol'], equals('vless'));

      // Sensitive data NOT in metadata.
      expect(meta.containsKey('configData'), isFalse);

      // Config data in SecureStorage.
      final secureData = await secureStorage.read(key: 'last_vpn_config_data');
      expect(secureData, equals('vless://test-config-data'));
    });

    test('getLastConfig reconstructs entity from split storage', () async {
      final config = _testConfig();
      await repo.saveConfig(config);

      final result = await repo.getLastConfig();
      expect(result, isA<Success<VpnConfigEntity?>>());

      final retrieved = (result as Success<VpnConfigEntity?>).data;
      expect(retrieved, isNotNull);
      expect(retrieved!.id, equals('cfg-1'));
      expect(retrieved.name, equals('Test Config'));
      expect(retrieved.configData, equals('vless://test-config-data'));
      expect(retrieved.protocol, equals(VpnProtocol.vless));
    });

    test('getLastConfig returns null when no config saved', () async {
      final result = await repo.getLastConfig();
      expect(result, isA<Success<VpnConfigEntity?>>());
      expect((result as Success).data, isNull);
    });

    test('getLastConfig returns null when metadata exists but data missing', () async {
      // Write metadata without corresponding secure data.
      await localStorage.setString(
        'last_vpn_config_meta',
        jsonEncode({
          'id': 'cfg-orphan',
          'name': 'Orphan',
          'serverAddress': '5.6.7.8',
          'port': 443,
          'protocol': 'vless',
        }),
      );

      final result = await repo.getLastConfig();
      expect((result as Success).data, isNull);
    });
  });

  // ── getSavedConfigs / deleteConfig ─────────────────────────────────────────

  group('getSavedConfigs', () {
    test('returns empty list when no configs saved', () async {
      final result = await repo.getSavedConfigs();
      expect(result, isA<Success<List<VpnConfigEntity>>>());
      expect((result as Success).data, isEmpty);
    });
  });

  group('deleteConfig', () {
    test('removes config data from SecureStorage', () async {
      // Manually seed a saved config.
      const configId = 'cfg-to-delete';
      final metaList = [
        {
          'id': configId,
          'name': 'Delete Me',
          'serverAddress': '9.9.9.9',
          'port': 443,
          'protocol': 'vless',
        },
      ];
      await localStorage.setString('saved_vpn_configs_meta', jsonEncode(metaList));
      await secureStorage.write(
        key: 'vpn_config_data_$configId',
        value: 'vless://delete-me',
      );

      // Verify it exists.
      var result = await repo.getSavedConfigs();
      expect((result as Success<List<VpnConfigEntity>>).data, hasLength(1));

      // Delete.
      await repo.deleteConfig(configId);

      // Verify deleted.
      result = await repo.getSavedConfigs();
      expect((result as Success<List<VpnConfigEntity>>).data, isEmpty);

      // SecureStorage data should be removed.
      final secureData =
          await secureStorage.read(key: 'vpn_config_data_$configId');
      expect(secureData, isNull);
    });
  });

  // ── Migration Logic ────────────────────────────────────────────────────────
  //
  // Migration tests use FRESH mocks to avoid the migration flag being set
  // by the setUp() repo constructor.

  group('migration', () {
    test('migrates old last config to split storage', () async {
      final freshLocal = _MockLocalStorage();
      final freshSecure = _MockSecureStorage();

      // Seed old format BEFORE creating repo.
      final oldConfig = {
        'id': 'old-1',
        'name': 'Old Config',
        'serverAddress': '10.0.0.1',
        'port': 443,
        'protocol': 'vless',
        'configData': 'vless://old-config-data',
      };
      await freshLocal.setString('last_vpn_config', jsonEncode(oldConfig));

      // Create repo (migration runs in constructor).
      final migrationRepo = VpnRepositoryImpl(
        engine: engine,
        localStorage: freshLocal,
        secureStorage: freshSecure,
      );

      // Read the migrated config.
      final result = await migrationRepo.getLastConfig();
      final config = (result as Success<VpnConfigEntity?>).data;
      expect(config, isNotNull);
      expect(config!.id, equals('old-1'));
      expect(config.configData, equals('vless://old-config-data'));

      // Old key should be removed.
      expect(await freshLocal.getString('last_vpn_config'), isNull);
    });

    test('migrates old saved configs list to split storage', () async {
      final freshLocal = _MockLocalStorage();
      final freshSecure = _MockSecureStorage();

      final oldConfigs = [
        {
          'id': 'saved-1',
          'name': 'Saved One',
          'serverAddress': '10.0.0.2',
          'port': 443,
          'protocol': 'vless',
          'configData': 'vless://saved-one',
        },
        {
          'id': 'saved-2',
          'name': 'Saved Two',
          'serverAddress': '10.0.0.3',
          'port': 443,
          'protocol': 'vmess',
          'configData': 'vmess://saved-two',
        },
      ];
      await freshLocal.setString('saved_vpn_configs', jsonEncode(oldConfigs));

      final migrationRepo = VpnRepositoryImpl(
        engine: engine,
        localStorage: freshLocal,
        secureStorage: freshSecure,
      );

      final result = await migrationRepo.getSavedConfigs();
      final configs = (result as Success<List<VpnConfigEntity>>).data;
      expect(configs, hasLength(2));
      expect(configs[0].id, equals('saved-1'));
      expect(configs[0].configData, equals('vless://saved-one'));
      expect(configs[1].id, equals('saved-2'));

      // Old key should be removed.
      expect(await freshLocal.getString('saved_vpn_configs'), isNull);
    });

    test('runs only once (migration flag prevents re-migration)', () async {
      final freshLocal = _MockLocalStorage();
      final freshSecure = _MockSecureStorage();

      await freshLocal.setString(
        'last_vpn_config',
        jsonEncode({
          'id': 'old-2',
          'name': 'Should Not Migrate Twice',
          'serverAddress': '10.0.0.4',
          'port': 443,
          'protocol': 'vless',
          'configData': 'vless://should-not-migrate-twice',
        }),
      );

      // First repo triggers migration.
      VpnRepositoryImpl(
        engine: engine,
        localStorage: freshLocal,
        secureStorage: freshSecure,
      );
      // Wait for async migration.
      await Future<void>.delayed(const Duration(milliseconds: 50));

      // Clear secure storage to simulate "post-migration" state.
      await freshSecure.delete(key: 'last_vpn_config_data');

      // Second repo should NOT re-migrate (flag is set).
      final secondRepo = VpnRepositoryImpl(
        engine: engine,
        localStorage: freshLocal,
        secureStorage: freshSecure,
      );

      final result = await secondRepo.getLastConfig();
      // Data was cleared from secure storage and migration won't run again.
      expect((result as Success).data, isNull);
    });

    test('handles missing old data gracefully', () async {
      final freshLocal = _MockLocalStorage();
      final freshSecure = _MockSecureStorage();

      // No old data at all — migration should be a no-op.
      final migrationRepo = VpnRepositoryImpl(
        engine: engine,
        localStorage: freshLocal,
        secureStorage: freshSecure,
      );

      final result = await migrationRepo.getLastConfig();
      expect((result as Success).data, isNull);

      // Migration flag should still be set.
      expect(await freshLocal.getBool('vpn_config_migration_v1_complete'), isTrue);
    });
  });

  // ── connect() / disconnect() / isConnected ────────────────────────────────

  group('connect()', () {
    test('initializes engine once then calls engine.connect()', () async {
      final config = _testConfig();
      expect(engine.initializeCallCount, equals(0));

      final result1 = await repo.connect(config);
      expect(result1, isA<Success<void>>());
      expect(engine.initializeCallCount, equals(1));
      expect(engine.connectCallCount, equals(1));

      // Second connect should NOT re-initialize.
      await repo.connect(config);
      expect(engine.initializeCallCount, equals(1));
      expect(engine.connectCallCount, equals(2));
    });

    test('returns Success on success', () async {
      final result = await repo.connect(_testConfig());
      expect(result, isA<Success<void>>());
      expect(engine.connected, isTrue);
    });

    test('returns Failure(VpnFailure) on engine error', () async {
      engine.shouldFailConnect = true;
      final result = await repo.connect(_testConfig());
      expect(result, isA<Failure<void>>());
    });
  });

  group('disconnect()', () {
    test('calls engine.disconnect() and returns Success', () async {
      engine.connected = true;
      final result = await repo.disconnect();
      expect(result, isA<Success<void>>());
      expect(engine.connected, isFalse);
    });

    test('returns Failure on engine error', () async {
      engine.shouldFailDisconnect = true;
      final result = await repo.disconnect();
      expect(result, isA<Failure<void>>());
    });
  });

  group('isConnected', () {
    test('returns engine.isConnected value', () async {
      engine.connected = false;
      var result = await repo.isConnected;
      expect((result as Success<bool>).data, isFalse);

      engine.connected = true;
      result = await repo.isConnected;
      expect((result as Success<bool>).data, isTrue);
    });
  });

  // ── connectionStateStream ────────────────────────────────────────────────

  group('connectionStateStream', () {
    test('maps CONNECTED status to VpnConnectionStatus.connected', () async {
      final events = <ConnectionStateEntity>[];
      final sub = repo.connectionStateStream.listen(events.add);

      engine.emitStatus(VlessStatus(state: 'CONNECTED'));
      await Future<void>.delayed(const Duration(milliseconds: 20));

      expect(events, hasLength(1));
      expect(events[0].status, equals(VpnConnectionStatus.connected));
      await sub.cancel();
    });

    test('maps DISCONNECTED status to VpnConnectionStatus.disconnected', () async {
      final events = <ConnectionStateEntity>[];
      final sub = repo.connectionStateStream.listen(events.add);

      engine.emitStatus(VlessStatus(state: 'DISCONNECTED'));
      await Future<void>.delayed(const Duration(milliseconds: 20));

      expect(events, hasLength(1));
      expect(events[0].status, equals(VpnConnectionStatus.disconnected));
      await sub.cancel();
    });

    test('maps unknown engine states to disconnected', () async {
      final events = <ConnectionStateEntity>[];
      final sub = repo.connectionStateStream.listen(events.add);

      engine.emitStatus(VlessStatus(state: 'CONNECTING'));
      await Future<void>.delayed(const Duration(milliseconds: 20));

      expect(events, hasLength(1));
      // Non-connected states map to disconnected.
      expect(events[0].status, equals(VpnConnectionStatus.disconnected));
      await sub.cancel();
    });
  });
}
