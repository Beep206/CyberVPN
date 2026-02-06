import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';
import 'package:cybervpn_mobile/features/servers/data/repositories/server_repository_impl.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/ping_service.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show serverRemoteDataSourceProvider, serverLocalDataSourceProvider;
import 'package:cybervpn_mobile/features/servers/data/datasources/favorites_local_datasource.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

// ---------------------------------------------------------------------------
// Enums & State
// ---------------------------------------------------------------------------

/// How the server list should be sorted.
enum SortMode { recommended, countryName, latency, load }

/// Immutable state for the server list screen.
class ServerListState {
  const ServerListState({
    this.servers = const [],
    this.sortMode = SortMode.recommended,
    this.filterCountry,
    this.filterProtocol,
    this.isRefreshing = false,
    this.favoriteServerIds = const [],
  });

  final List<ServerEntity> servers;
  final SortMode sortMode;
  final String? filterCountry;
  final VpnProtocol? filterProtocol;
  final bool isRefreshing;

  /// Ordered list of favorite server IDs (persisted locally).
  final List<String> favoriteServerIds;

  /// Convenience getter for the filtered + sorted view of servers.
  List<ServerEntity> get filteredServers {
    var result = List<ServerEntity>.from(servers);

    // Apply country filter.
    if (filterCountry != null && filterCountry!.isNotEmpty) {
      result = result
          .where((ServerEntity s) => s.countryCode == filterCountry)
          .toList();
    }

    // Apply protocol filter.
    if (filterProtocol != null) {
      result = result
          .where((ServerEntity s) => s.protocol == filterProtocol!.name)
          .toList();
    }

    // Apply sort.
    switch (sortMode) {
      case SortMode.recommended:
        result.sort((ServerEntity a, ServerEntity b) {
          if (a.isAvailable != b.isAvailable) {
            return a.isAvailable ? -1 : 1;
          }
          final pingA = a.ping ?? 9999;
          final pingB = b.ping ?? 9999;
          if (pingA != pingB) return pingA.compareTo(pingB);
          final loadA = a.load ?? 100.0;
          final loadB = b.load ?? 100.0;
          return loadA.compareTo(loadB);
        });
      case SortMode.countryName:
        result.sort((ServerEntity a, ServerEntity b) =>
            a.countryName.compareTo(b.countryName));
      case SortMode.latency:
        result.sort((ServerEntity a, ServerEntity b) {
          final pingA = a.ping ?? 9999;
          final pingB = b.ping ?? 9999;
          return pingA.compareTo(pingB);
        });
      case SortMode.load:
        result.sort((ServerEntity a, ServerEntity b) {
          final loadA = a.load ?? 100.0;
          final loadB = b.load ?? 100.0;
          return loadA.compareTo(loadB);
        });
    }

    return result;
  }

  ServerListState copyWith({
    List<ServerEntity>? servers,
    SortMode? sortMode,
    String? Function()? filterCountry,
    VpnProtocol? Function()? filterProtocol,
    bool? isRefreshing,
    List<String>? favoriteServerIds,
  }) {
    return ServerListState(
      servers: servers ?? this.servers,
      sortMode: sortMode ?? this.sortMode,
      filterCountry:
          filterCountry != null ? filterCountry() : this.filterCountry,
      filterProtocol:
          filterProtocol != null ? filterProtocol() : this.filterProtocol,
      isRefreshing: isRefreshing ?? this.isRefreshing,
      favoriteServerIds: favoriteServerIds ?? this.favoriteServerIds,
    );
  }
}

// ---------------------------------------------------------------------------
// Dependency providers
// ---------------------------------------------------------------------------

/// Provides the [ServerRepository] lazily via ref.watch.
final serverRepositoryProvider = Provider<ServerRepository>((ref) {
  return ServerRepositoryImpl(
    remoteDataSource: ref.watch(serverRemoteDataSourceProvider),
    localDataSource: ref.watch(serverLocalDataSourceProvider),
  );
});

/// Singleton [PingService] instance.
final pingServiceProvider = Provider<PingService>((ref) {
  final service = PingService();
  ref.onDispose(service.dispose);
  return service;
});

/// Provider for [FavoritesLocalDatasource].
///
/// Requires [SharedPreferences] to be available. Use
/// [sharedPreferencesProvider] to supply the instance.
final favoritesLocalDatasourceProvider =
    Provider<FavoritesLocalDatasource>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return FavoritesLocalDatasource(prefs);
});

// ---------------------------------------------------------------------------
// ServerListNotifier
// ---------------------------------------------------------------------------

class ServerListNotifier extends AsyncNotifier<ServerListState> {
  StreamSubscription<ServerStatusChanged>? _webSocketSubscription;

  @override
  Future<ServerListState> build() async {
    // Load favorite IDs from local storage.
    final favoritesDs = ref.read(favoritesLocalDatasourceProvider);
    final favoriteIds = await favoritesDs.getFavoriteIds();

    // Fetch servers on initial build.
    final servers = await _fetchServers();

    // Mark servers that are in the favorites list.
    final serversWithFavorites = _applyFavoriteFlags(servers, favoriteIds);

    // Trigger ping test for initial load (fire-and-forget).
    _triggerPingTest(serversWithFavorites);

    // Listen to WebSocket server status change events.
    _listenToWebSocketEvents();

    // Clean up subscription when provider is disposed.
    ref.onDispose(_dispose);

    return ServerListState(
      servers: serversWithFavorites,
      favoriteServerIds: favoriteIds,
    );
  }

  // ---- Public methods ----

  /// Fetch servers from the repository.
  Future<void> fetchServers() async {
    state = const AsyncLoading<ServerListState>();
    state = await AsyncValue.guard(() async {
      final servers = await _fetchServers();
      final current = state.value ?? const ServerListState();
      final serversWithFavorites =
          _applyFavoriteFlags(servers, current.favoriteServerIds);
      return current.copyWith(servers: serversWithFavorites);
    });
  }

  /// Change the sort mode.
  void sortBy(SortMode mode) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData<ServerListState>(current.copyWith(sortMode: mode));
  }

  /// Filter by country code. Pass `null` to clear.
  void filterByCountry(String? countryCode) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData<ServerListState>(
        current.copyWith(filterCountry: () => countryCode));
  }

  /// Filter by VPN protocol. Pass `null` to clear.
  void filterByProtocol(VpnProtocol? protocol) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData<ServerListState>(
        current.copyWith(filterProtocol: () => protocol));
  }

  /// Toggle a server's favorite status.
  ///
  /// Persists the change locally via [FavoritesLocalDatasource] and also
  /// notifies the remote repository.
  Future<void> toggleFavorite(String serverId) async {
    final current = state.value;
    if (current == null) return;

    final favoritesDs = ref.read(favoritesLocalDatasourceProvider);
    final repo = ref.read(serverRepositoryProvider);

    final isFavorite = current.favoriteServerIds.contains(serverId);
    List<String> updatedIds;

    if (isFavorite) {
      // Remove from favorites.
      await favoritesDs.removeFavorite(serverId);
      updatedIds = List<String>.from(current.favoriteServerIds)
        ..remove(serverId);
    } else {
      // Add to favorites (respects max limit).
      final added = await favoritesDs.addFavorite(serverId);
      if (!added) {
        // Limit reached - state unchanged; caller should show SnackBar.
        return;
      }
      updatedIds = List<String>.from(current.favoriteServerIds)
        ..add(serverId);
    }

    // Also notify remote repository (ignore Result; fire-and-forget).
    final _ = await repo.toggleFavorite(serverId);

    final updatedServers = current.servers.map((ServerEntity s) {
      if (s.id == serverId) return s.copyWith(isFavorite: !s.isFavorite);
      return s;
    }).toList();

    state = AsyncData<ServerListState>(current.copyWith(
      servers: updatedServers,
      favoriteServerIds: updatedIds,
    ));
  }

  /// Reorder favorites. Matches [ReorderableListView] onReorder signature.
  ///
  /// [oldIndex] and [newIndex] use the ReorderableListView convention where
  /// [newIndex] is already adjusted for forward moves by the framework.
  Future<void> reorderFavorites(int oldIndex, int newIndex) async {
    final current = state.value;
    if (current == null) return;

    final favoritesDs = ref.read(favoritesLocalDatasourceProvider);
    await favoritesDs.reorderFavorites(oldIndex, newIndex);

    // Rebuild the in-memory ordered list.
    final ids = List<String>.from(current.favoriteServerIds);
    // Apply the same reorder logic as ReorderableListView:
    final adjustedNewIndex = newIndex > oldIndex ? newIndex - 1 : newIndex;
    final item = ids.removeAt(oldIndex);
    ids.insert(adjustedNewIndex, item);

    state = AsyncData<ServerListState>(
        current.copyWith(favoriteServerIds: ids));
  }

  /// Pull-to-refresh handler.
  Future<void> refresh() async {
    final current = state.value;
    if (current == null) return;

    state = AsyncData<ServerListState>(
        current.copyWith(isRefreshing: true));

    try {
      final servers = await _fetchServers();
      final serversWithFavorites =
          _applyFavoriteFlags(servers, current.favoriteServerIds);
      final refreshed = current.copyWith(
        servers: serversWithFavorites,
        isRefreshing: false,
      );
      state = AsyncData<ServerListState>(refreshed);

      // Re-run pings after refresh.
      _triggerPingTest(serversWithFavorites);
    } catch (e, st) {
      state = AsyncError<ServerListState>(e, st);
    }
  }

  // ---- Private helpers ----

  Future<List<ServerEntity>> _fetchServers() async {
    final repo = ref.read(serverRepositoryProvider);
    final result = await repo.getServers();
    return switch (result) {
      Success(:final data) => data,
      Failure(:final failure) => throw failure,
    };
  }

  /// Applies the `isFavorite` flag to servers based on the persisted IDs.
  List<ServerEntity> _applyFavoriteFlags(
    List<ServerEntity> servers,
    List<String> favoriteIds,
  ) {
    final favoriteSet = favoriteIds.toSet();
    return servers.map((ServerEntity s) {
      final shouldBeFavorite = favoriteSet.contains(s.id);
      if (s.isFavorite != shouldBeFavorite) {
        return s.copyWith(isFavorite: shouldBeFavorite);
      }
      return s;
    }).toList();
  }

  void _triggerPingTest(List<ServerEntity> servers) {
    final pingService = ref.read(pingServiceProvider);
    pingService.pingAllConcurrent(servers).then((Map<String, int> results) {
      final current = state.value;
      if (current == null) return;

      final updated = current.servers.map((ServerEntity s) {
        final latency = results[s.id];
        if (latency != null) return s.copyWith(ping: latency);
        return s;
      }).toList();

      state = AsyncData<ServerListState>(current.copyWith(servers: updated));
    });
  }

  /// Listens to WebSocket server_status_changed events and updates
  /// the corresponding server in the list.
  void _listenToWebSocketEvents() {
    try {
      final client = ref.read(webSocketClientProvider);
      _webSocketSubscription = client.serverStatusEvents.listen(
        _onServerStatusChanged,
        onError: (Object e) {
          AppLogger.error('WebSocket server status stream error', error: e);
        },
      );
    } catch (e) {
      AppLogger.error(
        'Failed to listen to WebSocket server status stream',
        error: e,
      );
    }
  }

  /// Handles incoming server_status_changed WebSocket events.
  ///
  /// Updates the server's status in the local list and notifies listeners.
  void _onServerStatusChanged(ServerStatusChanged event) {
    final current = state.value;
    if (current == null) return;

    // Find the server by ID.
    final serverIndex =
        current.servers.indexWhere((s) => s.id == event.serverId);

    if (serverIndex == -1) {
      AppLogger.warning(
        'Received server_status_changed for unknown server: ${event.serverId}',
      );
      return;
    }

    // Parse the new status. Valid values: 'online', 'offline', 'maintenance'.
    // Map them to the `isAvailable` field.
    final isAvailable = event.status == 'online';

    // Update the server entity.
    final updatedServers = List<ServerEntity>.from(current.servers);
    updatedServers[serverIndex] =
        updatedServers[serverIndex].copyWith(isAvailable: isAvailable);

    // Notify listeners.
    state = AsyncData<ServerListState>(
      current.copyWith(servers: updatedServers),
    );

    AppLogger.info(
      'Server ${event.serverId} status updated to ${event.status} (isAvailable: $isAvailable)',
    );
  }

  /// Disposes resources when the provider is no longer used.
  void _dispose() {
    _webSocketSubscription?.cancel();
  }
}

// ---------------------------------------------------------------------------
// Main provider
// ---------------------------------------------------------------------------

final serverListProvider =
    AsyncNotifierProvider<ServerListNotifier, ServerListState>(
  ServerListNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Servers grouped by country code.
final groupedByCountryProvider =
    Provider<Map<String, List<ServerEntity>>>((ref) {
  final asyncState = ref.watch(serverListProvider);
  final serverState = asyncState.value;
  if (serverState == null) return {};

  final grouped = <String, List<ServerEntity>>{};
  for (final ServerEntity server in serverState.filteredServers) {
    grouped.putIfAbsent(server.countryCode, () => []).add(server);
  }
  return grouped;
});

/// Only favorite servers, ordered by the persisted favorite order.
final favoriteServersProvider = Provider<List<ServerEntity>>((ref) {
  final asyncState = ref.watch(serverListProvider);
  final serverState = asyncState.value;
  if (serverState == null) return [];

  final favoriteIds = serverState.favoriteServerIds;
  final serverMap = <String, ServerEntity>{};
  for (final s in serverState.servers) {
    serverMap[s.id] = s;
  }

  // Return in persisted order, filtering out any IDs not in current server list.
  final ordered = <ServerEntity>[];
  for (final id in favoriteIds) {
    final server = serverMap[id];
    if (server != null) {
      ordered.add(server);
    }
  }
  return ordered;
});

/// The single best recommended server (lowest ping, available, non-premium).
final recommendedServerProvider = Provider<ServerEntity?>((ref) {
  final asyncState = ref.watch(serverListProvider);
  final serverState = asyncState.value;
  if (serverState == null) return null;

  final available = serverState.servers
      .where((ServerEntity s) => s.isAvailable && !s.isPremium)
      .toList();
  if (available.isEmpty) return null;

  available.sort((ServerEntity a, ServerEntity b) {
    final pingA = a.ping ?? 9999;
    final pingB = b.ping ?? 9999;
    return pingA.compareTo(pingB);
  });

  return available.first;
});

/// Look up a single server by ID.
final serverByIdProvider =
    Provider.family<ServerEntity?, String>((ref, String id) {
  final asyncState = ref.watch(serverListProvider);
  final serverState = asyncState.value;
  if (serverState == null) return null;

  try {
    return serverState.servers.firstWhere((ServerEntity s) => s.id == id);
  } catch (_) {
    return null;
  }
});
