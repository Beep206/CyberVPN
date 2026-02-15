import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/domain/repositories/config_import_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';

/// Service that migrates legacy single-config imported data into the
/// multi-profile system.
///
/// Reads all [ImportedConfig] entries from [ConfigImportRepository],
/// maps them to [ProfileServer] objects, creates a single "CyberVPN"
/// local profile, sets it as active, and marks migration complete via
/// a SharedPreferences flag.
///
/// Idempotent: checks [LocalStorageWrapper.profileMigrationV1CompleteKey]
/// before running. Safe to call multiple times.
class LegacyProfileMigrationService {
  LegacyProfileMigrationService({
    required ConfigImportRepository configImportRepository,
    required ProfileRepository profileRepository,
    required LocalStorageWrapper localStorage,
  })  : _configImportRepo = configImportRepository,
        _profileRepo = profileRepository,
        _localStorage = localStorage;

  final ConfigImportRepository _configImportRepo;
  final ProfileRepository _profileRepo;
  final LocalStorageWrapper _localStorage;

  /// Runs the migration. Returns `true` if migration was performed,
  /// `false` if already completed or no data to migrate.
  Future<bool> migrate() async {
    // 1. Check if already migrated.
    final alreadyDone = await _localStorage.getBool(
      LocalStorageWrapper.profileMigrationV1CompleteKey,
    );
    if (alreadyDone == true) {
      AppLogger.debug(
        'Legacy profile migration already complete',
        category: 'migration',
      );
      return false;
    }

    try {
      // 2. Read legacy imported configs.
      final legacyConfigs = await _configImportRepo.getImportedConfigs();

      if (legacyConfigs.isEmpty) {
        AppLogger.info(
          'No legacy configs to migrate — marking complete',
          category: 'migration',
        );
        await _markComplete();
        return false;
      }

      // 3. Check if profiles already exist (someone may have created
      //    profiles before migration ran — e.g. fresh install with new UI).
      final countResult = await _profileRepo.count();
      final existingCount = switch (countResult) {
        Success(:final data) => data,
        Failure() => 0,
      };

      if (existingCount > 0) {
        AppLogger.info(
          'Profiles already exist ($existingCount) — skipping migration',
          category: 'migration',
        );
        await _markComplete();
        return false;
      }

      // 4. Map ImportedConfig → ProfileServer.
      final servers = legacyConfigs
          .asMap()
          .entries
          .map((entry) => _mapToProfileServer(entry.value, entry.key))
          .toList();

      // 5. Create local profile with all servers.
      final result = await _profileRepo.addLocalProfile(
        'CyberVPN',
        servers,
      );

      switch (result) {
        case Success(:final data):
          // 6. Set as active profile.
          await _profileRepo.setActive(data.id);
          AppLogger.info(
            'Legacy migration complete: created profile "${data.name}" '
            'with ${servers.length} servers',
            category: 'migration',
          );
        case Failure(:final failure):
          AppLogger.error(
            'Legacy migration failed to create profile: ${failure.message}',
            category: 'migration',
          );
          // Don't mark complete — allow retry on next startup.
          return false;
      }

      // 7. Mark migration complete.
      await _markComplete();
      return true;
    } catch (e, st) {
      AppLogger.error(
        'Legacy profile migration failed',
        error: e,
        stackTrace: st,
        category: 'migration',
      );
      // Don't mark complete — allow retry on next startup.
      return false;
    }
  }

  /// Converts a legacy [ImportedConfig] to a [ProfileServer].
  ProfileServer _mapToProfileServer(ImportedConfig config, int index) {
    return ProfileServer(
      // ID and profileId are overwritten by the repository — use placeholders.
      id: 'legacy-${config.id}',
      profileId: '',
      name: config.name,
      serverAddress: config.serverAddress,
      port: config.port,
      protocol: _parseProtocol(config.protocol),
      configData: config.rawUri,
      sortOrder: index,
      createdAt: config.importedAt,
    );
  }

  /// Maps a protocol string from [ImportedConfig] to [VpnProtocol].
  VpnProtocol _parseProtocol(String protocol) {
    return switch (protocol.toLowerCase()) {
      'vless' => VpnProtocol.vless,
      'vmess' => VpnProtocol.vmess,
      'trojan' => VpnProtocol.trojan,
      'ss' || 'shadowsocks' => VpnProtocol.shadowsocks,
      _ => VpnProtocol.vless, // default fallback
    };
  }

  Future<void> _markComplete() async {
    await _localStorage.setBool(
      LocalStorageWrapper.profileMigrationV1CompleteKey,
      true,
    );
  }
}
