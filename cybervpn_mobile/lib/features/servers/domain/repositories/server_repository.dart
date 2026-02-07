import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_remote_ds.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';

abstract class ServerRepository {
  Future<Result<List<ServerEntity>>> getServers({
    CacheStrategy strategy = CacheStrategy.staleWhileRevalidate,
  });
  Future<Result<PaginatedResponse<ServerEntity>>> getServersPaginated({
    int offset = 0,
    int limit = 50,
  });
  Future<Result<ServerEntity>> getServerById(String id);
  Future<Result<List<ServerEntity>>> getServersByCountry(String countryCode);
  Future<Result<List<ServerEntity>>> getFavoriteServers();
  Future<Result<void>> toggleFavorite(String serverId);
  Future<Result<int>> pingServer(String serverAddress);
  Future<Result<ServerEntity>> getBestServer();
}
