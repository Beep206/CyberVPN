import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show listEquals, mapEquals;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/server_remote_ds.dart'
    show PaginatedResponse;
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show
        serverRepositoryProvider,
        pingServiceProvider,
        favoritesLocalDatasourceProvider;
import 'package:cybervpn_mobile/core/domain/vpn_protocol.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/profile_aware_server_list.dart';

part 'server_list_provider.freezed.dart';

// ---------------------------------------------------------------------------
// Enums & State
// ---------------------------------------------------------------------------

/// How the server list should be sorted.
enum SortMode { recommended, countryName, latency, load }

class ServerListEntryViewModel {
  const ServerListEntryViewModel.remote({required this.serverId})
    : isCustom = false,
      configId = null,
      customServer = null;

  const ServerListEntryViewModel.custom({
    required this.serverId,
    required this.customServer,
    required this.configId,
  }) : isCustom = true;

  final String serverId;
  final bool isCustom;
  final String? configId;

  /// Snapshot used only for custom imported servers that do not exist in the
  /// main server provider graph.
  final ServerEntity? customServer;

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ServerListEntryViewModel &&
            serverId == other.serverId &&
            isCustom == other.isCustom &&
            configId == other.configId &&
            customServer == other.customServer;
  }

  @override
  int get hashCode => Object.hash(serverId, isCustom, configId, customServer);
}

class ServerListGroupViewModel {
  const ServerListGroupViewModel({
    required this.countryCode,
    required this.countryName,
    required this.entries,
  });

  final String countryCode;
  final String countryName;
  final List<ServerListEntryViewModel> entries;

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ServerListGroupViewModel &&
            countryCode == other.countryCode &&
            countryName == other.countryName &&
            listEquals(entries, other.entries);
  }

  @override
  int get hashCode =>
      Object.hash(countryCode, countryName, Object.hashAll(entries));
}

class ServerListViewModel {
  const ServerListViewModel({
    required this.searchQuery,
    required this.favoriteServerIds,
    required this.groupedServers,
  });

  final String searchQuery;
  final List<String> favoriteServerIds;
  final List<ServerListGroupViewModel> groupedServers;

  bool get hasActiveSearch => searchQuery.isNotEmpty;

  bool get hasResults =>
      favoriteServerIds.isNotEmpty || groupedServers.isNotEmpty;

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ServerListViewModel &&
            searchQuery == other.searchQuery &&
            listEquals(favoriteServerIds, other.favoriteServerIds) &&
            listEquals(groupedServers, other.groupedServers);
  }

  @override
  int get hashCode => Object.hash(
    searchQuery,
    Object.hashAll(favoriteServerIds),
    Object.hashAll(groupedServers),
  );
}

class ServerSearchQueryNotifier extends Notifier<String> {
  @override
  String build() => '';

  void setQuery(String value) => state = value;

  void clear() => state = '';
}

class ServerPingResultsNotifier extends Notifier<Map<String, int>> {
  @override
  Map<String, int> build() => const <String, int>{};

  void mergeResults(Map<String, int> results) {
    if (results.isEmpty) return;

    final next = Map<String, int>.from(state);
    var changed = false;

    for (final entry in results.entries) {
      if (next[entry.key] != entry.value) {
        next[entry.key] = entry.value;
        changed = true;
      }
    }

    if (!changed) return;
    state = Map<String, int>.unmodifiable(next);
  }

  void pruneTo(Iterable<String> serverIds) {
    final allowedIds = serverIds.toSet();
    final next = <String, int>{
      for (final entry in state.entries)
        if (allowedIds.contains(entry.key)) entry.key: entry.value,
    };

    if (mapEquals(next, state)) return;
    state = Map<String, int>.unmodifiable(next);
  }
}

/// Immutable state for the server list screen.
@freezed
sealed class ServerListState with _$ServerListState {
  const ServerListState._();

  const factory ServerListState({
    @Default([]) List<ServerEntity> servers,
    @Default(SortMode.recommended) SortMode sortMode,
    String? filterCountry,
    VpnProtocol? filterProtocol,
    @Default(false) bool isRefreshing,

    /// Ordered list of favorite server IDs (persisted locally).
    @Default([]) List<String> favoriteServerIds,

    /// Total server count from the API (for pagination).
    @Default(0) int totalServerCount,

    /// Whether more pages are available.
    @Default(true) bool hasMore,

    /// Whether a page is currently loading.
    @Default(false) bool isLoadingMore,
  }) = _ServerListState;

  /// Per-instance cache for [filteredServers] using identity-based [Expando].
  /// Avoids recomputation when the same state instance is read multiple times.
  static final Expando<List<ServerEntity>> _filteredCache =
      Expando<List<ServerEntity>>('filteredServers');

  /// Convenience getter for the filtered + sorted view of servers.
  /// Result is memoized per instance via [Expando].
  List<ServerEntity> get filteredServers {
    final cached = _filteredCache[this];
    if (cached != null) return cached;

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
        result.sort(
          (ServerEntity a, ServerEntity b) =>
              a.countryName.compareTo(b.countryName),
        );
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

    _filteredCache[this] = result;
    return result;
  }
}

// ---------------------------------------------------------------------------
// ServerListNotifier
// ---------------------------------------------------------------------------

class ServerListNotifier extends AsyncNotifier<ServerListState> {
  StreamSubscription<ServerStatusChanged>? _webSocketSubscription;

  /// CancelToken for in-flight API requests. Cancelled when provider disposes.
  CancelToken _cancelToken = CancelToken();

  static const _pageSize = 50;

  @override
  Future<ServerListState> build() async {
    // Create a fresh CancelToken for this build cycle.
    _cancelToken = CancelToken();
    ref.onDispose(() => _cancelToken.cancel('Provider disposed'));

    // Load favorite IDs from local storage.
    final favoritesDs = ref.read(favoritesLocalDatasourceProvider);
    final favoriteIds = await favoritesDs.getFavoriteIds();

    // Fetch first page of servers.
    final page = await _fetchServersPaginated(offset: 0, limit: _pageSize);

    // Mark servers that are in the favorites list.
    final serversWithFavorites = _applyFavoriteFlags(page.items, favoriteIds);
    _syncPingResults(serversWithFavorites, replaceExisting: true);

    // Trigger ping test for initial load (fire-and-forget).
    _triggerPingTest(serversWithFavorites);

    // Listen to WebSocket server status change events.
    _listenToWebSocketEvents();

    // Clean up subscription when provider is disposed.
    ref.onDispose(_dispose);

    return ServerListState(
      servers: serversWithFavorites,
      favoriteServerIds: favoriteIds,
      totalServerCount: page.total,
      hasMore: page.hasMore,
    );
  }

  // ---- Public methods ----

  /// Fetch servers from the repository.
  Future<void> fetchServers() async {
    final previousState = state.value;
    state = const AsyncLoading<ServerListState>();
    state = await AsyncValue.guard(() async {
      final servers = await _fetchServers();
      final current = previousState ?? const ServerListState();
      final serversWithFavorites = _applyFavoriteFlags(
        servers,
        current.favoriteServerIds,
      );
      _syncPingResults(serversWithFavorites, replaceExisting: true);
      _triggerPingTest(serversWithFavorites);
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
      current.copyWith(filterCountry: countryCode),
    );
  }

  /// Filter by VPN protocol. Pass `null` to clear.
  void filterByProtocol(VpnProtocol? protocol) {
    final current = state.value;
    if (current == null) return;
    state = AsyncData<ServerListState>(
      current.copyWith(filterProtocol: protocol),
    );
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
      updatedIds = List<String>.from(current.favoriteServerIds)..add(serverId);
    }

    // Also notify remote repository (ignore Result; fire-and-forget).
    unawaited(repo.toggleFavorite(serverId));

    final updatedServers = current.servers.map((ServerEntity s) {
      if (s.id == serverId) return s.copyWith(isFavorite: !s.isFavorite);
      return s;
    }).toList();

    state = AsyncData<ServerListState>(
      current.copyWith(servers: updatedServers, favoriteServerIds: updatedIds),
    );
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
      current.copyWith(favoriteServerIds: ids),
    );
  }

  /// Pull-to-refresh handler. Resets pagination to first page.
  Future<void> refresh() async {
    final current = state.value;
    if (current == null) return;

    state = AsyncData<ServerListState>(current.copyWith(isRefreshing: true));

    try {
      final page = await _fetchServersPaginated(offset: 0, limit: _pageSize);
      final serversWithFavorites = _applyFavoriteFlags(
        page.items,
        current.favoriteServerIds,
      );
      final refreshed = current.copyWith(
        servers: serversWithFavorites,
        isRefreshing: false,
        totalServerCount: page.total,
        hasMore: page.hasMore,
      );
      _syncPingResults(serversWithFavorites, replaceExisting: true);
      state = AsyncData<ServerListState>(refreshed);

      // Re-run pings after refresh.
      _triggerPingTest(serversWithFavorites);
    } catch (e, st) {
      state = AsyncError<ServerListState>(e, st);
    }
  }

  /// Load the next page of servers (infinite scroll).
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || current.isLoadingMore || !current.hasMore) return;

    state = AsyncData<ServerListState>(current.copyWith(isLoadingMore: true));

    try {
      final page = await _fetchServersPaginated(
        offset: current.servers.length,
        limit: _pageSize,
      );
      final newServers = _applyFavoriteFlags(
        page.items,
        current.favoriteServerIds,
      );
      final allServers = [...current.servers, ...newServers];
      _syncPingResults(allServers, replaceExisting: false);

      state = AsyncData<ServerListState>(
        current.copyWith(
          servers: allServers,
          totalServerCount: page.total,
          hasMore: page.hasMore,
          isLoadingMore: false,
        ),
      );

      // Ping new servers.
      _triggerPingTest(newServers);
    } catch (e, st) {
      AppLogger.error('Failed to load more servers', error: e, stackTrace: st);
      state = AsyncData<ServerListState>(
        current.copyWith(isLoadingMore: false),
      );
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

  Future<PaginatedResponse<ServerEntity>> _fetchServersPaginated({
    required int offset,
    required int limit,
  }) async {
    final repo = ref.read(serverRepositoryProvider);
    final result = await repo.getServersPaginated(offset: offset, limit: limit);
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
    final staleServers = servers
        .where((server) => !pingService.isFresh(server.id))
        .toList(growable: false);

    if (staleServers.isEmpty) {
      return;
    }

    unawaited(
      pingService.pingAllConcurrent(staleServers).then((
        Map<String, int> results,
      ) {
        ref.read(serverPingResultsProvider.notifier).mergeResults(results);
      }),
    );
  }

  void _syncPingResults(
    List<ServerEntity> servers, {
    required bool replaceExisting,
  }) {
    final pingService = ref.read(pingServiceProvider);
    final cachedPings = <String, int>{};

    for (final server in servers) {
      final ping = pingService.getLatency(server.id);
      if (ping != null && pingService.isFresh(server.id)) {
        cachedPings[server.id] = ping;
      }
    }

    final notifier = ref.read(serverPingResultsProvider.notifier);
    if (replaceExisting) {
      notifier.pruneTo(servers.map((server) => server.id));
    }
    notifier.mergeResults(cachedPings);
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
    final serverIndex = current.servers.indexWhere(
      (s) => s.id == event.serverId,
    );

    if (serverIndex == -1) {
      AppLogger.warning(
        'Received server_status_changed for unknown server: ${event.serverId}',
      );
      return;
    }

    // Parse the new status. Valid values: 'online', 'offline', 'maintenance'.
    // Map them to the `isAvailable` field.
    final isAvailable = event.status == 'online';
    if (current.servers[serverIndex].isAvailable == isAvailable) {
      return;
    }

    // Update the server entity.
    final updatedServers = List<ServerEntity>.from(current.servers);
    updatedServers[serverIndex] = updatedServers[serverIndex].copyWith(
      isAvailable: isAvailable,
    );

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
    unawaited(_webSocketSubscription?.cancel());
  }
}

// ---------------------------------------------------------------------------
// Main provider
// ---------------------------------------------------------------------------

final serverListProvider =
    AsyncNotifierProvider<ServerListNotifier, ServerListState>(
      ServerListNotifier.new,
    );

final serverPingResultsProvider =
    NotifierProvider<ServerPingResultsNotifier, Map<String, int>>(
      ServerPingResultsNotifier.new,
    );

final serverPingByIdProvider = Provider.family<int?, String>((ref, String id) {
  return ref.watch(serverPingResultsProvider.select((pings) => pings[id]));
});

// ---------------------------------------------------------------------------
// Derived providers
// ---------------------------------------------------------------------------

/// Filtered + sorted server list, derived from [profileAwareServerListProvider].
///
/// Riverpod auto-memoizes: downstream widgets only rebuild when the
/// filtered list actually changes.
final filteredServersProvider = Provider<List<ServerEntity>>((ref) {
  final asyncState = ref.watch(profileAwareServerListProvider);
  final serverState = asyncState.value;
  final pingResults = ref.watch(serverPingResultsProvider);
  if (serverState == null) return [];
  return _buildFilteredServers(serverState, pingResults);
});

final allServersWithPingProvider = Provider<List<ServerEntity>>((ref) {
  final asyncState = ref.watch(profileAwareServerListProvider);
  final serverState = asyncState.value;
  final pingResults = ref.watch(serverPingResultsProvider);
  if (serverState == null) {
    return const <ServerEntity>[];
  }

  return _applyPingResults(serverState.servers, pingResults);
});

/// Servers grouped by country code, derived from [filteredServersProvider].
final groupedByCountryProvider = Provider<Map<String, List<ServerEntity>>>((
  ref,
) {
  final servers = ref.watch(filteredServersProvider);

  final grouped = <String, List<ServerEntity>>{};
  for (final ServerEntity server in servers) {
    grouped.putIfAbsent(server.countryCode, () => []).add(server);
  }
  return grouped;
});

/// Only favorite servers, ordered by the persisted favorite order.
final favoriteServersProvider = Provider<List<ServerEntity>>((ref) {
  final asyncState = ref.watch(profileAwareServerListProvider);
  final serverState = asyncState.value;
  if (serverState == null) return [];

  final favoriteIds = serverState.favoriteServerIds;
  final serverMap = ref.watch(serverMapProvider);

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
  final servers = ref.watch(allServersWithPingProvider);
  if (servers.isEmpty) return null;

  final available = servers
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

final serverSearchQueryProvider =
    NotifierProvider<ServerSearchQueryNotifier, String>(
      ServerSearchQueryNotifier.new,
    );

String? _extractCountryCode(String name) {
  final countryPattern = RegExp(r'\b([A-Z]{2})\b');
  final match = countryPattern.firstMatch(name.toUpperCase());
  return match?.group(1);
}

ServerEntity _customConfigToServer(ImportedConfig config) {
  final countryCode = _extractCountryCode(config.name) ?? 'XX';
  return ServerEntity(
    id: config.id,
    name: config.name,
    countryCode: countryCode,
    countryName: countryCode == 'XX' ? 'Custom' : countryCode,
    city: config.serverAddress,
    address: config.serverAddress,
    port: config.port,
    protocol: config.protocol,
    isAvailable: config.isReachable ?? true,
  );
}

bool _matchesServerSearch(ServerEntity server, String normalizedQuery) {
  if (normalizedQuery.isEmpty) return true;

  return server.name.toLowerCase().contains(normalizedQuery) ||
      server.city.toLowerCase().contains(normalizedQuery) ||
      server.countryName.toLowerCase().contains(normalizedQuery);
}

final serverListViewProvider = Provider<ServerListViewModel>((ref) {
  final asyncState = ref.watch(profileAwareServerListProvider);
  final serverState = asyncState.value;
  final serverMap = ref.watch(serverMapProvider);
  final filteredServers = ref.watch(filteredServersProvider);
  final customServers = ref.watch(importedConfigsProvider);
  final searchQuery = ref.watch(serverSearchQueryProvider);
  final normalizedQuery = searchQuery.trim().toLowerCase();

  if (serverState == null) {
    return ServerListViewModel(
      searchQuery: searchQuery,
      favoriteServerIds: const <String>[],
      groupedServers: const <ServerListGroupViewModel>[],
    );
  }

  final filteredFavoriteIds = serverState.favoriteServerIds
      .where((id) {
        final server = serverMap[id];
        return server != null && _matchesServerSearch(server, normalizedQuery);
      })
      .toList(growable: false);

  final grouped = <String, List<ServerListEntryViewModel>>{};
  final countryNames = <String, String>{};

  for (final server in filteredServers) {
    if (!_matchesServerSearch(server, normalizedQuery)) {
      continue;
    }

    final countryEntries = grouped.putIfAbsent(
      server.countryCode,
      () => <ServerListEntryViewModel>[],
    );
    countryEntries.add(ServerListEntryViewModel.remote(serverId: server.id));
    countryNames.putIfAbsent(server.countryCode, () => server.countryName);
  }

  for (final config in customServers) {
    final server = _customConfigToServer(config);
    if (!_matchesServerSearch(server, normalizedQuery)) {
      continue;
    }

    final countryEntries = grouped.putIfAbsent(
      server.countryCode,
      () => <ServerListEntryViewModel>[],
    );
    countryEntries.add(
      ServerListEntryViewModel.custom(
        serverId: server.id,
        customServer: server,
        configId: config.id,
      ),
    );
    countryNames.putIfAbsent(server.countryCode, () => server.countryName);
  }

  final groupedServers = grouped.entries
      .map(
        (entry) => ServerListGroupViewModel(
          countryCode: entry.key,
          countryName: countryNames[entry.key] ?? entry.key,
          entries: List<ServerListEntryViewModel>.unmodifiable(entry.value),
        ),
      )
      .toList(growable: false);

  return ServerListViewModel(
    searchQuery: searchQuery,
    favoriteServerIds: filteredFavoriteIds,
    groupedServers: groupedServers,
  );
});

/// Stable index of servers by ID for row-level lookups.
final serverMapProvider = Provider<Map<String, ServerEntity>>((ref) {
  final servers = ref.watch(allServersWithPingProvider);
  if (servers.isEmpty) {
    return const <String, ServerEntity>{};
  }

  return Map<String, ServerEntity>.unmodifiable({
    for (final server in servers) server.id: server,
  });
});

/// Look up a single server by ID.
final serverByIdProvider = Provider.family<ServerEntity?, String>((
  ref,
  String id,
) {
  return ref.watch(serverMapProvider.select((serverMap) => serverMap[id]));
});

List<ServerEntity> _applyPingResults(
  List<ServerEntity> servers,
  Map<String, int> pingResults,
) {
  if (servers.isEmpty || pingResults.isEmpty) {
    return servers;
  }

  var changed = false;
  final merged = servers
      .map((server) {
        final ping = pingResults[server.id];
        if (ping == null || ping == server.ping) {
          return server;
        }

        changed = true;
        return server.copyWith(ping: ping);
      })
      .toList(growable: false);

  return changed ? merged : servers;
}

List<ServerEntity> _buildFilteredServers(
  ServerListState state,
  Map<String, int> pingResults,
) {
  var result = List<ServerEntity>.from(
    _applyPingResults(state.servers, pingResults),
  );

  if (state.filterCountry != null && state.filterCountry!.isNotEmpty) {
    result = result
        .where((ServerEntity s) => s.countryCode == state.filterCountry)
        .toList(growable: false);
  }

  if (state.filterProtocol != null) {
    result = result
        .where((ServerEntity s) => s.protocol == state.filterProtocol!.name)
        .toList(growable: false);
  }

  switch (state.sortMode) {
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
      result.sort(
        (ServerEntity a, ServerEntity b) =>
            a.countryName.compareTo(b.countryName),
      );
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
