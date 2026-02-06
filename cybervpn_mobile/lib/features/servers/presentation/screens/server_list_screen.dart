import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/country_group_header.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/server_card.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/shared/services/tooltip_preferences_service.dart';
import 'package:cybervpn_mobile/shared/widgets/feature_tooltip.dart';
import 'package:cybervpn_mobile/shared/widgets/staggered_list_item.dart';

/// Main server list screen.
///
/// Features:
/// - Search bar at top
/// - Sort dropdown (Recommended / Country / Latency / Load)
/// - Collapsible favorites section
/// - "Fastest" quick-select chip
/// - Server list grouped by country with flag headers
/// - Pull-to-refresh
/// - Tap server to connect
class ServerListScreen extends ConsumerStatefulWidget {
  const ServerListScreen({super.key});

  @override
  ConsumerState<ServerListScreen> createState() => _ServerListScreenState();
}

class _ServerListScreenState extends ConsumerState<ServerListScreen> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  bool _favoritesExpanded = true;

  /// Tracks which country groups are expanded. All start expanded.
  final Map<String, bool> _expandedCountries = {};

  /// Global key for the "Fastest" button to position the tooltip.
  final GlobalKey _fastestButtonKey = GlobalKey();

  /// Service to track shown tooltips.
  final TooltipPreferencesService _tooltipService = TooltipPreferencesService();

  @override
  void initState() {
    super.initState();
    // Show tooltip after first frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_showTooltipIfNeeded());
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Tooltip
  // ---------------------------------------------------------------------------

  Future<void> _showTooltipIfNeeded() async {
    const tooltipId = 'servers_fastest_button';
    final hasShown = await _tooltipService.hasShownTooltip(tooltipId);

    if (!hasShown && mounted) {
      FeatureTooltip.show(
        context: context,
        targetKey: _fastestButtonKey,
        message: 'Tap Fastest to auto-select best server',
        position: TooltipPosition.bottom,
        onDismiss: () async {
          await _tooltipService.markTooltipAsShown(tooltipId);
        },
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  void _onSortChanged(SortMode? mode) {
    if (mode == null) return;
    ref.read(serverListProvider.notifier).sortBy(mode);
  }

  Future<void> _onRefresh() async {
    // Trigger haptic feedback when refresh is released/triggered.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.selection());

    await ref.read(serverListProvider.notifier).refresh();
  }

  void _onServerTap(ServerEntity server) {
    unawaited(Navigator.of(context).pushNamed(
      '/server-detail',
      arguments: server.id,
    ));
  }

  void _onFastestTap() {
    final recommended = ref.read(recommendedServerProvider);
    if (recommended != null) {
      _onServerTap(recommended);
    }
  }

  Future<void> _onCustomServerTap(String configId) async {
    // Find the custom server config
    final customServers = ref.read(importedConfigsProvider);
    final config = customServers.firstWhere(
      (c) => c.id == configId,
      orElse: () => throw Exception('Custom server not found'),
    );

    // Trigger haptic feedback on server selection.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.selection());

    // Connect to the custom server using VPN connection provider
    try {
      await ref.read(vpnConnectionProvider.notifier).connectFromCustomServer(config);

      // Show success snackbar
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connecting to ${config.name}...'),
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      // Show error snackbar
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to connect: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  String _sortModeLabel(SortMode mode) {
    return switch (mode) {
      SortMode.recommended => 'Recommended',
      SortMode.countryName => 'Country',
      SortMode.latency => 'Latency',
      SortMode.load => 'Load',
    };
  }

  bool _matchesSearch(ServerEntity server) {
    if (_searchQuery.isEmpty) return true;
    final q = _searchQuery.toLowerCase();
    return server.name.toLowerCase().contains(q) ||
        server.city.toLowerCase().contains(q) ||
        server.countryName.toLowerCase().contains(q);
  }

  /// Extract country code from custom server name if possible.
  /// Looks for common patterns like "US", "UK", "JP" in the name.
  /// Returns null if no country code can be extracted.
  String? _extractCountryCode(String name) {
    // Common 2-letter country codes
    final countryPattern = RegExp(r'\b([A-Z]{2})\b');
    final match = countryPattern.firstMatch(name.toUpperCase());
    return match?.group(1);
  }

  /// Convert ImportedConfig to ServerEntity for unified display.
  ServerEntity _customConfigToServer(ImportedConfig config) {
    final countryCode = _extractCountryCode(config.name) ?? 'XX';
    final countryName = countryCode == 'XX' ? 'Custom' : countryCode;

    return ServerEntity(
      id: config.id,
      name: config.name,
      countryCode: countryCode,
      countryName: countryName,
      city: config.serverAddress,
      address: config.serverAddress,
      port: config.port,
      protocol: config.protocol,
      isAvailable: config.isReachable ?? true,
    );
  }

  /// Build a merged map of servers grouped by country, including custom servers.
  Map<String, List<Map<String, dynamic>>> _getMergedGroupedServers(
    Map<String, List<ServerEntity>> grouped,
  ) {
    final customServers = ref.watch(importedConfigsProvider);
    final result = <String, List<Map<String, dynamic>>>{};

    // Add regular servers
    grouped.forEach((countryCode, servers) {
      result[countryCode] = servers
          .map((s) => {
                'server': s,
                'isCustom': false,
                'configId': null,
              })
          .toList();
    });

    // Add custom servers to their respective country groups
    for (final config in customServers) {
      final countryCode = _extractCountryCode(config.name) ?? 'XX';
      final serverEntity = _customConfigToServer(config);

      result.putIfAbsent(countryCode, () => []).add({
        'server': serverEntity,
        'isCustom': true,
        'configId': config.id,
      });
    }

    return result;
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(serverListProvider);
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Servers'),
      ),
      body: asyncState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
              const SizedBox(height: 12),
              Text('Failed to load servers',
                  style: theme.textTheme.bodyLarge),
              const SizedBox(height: 8),
              FilledButton.tonal(
                onPressed: () =>
                    ref.read(serverListProvider.notifier).fetchServers(),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (state) => _buildBody(context, state),
      ),
    );
  }

  Widget _buildBody(BuildContext context, ServerListState state) {
    final theme = Theme.of(context);
    final favorites = ref.watch(favoriteServersProvider);
    final grouped = ref.watch(groupedByCountryProvider);

    return RefreshIndicator(
      onRefresh: _onRefresh,
      child: CustomScrollView(
        slivers: [
          // --- Search bar + Sort dropdown ---
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Row(
                children: [
                  // Search
                  Expanded(
                    child: TextField(
                      controller: _searchController,
                      decoration: InputDecoration(
                        hintText: 'Search servers...',
                        prefixIcon: const Icon(Icons.search, size: 20),
                        suffixIcon: _searchQuery.isNotEmpty
                            ? IconButton(
                                icon: const Icon(Icons.clear, size: 18),
                                onPressed: () {
                                  _searchController.clear();
                                  setState(() => _searchQuery = '');
                                },
                              )
                            : null,
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 10,
                        ),
                      ),
                      onChanged: (value) =>
                          setState(() => _searchQuery = value),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Sort dropdown
                  DropdownButtonHideUnderline(
                    child: DropdownButton<SortMode>(
                      value: state.sortMode,
                      onChanged: _onSortChanged,
                      borderRadius: BorderRadius.circular(12),
                      items: SortMode.values
                          .map(
                            (mode) => DropdownMenuItem(
                              value: mode,
                              child: Text(
                                _sortModeLabel(mode),
                                style: theme.textTheme.bodyMedium,
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // --- Fastest quick-select chip ---
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Wrap(
                spacing: 8,
                children: [
                  Semantics(
                    label: 'Select fastest server',
                    button: true,
                    hint: 'Tap to automatically connect to the fastest available server',
                    child: ActionChip(
                      key: _fastestButtonKey,
                      avatar: const ExcludeSemantics(
                        child: Icon(Icons.bolt,
                            size: 16, color: Colors.amber),
                      ),
                      label: const Text('Fastest'),
                      onPressed: _onFastestTap,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // --- Favorites section (collapsible) ---
          if (favorites.isNotEmpty) ...[
            SliverToBoxAdapter(
              child: _buildFavoritesHeader(favorites.length),
            ),
            if (_favoritesExpanded)
              SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final server = favorites[index];
                    if (!_matchesSearch(server)) {
                      return const SizedBox.shrink();
                    }
                    return StaggeredListItem(
                      index: index,
                      child: ServerCard(
                        server: server,
                        onTap: () => _onServerTap(server),
                      ),
                    );
                  },
                  childCount: favorites.length,
                ),
              ),
            const SliverToBoxAdapter(
              child: Divider(indent: 16, endIndent: 16),
            ),
          ],

          // --- Merged grouped server list (includes custom servers) ---
          ..._getMergedGroupedServers(grouped).entries.expand((entry) {
            final countryCode = entry.key;
            final serverData = entry.value
                .where((data) => _matchesSearch(data['server'] as ServerEntity))
                .toList();
            if (serverData.isEmpty) return <Widget>[];

            final isExpanded = _expandedCountries[countryCode] ?? true;
            final countryName = serverData.isNotEmpty
                ? (serverData.first['server'] as ServerEntity).countryName
                : countryCode;

            return [
              SliverToBoxAdapter(
                child: CountryGroupHeader(
                  countryCode: countryCode,
                  countryName: countryName,
                  serverCount: serverData.length,
                  isExpanded: isExpanded,
                  onToggle: () {
                    setState(() {
                      _expandedCountries[countryCode] = !isExpanded;
                    });
                  },
                ),
              ),
              if (isExpanded)
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final data = serverData[index];
                      final server = data['server'] as ServerEntity;
                      final isCustom = data['isCustom'] as bool;
                      final configId = data['configId'] as String?;

                      return StaggeredListItem(
                        index: index,
                        child: ServerCard(
                          server: server,
                          onTap: isCustom && configId != null
                              ? () => _onCustomServerTap(configId)
                              : () => _onServerTap(server),
                          isCustomServer: isCustom,
                        ),
                      );
                    },
                    childCount: serverData.length,
                  ),
                ),
            ];
          }),

          // Bottom padding
          const SliverPadding(padding: EdgeInsets.only(bottom: 80)),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Favorites header
  // ---------------------------------------------------------------------------

  Widget _buildFavoritesHeader(int count) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return InkWell(
      onTap: () => setState(() => _favoritesExpanded = !_favoritesExpanded),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(
          children: [
            const Icon(Icons.star, color: Colors.amber, size: 20),
            const SizedBox(width: 8),
            Text(
              'Favorites',
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '$count',
                style: theme.textTheme.labelSmall?.copyWith(
                  color: colorScheme.onPrimaryContainer,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const Spacer(),
            AnimatedRotation(
              turns: _favoritesExpanded ? 0.0 : -0.25,
              duration: const Duration(milliseconds: 200),
              child: Icon(
                Icons.expand_more,
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
