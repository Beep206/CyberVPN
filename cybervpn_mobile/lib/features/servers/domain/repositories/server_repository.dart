import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';

abstract class ServerRepository {
  Future<List<ServerEntity>> getServers();
  Future<ServerEntity> getServerById(String id);
  Future<List<ServerEntity>> getServersByCountry(String countryCode);
  Future<List<ServerEntity>> getFavoriteServers();
  Future<void> toggleFavorite(String serverId);
  Future<int> pingServer(String serverAddress);
  Future<ServerEntity> getBestServer();
}
