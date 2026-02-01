import 'dart:io';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_remote_ds.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_local_ds.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';

class ServerRepositoryImpl with NetworkErrorHandler implements ServerRepository {
  final ServerRemoteDataSource _remoteDataSource;
  final ServerLocalDataSource _localDataSource;
  final NetworkInfo _networkInfo;

  ServerRepositoryImpl({
    required ServerRemoteDataSource remoteDataSource,
    required ServerLocalDataSource localDataSource,
    required NetworkInfo networkInfo,
  })  : _remoteDataSource = remoteDataSource,
        _localDataSource = localDataSource,
        _networkInfo = networkInfo;

  @override
  Future<List<ServerEntity>> getServers() async {
    final cached = _localDataSource.getCachedServers();
    if (cached != null) return _applyFavorites(cached);
    if (!await _networkInfo.isConnected) {
      throw const NetworkFailure(message: 'No internet connection');
    }
    final servers = await _remoteDataSource.fetchServers();
    await _localDataSource.cacheServers(servers);
    return _applyFavorites(servers);
  }

  @override
  Future<ServerEntity> getServerById(String id) async {
    return _remoteDataSource.fetchServerById(id);
  }

  @override
  Future<List<ServerEntity>> getServersByCountry(String countryCode) async {
    final servers = await getServers();
    return servers.where((s) => s.countryCode == countryCode).toList();
  }

  @override
  Future<List<ServerEntity>> getFavoriteServers() async {
    final favoriteIds = _localDataSource.getFavoriteIds();
    final servers = await getServers();
    return servers.where((s) => favoriteIds.contains(s.id)).toList();
  }

  @override
  Future<void> toggleFavorite(String serverId) async {
    final favorites = _localDataSource.getFavoriteIds();
    if (favorites.contains(serverId)) {
      favorites.remove(serverId);
    } else {
      favorites.add(serverId);
    }
    await _localDataSource.cacheFavorites(favorites);
  }

  @override
  Future<int> pingServer(String serverAddress) async {
    try {
      final stopwatch = Stopwatch()..start();
      final result = await InternetAddress.lookup(serverAddress);
      stopwatch.stop();
      if (result.isNotEmpty) return stopwatch.elapsedMilliseconds;
      return -1;
    } catch (_) {
      return -1;
    }
  }

  @override
  Future<ServerEntity> getBestServer() async {
    final servers = await getServers();
    final available = servers.where((s) => s.isAvailable && !s.isPremium).toList();
    if (available.isEmpty) throw const ServerFailure(message: 'No servers available');
    int bestPing = 999999;
    ServerEntity best = available.first;
    for (final server in available.take(5)) {
      final ping = await pingServer(server.address);
      if (ping > 0 && ping < bestPing) {
        bestPing = ping;
        best = server;
      }
    }
    return best;
  }

  List<ServerEntity> _applyFavorites(List<ServerEntity> servers) {
    final favoriteIds = _localDataSource.getFavoriteIds();
    return servers.map((s) => s.copyWith(isFavorite: favoriteIds.contains(s.id))).toList();
  }
}
