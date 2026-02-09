import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';

/// Response wrapper for paginated API endpoints.
class PaginatedResponse<T> {
  final List<T> items;
  final int total;
  final int offset;
  final int limit;

  const PaginatedResponse({
    required this.items,
    required this.total,
    required this.offset,
    required this.limit,
  });

  bool get hasMore => offset + items.length < total;
}

abstract class ServerRemoteDataSource {
  Future<List<ServerEntity>> fetchServers();
  Future<PaginatedResponse<ServerEntity>> fetchServersPaginated({
    int offset = 0,
    int limit = 50,
  });
  Future<ServerEntity> fetchServerById(String id);
}

class ServerRemoteDataSourceImpl implements ServerRemoteDataSource {
  final ApiClient _apiClient;

  ServerRemoteDataSourceImpl(this._apiClient);

  @override
  Future<List<ServerEntity>> fetchServers() async {
    final response = await _apiClient.get<Map<String, dynamic>>('/servers');
    final body = response.data;
    final items =
        (body?['items'] as List<dynamic>?) ??
        (body?['data'] as List<dynamic>?) ??
        <dynamic>[];
    return items
        .map((json) => _mapToEntity(json as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<PaginatedResponse<ServerEntity>> fetchServersPaginated({
    int offset = 0,
    int limit = 50,
  }) async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      '/servers',
      queryParameters: {'offset': offset, 'limit': limit},
    );
    final body = response.data!;
    final data =
        (body['items'] as List<dynamic>?) ??
        (body['data'] as List<dynamic>?) ??
        [];
    final total = body['total'] as int? ?? data.length;

    return PaginatedResponse(
      items: data
          .map((json) => _mapToEntity(json as Map<String, dynamic>))
          .toList(),
      total: total,
      offset: offset,
      limit: limit,
    );
  }

  @override
  Future<ServerEntity> fetchServerById(String id) async {
    final response = await _apiClient.get<Map<String, dynamic>>('/servers/$id');
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw FormatException('Expected Map response, got ${data.runtimeType}');
    }
    return _mapToEntity(data);
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
