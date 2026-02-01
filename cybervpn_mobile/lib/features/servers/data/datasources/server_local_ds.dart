import 'dart:convert';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';

abstract class ServerLocalDataSource {
  Future<void> cacheServers(List<ServerEntity> servers);
  List<ServerEntity>? getCachedServers();
  Future<void> cacheFavorites(List<String> serverIds);
  List<String> getFavoriteIds();
  Future<void> clearCache();
}

class ServerLocalDataSourceImpl implements ServerLocalDataSource {
  final LocalStorageWrapper _localStorage;

  static const String _serversKey = 'cached_servers';
  static const String _favoritesKey = 'favorite_servers';
  static const String _cacheTimestampKey = 'servers_cache_timestamp';
  static const int _cacheValidityMinutes = 30;

  ServerLocalDataSourceImpl(this._localStorage);

  @override
  Future<void> cacheServers(List<ServerEntity> servers) async {
    final jsonList = servers.map((s) => {
      'id': s.id, 'name': s.name, 'countryCode': s.countryCode,
      'countryName': s.countryName, 'city': s.city, 'address': s.address,
      'port': s.port, 'protocol': s.protocol, 'isAvailable': s.isAvailable,
      'isPremium': s.isPremium,
    }).toList();
    await _localStorage.setString(_serversKey, jsonEncode(jsonList));
    await _localStorage.setString(_cacheTimestampKey, DateTime.now().toIso8601String());
  }

  @override
  List<ServerEntity>? getCachedServers() {
    final timestampStr = _localStorage.getString(_cacheTimestampKey);
    if (timestampStr != null) {
      final timestamp = DateTime.parse(timestampStr);
      if (DateTime.now().difference(timestamp).inMinutes > _cacheValidityMinutes) return null;
    }
    final jsonStr = _localStorage.getString(_serversKey);
    if (jsonStr == null) return null;
    final jsonList = jsonDecode(jsonStr) as List<dynamic>;
    return jsonList.map((json) {
      final m = json as Map<String, dynamic>;
      return ServerEntity(
        id: m['id'] as String, name: m['name'] as String,
        countryCode: m['countryCode'] as String, countryName: m['countryName'] as String,
        city: m['city'] as String, address: m['address'] as String,
        port: m['port'] as int, protocol: m['protocol'] as String? ?? 'vless',
        isAvailable: m['isAvailable'] as bool? ?? true, isPremium: m['isPremium'] as bool? ?? false,
      );
    }).toList();
  }

  @override
  Future<void> cacheFavorites(List<String> serverIds) async {
    await _localStorage.setStringList(_favoritesKey, serverIds);
  }

  @override
  List<String> getFavoriteIds() {
    return _localStorage.getStringList(_favoritesKey) ?? [];
  }

  @override
  Future<void> clearCache() async {
    await _localStorage.remove(_serversKey);
    await _localStorage.remove(_cacheTimestampKey);
  }
}
