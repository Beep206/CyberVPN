import 'dart:io';

import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/data/database/app_database.dart';
import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/data/services/app_reset_service.dart';
import '../../../../helpers/fakes/fake_secure_storage.dart';

void main() {
  late SharedPreferences prefs;
  late FakeSecureStorage secureStorage;
  late AppDatabase database;
  late Directory tempDir;
  late LogFileStore logFileStore;
  late AppResetService service;

  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'settings.themeMode': 'cyberpunk',
      'config_import.imported_configs': '[{"id":"cfg-1"}]',
      'cached_servers': '[{"id":"srv-1"}]',
      'quick_setup_completed': true,
    });
    prefs = await SharedPreferences.getInstance();
    secureStorage = FakeSecureStorage();
    database = AppDatabase(NativeDatabase.memory());
    tempDir = await Directory.systemTemp.createTemp('app-reset-service-test');
    logFileStore = LogFileStore(supportDirectoryLoader: () async => tempDir);
    service = AppResetService(
      sharedPreferences: prefs,
      secureStorage: secureStorage,
      database: database,
      logFileStore: logFileStore,
    );

    secureStorage.seed({
      SecureStorageWrapper.accessTokenKey: 'access-token',
      SecureStorageWrapper.refreshTokenKey: 'refresh-token',
      SecureStorageWrapper.deviceIdKey: 'device-123',
      'oauth_state': 'csrf-state',
      'encrypted_field_master_key': 'master-key',
    });

    final now = DateTime(2026, 4, 17, 12);
    await database.into(database.profiles).insert(
      ProfilesCompanion.insert(
        id: 'profile-1',
        name: 'Remote Profile',
        type: ProfileType.remote,
        createdAt: now,
      ),
    );
    await database.into(database.profileConfigs).insert(
      ProfileConfigsCompanion.insert(
        id: 'config-1',
        profileId: 'profile-1',
        name: 'Server A',
        serverAddress: 'example.com',
        port: 443,
        protocol: 'vless',
        configData: '{"id":"secret"}',
        createdAt: now,
      ),
    );

    await logFileStore.record(
      LogEntry(
        timestamp: DateTime.utc(2026, 4, 17, 10),
        level: 'info',
        message: 'Access entry',
      ),
    );
    await logFileStore.record(
      LogEntry(
        timestamp: DateTime.utc(2026, 4, 17, 10, 5),
        level: 'info',
        message: 'Subscription entry',
        category: 'subscription.refresh',
      ),
      category: 'subscription.refresh',
    );
    await logFileStore.writeXrayRuntimeSnapshot(
      '{"outbounds":[{"settings":{"vnext":[{"users":[{"id":"secret-id"}]}]}}]}',
      remark: 'Remote Profile',
    );

    AppLogger.clearLogs();
    AppLogger.resetConfiguration();
    AppLogger.info('Buffered reset candidate');
  });

  tearDown(() async {
    AppLogger.clearLogs();
    AppLogger.resetConfiguration();
    await database.close();
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('performFullReset clears prefs, secure storage, db, and logs', () async {
    expect(prefs.getKeys(), isNotEmpty);
    expect(await logFileStore.listFiles(), isNotEmpty);
    expect(AppLogger.entryCount, 1);

    await service.performFullReset();

    expect(prefs.getKeys(), isEmpty);
    expect(await secureStorage.getAccessToken(), isNull);
    expect(await secureStorage.getRefreshToken(), isNull);
    expect(await secureStorage.read(key: 'oauth_state'), isNull);
    expect(
      await secureStorage.read(key: 'encrypted_field_master_key'),
      isNull,
    );
    expect(await secureStorage.read(key: SecureStorageWrapper.deviceIdKey), 'device-123');

    final profiles = await database.select(database.profiles).get();
    final configs = await database.select(database.profileConfigs).get();
    expect(profiles, isEmpty);
    expect(configs, isEmpty);
    expect(await logFileStore.listFiles(), isEmpty);
    expect(AppLogger.entryCount, 0);
  });
}
