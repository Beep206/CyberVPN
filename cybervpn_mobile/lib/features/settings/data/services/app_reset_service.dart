import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/data/database/app_database.dart';
import 'package:cybervpn_mobile/core/services/log_file_store.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Explicit contract for the destructive `Full App Reset` flow.
class FullAppResetScope {
  const FullAppResetScope({
    required this.clearsSettings,
    required this.clearsImportedConfigs,
    required this.clearsVpnProfiles,
    required this.clearsSubscriptionMetadata,
    required this.clearsLogs,
    required this.clearsLocalCaches,
    required this.clearsAuthSessionData,
    required this.preservesDeviceIdentity,
  });

  final bool clearsSettings;
  final bool clearsImportedConfigs;
  final bool clearsVpnProfiles;
  final bool clearsSubscriptionMetadata;
  final bool clearsLogs;
  final bool clearsLocalCaches;
  final bool clearsAuthSessionData;
  final bool preservesDeviceIdentity;
}

/// Service responsible for destructive app-reset flows.
class AppResetService {
  AppResetService({
    required SharedPreferences sharedPreferences,
    required SecureStorageWrapper secureStorage,
    required AppDatabase database,
    required LogFileStore logFileStore,
  }) : _sharedPreferences = sharedPreferences,
       _secureStorage = secureStorage,
       _database = database,
       _logFileStore = logFileStore;

  static const fullResetScope = FullAppResetScope(
    clearsSettings: true,
    clearsImportedConfigs: true,
    clearsVpnProfiles: true,
    clearsSubscriptionMetadata: true,
    clearsLogs: true,
    clearsLocalCaches: true,
    clearsAuthSessionData: true,
    preservesDeviceIdentity: true,
  );

  final SharedPreferences _sharedPreferences;
  final SecureStorageWrapper _secureStorage;
  final AppDatabase _database;
  final LogFileStore _logFileStore;

  /// Removes all local app data covered by [fullResetScope].
  Future<void> performFullReset() async {
    await _clearVpnProfileDatabase();
    await _sharedPreferences.clear();
    await _secureStorage.wipeAll(preserveDeviceId: true);
    AppLogger.clearLogs();
    await _logFileStore.clearPersistentLogs();
  }

  Future<void> _clearVpnProfileDatabase() async {
    await _database.transaction(() async {
      await _database.delete(_database.profileConfigs).go();
      await _database.delete(_database.profiles).go();
    });
  }
}
