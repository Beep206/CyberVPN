import 'dart:async';
import 'dart:convert';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/vpn_engine_datasource.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_state_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/connection_stats_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

class VpnRepositoryImpl implements VpnRepository {
  final VpnEngineDatasource _engine;
  final LocalStorageWrapper _localStorage;
  final SecureStorageWrapper _secureStorage;

  // NON-SENSITIVE: VPN config metadata - SharedPreferences is sufficient
  static const String _lastConfigKey = 'last_vpn_config_meta';
  static const String _savedConfigsKey = 'saved_vpn_configs_meta';

  // SENSITIVE: VPN config credentials - must use SecureStorage for encryption at rest
  static const String _lastConfigDataKey = 'last_vpn_config_data';
  static const String _savedConfigDataPrefix = 'vpn_config_data_';

  // Migration flag to track if old insecure configs have been migrated
  static const String _migrationCompleteKey = 'vpn_config_migration_v1_complete';

  // Old keys for migration
  static const String _oldLastConfigKey = 'last_vpn_config';
  static const String _oldSavedConfigsKey = 'saved_vpn_configs';

  VpnRepositoryImpl({
    required VpnEngineDatasource engine,
    required LocalStorageWrapper localStorage,
    required SecureStorageWrapper secureStorage,
  })  : _engine = engine,
        _localStorage = localStorage,
        _secureStorage = secureStorage {
    // Perform migration on initialization
    _migrateOldConfigsIfNeeded();
  }

  @override
  Future<void> connect(VpnConfigEntity config) async {
    await _engine.initialize();
    await _engine.connect(config.configData, remark: config.name);
    AppLogger.info('VPN connected to ${config.name}');
  }

  @override
  Future<void> disconnect() async {
    await _engine.disconnect();
  }

  @override
  Future<bool> get isConnected => _engine.isConnected;

  @override
  Stream<ConnectionStateEntity> get connectionStateStream {
    return _engine.statusStream.map((status) => ConnectionStateEntity(
      status: status.state == 'CONNECTED' ? VpnConnectionStatus.connected : VpnConnectionStatus.disconnected,
    ));
  }

  @override
  Stream<ConnectionStatsEntity> get connectionStatsStream {
    return _engine.statusStream.map((status) => const ConnectionStatsEntity());
  }

  @override
  Future<VpnConfigEntity?> getLastConfig() async {
    // NON-SENSITIVE: Read metadata from SharedPreferences
    final metaJsonStr = await _localStorage.getString(_lastConfigKey);
    if (metaJsonStr == null) return null;

    final meta = jsonDecode(metaJsonStr) as Map<String, dynamic>;

    // SENSITIVE: Read config data from SecureStorage
    final configData = await _secureStorage.read(key: _lastConfigDataKey);
    if (configData == null) {
      AppLogger.warning('VPN config metadata exists but config data is missing');
      return null;
    }

    return VpnConfigEntity(
      id: meta['id'] as String,
      name: meta['name'] as String,
      serverAddress: meta['serverAddress'] as String,
      port: meta['port'] as int,
      protocol: VpnProtocol.values.firstWhere(
        (e) => e.name == meta['protocol'],
        orElse: () => VpnProtocol.vless,
      ),
      configData: configData,
    );
  }

  @override
  Future<void> saveConfig(VpnConfigEntity config) async {
    // NON-SENSITIVE: Store metadata in SharedPreferences
    await _localStorage.setString(
      _lastConfigKey,
      jsonEncode({
        'id': config.id,
        'name': config.name,
        'serverAddress': config.serverAddress,
        'port': config.port,
        'protocol': config.protocol.name,
      }),
    );

    // SENSITIVE: Store config data in SecureStorage for encryption at rest
    await _secureStorage.write(
      key: _lastConfigDataKey,
      value: config.configData,
    );

    AppLogger.info('VPN config saved securely for ${config.name}');
  }

  @override
  Future<List<VpnConfigEntity>> getSavedConfigs() async {
    // NON-SENSITIVE: Read metadata list from SharedPreferences
    final metaJsonStr = await _localStorage.getString(_savedConfigsKey);
    if (metaJsonStr == null) return [];

    final metaList = jsonDecode(metaJsonStr) as List<dynamic>;
    final configs = <VpnConfigEntity>[];

    for (final metaItem in metaList) {
      final meta = metaItem as Map<String, dynamic>;
      final configId = meta['id'] as String;

      // SENSITIVE: Read config data from SecureStorage
      final configData = await _secureStorage.read(
        key: '$_savedConfigDataPrefix$configId',
      );

      if (configData != null) {
        configs.add(VpnConfigEntity(
          id: configId,
          name: meta['name'] as String,
          serverAddress: meta['serverAddress'] as String,
          port: meta['port'] as int,
          protocol: VpnProtocol.values.firstWhere(
            (e) => e.name == meta['protocol'],
            orElse: () => VpnProtocol.vless,
          ),
          configData: configData,
        ));
      } else {
        AppLogger.warning('Skipping config $configId: metadata exists but data is missing');
      }
    }

    return configs;
  }

  @override
  Future<void> deleteConfig(String id) async {
    // Get current configs
    final configs = await getSavedConfigs();
    configs.removeWhere((c) => c.id == id);

    // NON-SENSITIVE: Update metadata list in SharedPreferences
    await _localStorage.setString(
      _savedConfigsKey,
      jsonEncode(configs.map((c) => {
            'id': c.id,
            'name': c.name,
            'serverAddress': c.serverAddress,
            'port': c.port,
            'protocol': c.protocol.name,
          }).toList()),
    );

    // SENSITIVE: Delete config data from SecureStorage
    await _secureStorage.delete(key: '$_savedConfigDataPrefix$id');

    AppLogger.info('VPN config deleted: $id');
  }

  // ── Migration Logic ──────────────────────────────────────────────────────

  /// Migrates VPN configs from old insecure SharedPreferences storage to
  /// secure split storage (metadata in SharedPreferences, credentials in SecureStorage).
  ///
  /// This migration runs automatically on first app launch after the update.
  /// Old keys are deleted after successful migration.
  Future<void> _migrateOldConfigsIfNeeded() async {
    try {
      // Check if migration already completed
      final migrationComplete = await _localStorage.getBool(_migrationCompleteKey);
      if (migrationComplete == true) {
        return;
      }

      AppLogger.info('Starting VPN config migration to secure storage...');

      // Migrate last config
      await _migrateLastConfig();

      // Migrate saved configs
      await _migrateSavedConfigs();

      // Mark migration as complete
      await _localStorage.setBool(_migrationCompleteKey, true);

      AppLogger.info('VPN config migration completed successfully');
    } catch (e) {
      AppLogger.error('VPN config migration failed', error: e);
      // Don't throw - app should still function even if migration fails
      // Old configs will be lost, but new configs will be stored securely
    }
  }

  Future<void> _migrateLastConfig() async {
    final oldJsonStr = await _localStorage.getString(_oldLastConfigKey);
    if (oldJsonStr == null) return;

    try {
      final old = jsonDecode(oldJsonStr) as Map<String, dynamic>;

      // Extract metadata
      final meta = {
        'id': old['id'],
        'name': old['name'],
        'serverAddress': old['serverAddress'],
        'port': old['port'],
        'protocol': old['protocol'],
      };

      // Store metadata in new location
      await _localStorage.setString(_lastConfigKey, jsonEncode(meta));

      // Store config data securely
      await _secureStorage.write(
        key: _lastConfigDataKey,
        value: old['configData'] as String,
      );

      // Delete old insecure data
      await _localStorage.remove(_oldLastConfigKey);

      AppLogger.info('Migrated last VPN config to secure storage');
    } catch (e) {
      AppLogger.error('Failed to migrate last VPN config', error: e);
    }
  }

  Future<void> _migrateSavedConfigs() async {
    final oldJsonStr = await _localStorage.getString(_oldSavedConfigsKey);
    if (oldJsonStr == null) return;

    try {
      final oldList = jsonDecode(oldJsonStr) as List<dynamic>;
      final metaList = <Map<String, dynamic>>[];

      for (final oldItem in oldList) {
        final old = oldItem as Map<String, dynamic>;
        final configId = old['id'] as String;

        // Extract metadata
        final meta = {
          'id': configId,
          'name': old['name'],
          'serverAddress': old['serverAddress'],
          'port': old['port'],
          'protocol': old['protocol'],
        };
        metaList.add(meta);

        // Store config data securely
        await _secureStorage.write(
          key: '$_savedConfigDataPrefix$configId',
          value: old['configData'] as String,
        );
      }

      // Store metadata list in new location
      await _localStorage.setString(_savedConfigsKey, jsonEncode(metaList));

      // Delete old insecure data
      await _localStorage.remove(_oldSavedConfigsKey);

      AppLogger.info('Migrated ${metaList.length} saved VPN configs to secure storage');
    } catch (e) {
      AppLogger.error('Failed to migrate saved VPN configs', error: e);
    }
  }
}
