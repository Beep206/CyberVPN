import 'package:drift/drift.dart';

import 'package:cybervpn_mobile/core/data/database/app_database.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';

/// Maps between Drift data classes and domain entities.
///
/// Provides conversion methods for:
/// - [Profile] (Drift) ↔ [VpnProfile] (domain)
/// - [ProfileConfig] (Drift) ↔ [ProfileServer] (domain)
/// - [ProfileServer] → [VpnConfigEntity] (adapter for the VPN engine)
class ProfileMapper {
  const ProfileMapper._();

  // ── Profile: Drift → Domain ───────────────────────────────────────

  /// Converts a Drift [Profile] row + its configs to a domain [VpnProfile].
  ///
  /// The [configs] list is mapped to [ProfileServer] entities and
  /// attached to the resulting profile.
  static VpnProfile toDomain(Profile row, List<ProfileConfig> configs) {
    final servers = configs.map(configToDomain).toList();

    return switch (row.type) {
      ProfileType.remote => VpnProfile.remote(
          id: row.id,
          name: row.name,
          subscriptionUrl: row.subscriptionUrl ?? '',
          isActive: row.isActive,
          sortOrder: row.sortOrder,
          createdAt: row.createdAt,
          lastUpdatedAt: row.lastUpdatedAt,
          uploadBytes: row.uploadBytes,
          downloadBytes: row.downloadBytes,
          totalBytes: row.totalBytes,
          expiresAt: row.expiresAt,
          updateIntervalMinutes: row.updateIntervalMinutes,
          supportUrl: row.supportUrl,
          testUrl: row.testUrl,
          servers: servers,
        ),
      ProfileType.local => VpnProfile.local(
          id: row.id,
          name: row.name,
          isActive: row.isActive,
          sortOrder: row.sortOrder,
          createdAt: row.createdAt,
          lastUpdatedAt: row.lastUpdatedAt,
          servers: servers,
        ),
    };
  }

  /// Converts a Drift [ProfileConfig] row to a domain [ProfileServer].
  static ProfileServer configToDomain(ProfileConfig row) {
    return ProfileServer(
      id: row.id,
      profileId: row.profileId,
      name: row.name,
      serverAddress: row.serverAddress,
      port: row.port,
      protocol: _parseProtocol(row.protocol),
      configData: row.configData,
      remark: row.remark,
      isFavorite: row.isFavorite,
      sortOrder: row.sortOrder,
      latencyMs: row.latencyMs,
      createdAt: row.createdAt,
    );
  }

  // ── Domain → Drift Companion ──────────────────────────────────────

  /// Converts a domain [VpnProfile] to a Drift [ProfilesCompanion] for insert.
  static ProfilesCompanion toCompanion(VpnProfile profile) {
    return switch (profile) {
      RemoteVpnProfile() => ProfilesCompanion.insert(
          id: profile.id,
          name: profile.name,
          type: ProfileType.remote,
          subscriptionUrl: Value(profile.subscriptionUrl),
          isActive: Value(profile.isActive),
          sortOrder: Value(profile.sortOrder),
          createdAt: profile.createdAt,
          lastUpdatedAt: Value(profile.lastUpdatedAt),
          uploadBytes: Value(profile.uploadBytes),
          downloadBytes: Value(profile.downloadBytes),
          totalBytes: Value(profile.totalBytes),
          expiresAt: Value(profile.expiresAt),
          updateIntervalMinutes: Value(profile.updateIntervalMinutes),
          supportUrl: Value(profile.supportUrl),
          testUrl: Value(profile.testUrl),
        ),
      LocalVpnProfile() => ProfilesCompanion.insert(
          id: profile.id,
          name: profile.name,
          type: ProfileType.local,
          isActive: Value(profile.isActive),
          sortOrder: Value(profile.sortOrder),
          createdAt: profile.createdAt,
          lastUpdatedAt: Value(profile.lastUpdatedAt),
        ),
    };
  }

  /// Converts a domain [ProfileServer] to a Drift [ProfileConfigsCompanion].
  static ProfileConfigsCompanion serverToCompanion(ProfileServer server) {
    return ProfileConfigsCompanion.insert(
      id: server.id,
      profileId: server.profileId,
      name: server.name,
      serverAddress: server.serverAddress,
      port: server.port,
      protocol: server.protocol.name,
      configData: server.configData,
      remark: Value(server.remark),
      isFavorite: Value(server.isFavorite),
      sortOrder: Value(server.sortOrder),
      latencyMs: Value(server.latencyMs),
      createdAt: server.createdAt,
    );
  }

  // ── Adapter for VPN Engine ────────────────────────────────────────

  /// Converts a [ProfileServer] to a [VpnConfigEntity] for the VPN engine.
  ///
  /// The VPN engine works with [VpnConfigEntity] objects. This adapter
  /// allows servers from the profile system to be used with the engine.
  static VpnConfigEntity toVpnConfigEntity(ProfileServer server) {
    return VpnConfigEntity(
      id: server.id,
      name: server.name,
      serverAddress: server.serverAddress,
      port: server.port,
      protocol: server.protocol,
      configData: server.configData,
      remark: server.remark,
      isFavorite: server.isFavorite,
    );
  }

  // ── Helpers ───────────────────────────────────────────────────────

  /// Parses a protocol string to [VpnProtocol], defaulting to [VpnProtocol.vless].
  static VpnProtocol _parseProtocol(String protocol) {
    return switch (protocol.toLowerCase()) {
      'vless' => VpnProtocol.vless,
      'vmess' => VpnProtocol.vmess,
      'trojan' => VpnProtocol.trojan,
      'ss' || 'shadowsocks' => VpnProtocol.shadowsocks,
      _ => VpnProtocol.vless,
    };
  }
}
