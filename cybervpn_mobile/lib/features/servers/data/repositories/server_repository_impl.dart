import 'dart:io';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
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
  Future<Result<List<ServerEntity>>> getServers() async {
    try {
      final cached = await _localDataSource.getCachedServers();
      if (cached != null) return Success(await _applyFavorites(cached));
      if (!await _networkInfo.isConnected) {
        return const Failure(NetworkFailure(message: 'No internet connection'));
      }
      final servers = await _remoteDataSource.fetchServers();
      await _localDataSource.cacheServers(servers);
      return Success(await _applyFavorites(servers));
    } on Exception catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<ServerEntity>> getServerById(String id) async {
    try {
      final server = await _remoteDataSource.fetchServerById(id);
      return Success(server);
    } on Exception catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<List<ServerEntity>>> getServersByCountry(String countryCode) async {
    final serversResult = await getServers();
    return serversResult.map(
      (servers) => servers.where((s) => s.countryCode == countryCode).toList(),
    );
  }

  @override
  Future<Result<List<ServerEntity>>> getFavoriteServers() async {
    final favoriteIds = await _localDataSource.getFavoriteIds();
    final serversResult = await getServers();
    return serversResult.map(
      (servers) => servers.where((s) => favoriteIds.contains(s.id)).toList(),
    );
  }

  @override
  Future<Result<void>> toggleFavorite(String serverId) async {
    try {
      final favorites = (await _localDataSource.getFavoriteIds()).toList();
      if (favorites.contains(serverId)) {
        favorites.remove(serverId);
      } else {
        favorites.add(serverId);
      }
      await _localDataSource.cacheFavorites(favorites);
      return const Success(null);
    } on Exception catch (e) {
      return Failure(CacheFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<int>> pingServer(String serverAddress) async {
    try {
      final stopwatch = Stopwatch()..start();
      final result = await InternetAddress.lookup(serverAddress);
      stopwatch.stop();
      if (result.isNotEmpty) return Success(stopwatch.elapsedMilliseconds);
      return const Success(-1);
    } catch (_) {
      return const Success(-1);
    }
  }

  @override
  Future<Result<ServerEntity>> getBestServer() async {
    final serversResult = await getServers();
    return switch (serversResult) {
      Failure(:final failure) => Failure(failure),
      Success(:final data) => await _findBestServer(data),
    };
  }

  Future<Result<ServerEntity>> _findBestServer(List<ServerEntity> servers) async {
    final available = servers.where((s) => s.isAvailable && !s.isPremium).toList();
    if (available.isEmpty) {
      return const Failure(ServerFailure(message: 'No servers available'));
    }
    int bestPing = 999999;
    ServerEntity best = available.first;
    for (final server in available.take(5)) {
      final pingResult = await pingServer(server.address);
      final ping = pingResult.dataOrNull ?? -1;
      if (ping > 0 && ping < bestPing) {
        bestPing = ping;
        best = server;
      }
    }
    return Success(best);
  }

  Future<List<ServerEntity>> _applyFavorites(List<ServerEntity> servers) async {
    final favoriteIds = await _localDataSource.getFavoriteIds();
    return servers.map((s) => s.copyWith(isFavorite: favoriteIds.contains(s.id))).toList();
  }
}
