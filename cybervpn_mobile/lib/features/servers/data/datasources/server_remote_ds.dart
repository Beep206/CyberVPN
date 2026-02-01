import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';

abstract class ServerRemoteDataSource {
  Future<List<ServerEntity>> fetchServers();
  Future<ServerEntity> fetchServerById(String id);
}

class ServerRemoteDataSourceImpl implements ServerRemoteDataSource {
  final ApiClient _apiClient;

  ServerRemoteDataSourceImpl(this._apiClient);

  @override
  Future<List<ServerEntity>> fetchServers() async {
    final response = await _apiClient.get('/servers');
    final data = response.data as List<dynamic>;
    return data.map((json) => _mapToEntity(json as Map<String, dynamic>)).toList();
  }

  @override
  Future<ServerEntity> fetchServerById(String id) async {
    final response = await _apiClient.get('/servers/$id');
    return _mapToEntity(response.data as Map<String, dynamic>);
  }

  ServerEntity _mapToEntity(Map<String, dynamic> json) {
    return ServerEntity(
      id: json['id'] as String,
      name: json['name'] as String,
      countryCode: json['country_code'] as String,
      countryName: json['country_name'] as String,
      city: json['city'] as String,
      address: json['address'] as String,
      port: json['port'] as int,
      protocol: json['protocol'] as String? ?? 'vless',
      isAvailable: json['is_available'] as bool? ?? true,
      isPremium: json['is_premium'] as bool? ?? false,
    );
  }
}
