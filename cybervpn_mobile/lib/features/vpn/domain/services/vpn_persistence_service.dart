import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show secureStorageProvider;
import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';

const _lastServerKey = 'last_connected_server';
const _lastProtocolKey = 'last_connected_protocol';

/// Manages persistence of VPN connection state (last server, protocol).
class VpnPersistenceService {
  final SecureStorageWrapper _storage;

  VpnPersistenceService({required SecureStorageWrapper storage})
      : _storage = storage;

  Future<void> persistLastConnection(
    ServerEntity server,
    VpnProtocol protocol,
  ) async {
    try {
      final serverJson = jsonEncode(server.toJson());
      await _storage.write(key: _lastServerKey, value: serverJson);
      await _storage.write(key: _lastProtocolKey, value: protocol.name);
    } catch (e) {
      AppLogger.warning('Failed to persist last connection', error: e);
    }
  }

  Future<ServerEntity?> loadLastServer() async {
    try {
      final raw = await _storage.read(key: _lastServerKey);
      if (raw == null) return null;
      final map = jsonDecode(raw) as Map<String, dynamic>;
      return ServerEntity.fromJson(map);
    } catch (e) {
      AppLogger.warning('Failed to load last server', error: e);
      return null;
    }
  }

  Future<void> clearPersistedConnection() async {
    try {
      await _storage.delete(key: _lastServerKey);
      await _storage.delete(key: _lastProtocolKey);
    } catch (e) {
      AppLogger.warning('Failed to clear persisted connection', error: e);
    }
  }
}

final vpnPersistenceServiceProvider = Provider<VpnPersistenceService>((ref) {
  return VpnPersistenceService(storage: ref.watch(secureStorageProvider));
});
