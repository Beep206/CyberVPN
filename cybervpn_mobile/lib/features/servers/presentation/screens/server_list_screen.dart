import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lottie/lottie.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/country_group_header.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_detail_screen.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/server_card.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/shared/services/tooltip_preferences_service.dart';
import 'package:cybervpn_mobile/shared/widgets/feature_tooltip.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/recent_servers_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/screens/server_map_screen.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/server_mini_card.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_refresh_indicator.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';

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

  /// Selected server ID for master-detail layout on wide screens.
  /// Persisted to SharedPreferences so tablet users keep context across restarts.
  static const _selectedServerKey = 'tablet_selected_server_id';
  String? _selectedServerId;

  /// Tracks which country groups are expanded. All start expanded.
  final Map<String, bool> _expandedCountries = {};

  /// Keys for country group headers, used for auto-scroll after expand.
  final Map<String, GlobalKey> _countryHeaderKeys = {};

  /// Global key for the "Fastest" button to position the tooltip.
  final GlobalKey _fastestButtonKey = GlobalKey();

  /// Service to track shown tooltips.
  final TooltipPreferencesService _tooltipService = TooltipPreferencesService();

  @override
  void initState() {
    super.initState();
    // Restore persisted selection for tablet master-detail layout.
    _restoreSelectedServer();
    // Show tooltip after first frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_showTooltipIfNeeded());
    });
  }

  void _restoreSelectedServer() {
    final prefs = ref.read(sharedPreferencesProvider);
    final saved = prefs.getString(_selectedServerKey);
    if (saved != null && saved.isNotEmpty) {
      setState(() => _selectedServerId = saved);
    }
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
        message: AppLocalizations.of(context).serverTooltipFastest,
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
    // Haptic feedback at pull threshold is handled by CyberRefreshIndicator
    // (fires mediumImpact when the user crosses the trigger distance).
    await ref.read(serverListProvider.notifier).refresh();
  }

  void _onServerTap(ServerEntity server) {
    if (_isWideLayout(context)) {
      setState(() => _selectedServerId = server.id);
      unawaited(ref.read(sharedPreferencesProvider).setString(
        _selectedServerKey,
        server.id,
      ));
    } else {
      unawaited(context.push('/servers/${server.id}'));
    }
  }

  /// Returns `true` when the screen is wide enough for master-detail layout.
  bool _isWideLayout(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= 600;

  void _onFastestTap() {
    // Trigger light haptic on button tap.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.selection());

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
            content: Text(AppLocalizations.of(context).serverDetailConnectingTo(config.name)),
            duration: const Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      // Show error snackbar with error haptic feedback.
      if (mounted) {
        final haptics = ref.read(hapticServiceProvider);
        unawaited(haptics.error());

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).serverDetailFailedToConnect(e.toString())),
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
    final l10n = AppLocalizations.of(context);
    return switch (mode) {
      SortMode.recommended => l10n.serverSortRecommended,
      SortMode.countryName => l10n.serverSortCountry,
      SortMode.latency => l10n.serverSortLatency,
      SortMode.load => l10n.serverSortLoad,
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
    final countryName = countryCode == 'XX' ? AppLocalizations.of(context).serverCustomCountry : countryCode;

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
    final isWide = _isWideLayout(context);

    final listContent = asyncState.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
            const SizedBox(height: Spacing.sm),
            Text(AppLocalizations.of(context).serverFailedToLoad,
                style: theme.textTheme.bodyLarge),
            const SizedBox(height: Spacing.sm),
            FilledButton.tonal(
              onPressed: () {
                unawaited(ref.read(hapticServiceProvider).selection());
                unawaited(ref.read(serverListProvider.notifier).fetchServers());
              },
              child: Text(AppLocalizations.of(context).retry),
            ),
          ],
        ),
      ),
      data: (state) => _buildBody(context, state),
    );

    if (isWide) {
      return Scaffold(
        appBar: AppBar(
          title: GlitchText(
          text: AppLocalizations.of(context).servers,
          style: Theme.of(context).appBarTheme.titleTextStyle,
        ),
        ),
        body: LayoutBuilder(
          builder: (context, constraints) {
            // Use ~28% of available width, clamped to [280, 400].
            final sidebarWidth =
                (constraints.maxWidth * 0.28).clamp(280.0, 400.0);

            return Row(
              children: [
                ConstrainedBox(
                  constraints: const BoxConstraints(
                    minWidth: 280,
                    maxWidth: 400,
                  ),
                  child: SizedBox(
                    width: sidebarWidth,
                    child: listContent,
                  ),
                ),
                const VerticalDivider(thickness: 1, width: 1),
                Expanded(
                  child: _selectedServerId != null
                      ? ServerDetailScreen(
                          serverId: _selectedServerId!,
                          embedded: true,
                        )
                      : Center(
                          child: Text(
                            AppLocalizations.of(context).serverSelectPrompt,
                            style: theme.textTheme.bodyLarge?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                ),
              ],
            );
          },
        ),
      );
    }

    final preferMap = ref.watch(
      settingsProvider.select((s) => s.value?.preferMapView ?? false),
    );

    return Scaffold(
      appBar: AppBar(
        title: GlitchText(
          text: AppLocalizations.of(context).servers,
          style: Theme.of(context).appBarTheme.titleTextStyle,
        ),
        actions: [
          IconButton(
            icon: Icon(preferMap ? Icons.list : Icons.map_outlined),
            tooltip: preferMap ? 'List view' : 'Map view',
            onPressed: () {
              unawaited(ref.read(settingsProvider.notifier).updatePreferMapView(!preferMap));
            },
          ),
        ],
      ),
      body: preferMap ? const ServerMapScreen() : listContent,
    );
  }

  Widget _buildBody(BuildContext context, ServerListState state) {
    final theme = Theme.of(context);
    final favorites = ref.watch(favoriteServersProvider);
    final grouped = ref.watch(groupedByCountryProvider);
    return NotificationListener<ScrollNotification>(
      onNotification: (notification) {
        if (notification is ScrollEndNotification &&
            notification.metrics.extentAfter < 200 &&
            state.hasMore &&
            !state.isLoadingMore) {
          unawaited(ref.read(serverListProvider.notifier).loadMore());
        }
        return false;
      },
      child: CyberRefreshIndicator(
      onRefresh: _onRefresh,
      child: CustomScrollView(
        slivers: [
          // --- Search bar + Sort dropdown ---
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(Spacing.md, Spacing.sm + 4, Spacing.md, Spacing.xs),
              child: Row(
                children: [
                  // Search
                  Expanded(
                    child: Semantics(
                      label: AppLocalizations.of(context).a11ySearchField,
                      hint: 'Type to filter servers by name, city, or country',
                      textField: true,
                      child: TextField(
                        controller: _searchController,
                        decoration: InputDecoration(
                          hintText: AppLocalizations.of(context).serverListSearchHint,
                          prefixIcon: const Icon(Icons.search, size: 20),
                          suffixIcon: _searchQuery.isNotEmpty
                              ? Semantics(
                                  label: 'Clear search',
                                  hint: 'Double tap to clear search text',
                                  button: true,
                                  child: IconButton(
                                    icon: const Icon(Icons.clear, size: 18),
                                    onPressed: () {
                                      _searchController.clear();
                                      setState(() => _searchQuery = '');
                                    },
                                  ),
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
                  ),
                  const SizedBox(width: Spacing.sm),

                  // Sort dropdown
                  Flexible(
                    flex: 0,
                    child: Semantics(
                      label: 'Sort servers by ${_sortModeLabel(state.sortMode)}',
                      hint: 'Double tap to change sort order',
                      button: true,
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<SortMode>(
                          value: state.sortMode,
                          onChanged: _onSortChanged,
                          borderRadius: BorderRadius.circular(Radii.md),
                          items: SortMode.values
                              .map(
                                (mode) => DropdownMenuItem(
                                  value: mode,
                                  child: Text(
                                    _sortModeLabel(mode),
                                    style: theme.textTheme.bodyMedium,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // --- Server count + Fastest chip ---
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md, vertical: Spacing.xs),
              child: Wrap(
                spacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  if (state.totalServerCount > 0)
                    Text(
                      AppLocalizations.of(context).serverListCount(
                        state.servers.length,
                        state.totalServerCount,
                      ),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  Semantics(
                    label: AppLocalizations.of(context).a11ySelectFastestServer,
                    button: true,
                    hint: AppLocalizations.of(context).a11ySelectFastestServerHint,
                    child: ActionChip(
                      key: _fastestButtonKey,
                      avatar: const ExcludeSemantics(
                        child: Icon(Icons.bolt,
                            size: 16, color: Colors.amber),
                      ),
                      label: Text(AppLocalizations.of(context).serverFastest),
                      onPressed: _onFastestTap,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // --- Recent servers carousel ---
          _RecentServersCarousel(
            onServerTap: _onServerTap,
            onServerLongPress: (server) =>
                unawaited(context.push('/servers/${server.id}')),
          ),

          // --- Favorites section (collapsible) ---
          if (favorites.isNotEmpty) ...[
            SliverToBoxAdapter(
              child: _buildFavoritesHeader(favorites.length),
            ),
            SliverToBoxAdapter(
              child: _AnimatedExpandSection(
                isExpanded: _favoritesExpanded,
                child: Column(
                  children: [
                    for (int index = 0; index < favorites.length; index++)
                      if (_matchesSearch(favorites[index]))
                        StaggeredListItem(
                          index: index,
                          child: ServerCard(
                            server: favorites[index],
                            onTap: () => _onServerTap(favorites[index]),
                          ),
                        ),
                  ],
                ),
              ),
            ),
            const SliverToBoxAdapter(
              child: Divider(indent: 16, endIndent: 16),
            ),
          ],

          // --- Merged grouped server list (includes custom servers) ---
          if (_searchQuery.isNotEmpty && _getMergedGroupedServers(grouped).entries.every((entry) =>
              entry.value.where((data) => _matchesSearch(data['server'] as ServerEntity)).isEmpty))
            SliverFillRemaining(
              hasScrollBody: false,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Lottie.asset(
                      'assets/animations/empty_state.json',
                      width: 120,
                      height: 120,
                      fit: BoxFit.contain,
                      animate: !MediaQuery.of(context).disableAnimations,
                    ),
                    const SizedBox(height: Spacing.md),
                    Text(
                      AppLocalizations.of(context).serverListNoResults,
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: Spacing.sm),
                    TextButton(
                      onPressed: () => setState(() => _searchQuery = ''),
                      child: Text(AppLocalizations.of(context).serverListClearSearch),
                    ),
                  ],
                ),
              ),
            )
          else
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

              final headerKey = _countryHeaderKeys.putIfAbsent(
                countryCode,
                GlobalKey.new,
              );

              return [
                SliverToBoxAdapter(
                  child: CountryGroupHeader(
                    key: headerKey,
                    countryCode: countryCode,
                    countryName: countryName,
                    serverCount: serverData.length,
                    isExpanded: isExpanded,
                    onToggle: () {
                      final wasCollapsed = !isExpanded;
                      setState(() {
                        _expandedCountries[countryCode] = !isExpanded;
                      });
                      // Auto-scroll to keep header visible after expanding.
                      if (wasCollapsed) {
                        WidgetsBinding.instance.addPostFrameCallback((_) {
                          final ctx = headerKey.currentContext;
                          if (ctx != null) {
                            unawaited(Scrollable.ensureVisible(
                              ctx,
                              duration: AnimDurations.medium,
                              curve: Curves.easeInOut,
                              alignmentPolicy:
                                  ScrollPositionAlignmentPolicy.keepVisibleAtEnd,
                            ));
                          }
                        });
                      }
                    },
                  ),
                ),
                SliverToBoxAdapter(
                  child: _AnimatedExpandSection(
                    isExpanded: isExpanded,
                    child: Column(
                      children: [
                        for (int index = 0; index < serverData.length; index++)
                          Builder(builder: (context) {
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
                          }),
                      ],
                    ),
                  ),
                ),
              ];
            }),

          // Loading indicator for infinite scroll
          if (state.isLoadingMore)
            const SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: Spacing.lg),
                child: Center(child: CircularProgressIndicator()),
              ),
            ),

          // Bottom padding
          SliverPadding(padding: EdgeInsets.only(bottom: Spacing.navBarClearance(context))),
        ],
      ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Favorites header
  // ---------------------------------------------------------------------------

  Widget _buildFavoritesHeader(int count) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Semantics(
      label: '${AppLocalizations.of(context).serverFavoritesTitle}, $count servers',
      hint: 'Double tap to ${_favoritesExpanded ? 'collapse' : 'expand'} favorites',
      button: true,
      expanded: _favoritesExpanded,
      child: InkWell(
        onTap: () => setState(() => _favoritesExpanded = !_favoritesExpanded),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: Spacing.md, vertical: Spacing.sm + 2),
          child: Row(
            children: [
              const ExcludeSemantics(
                child: Icon(Icons.star, color: Colors.amber, size: 20),
              ),
              const SizedBox(width: Spacing.sm),
              ExcludeSemantics(
                child: Text(
                  AppLocalizations.of(context).serverFavoritesTitle,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(width: Spacing.sm),
              ExcludeSemantics(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: Spacing.sm - 1, vertical: 2),
                  decoration: BoxDecoration(
                    color: colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(Radii.sm + 2),
                  ),
                  child: Text(
                    '$count',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
              const Spacer(),
              ExcludeSemantics(
                child: AnimatedRotation(
                  turns: _favoritesExpanded ? 0.0 : -0.25,
                  duration: AnimDurations.medium,
                  child: Icon(
                    Icons.expand_more,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Smoothly animates the height of [child] between 0 and its intrinsic size.
///
/// Used inside [SliverToBoxAdapter] to animate expand/collapse of server
/// groups without breaking the sliver layout.
class _AnimatedExpandSection extends StatefulWidget {
  const _AnimatedExpandSection({
    required this.isExpanded,
    required this.child,
  });

  final bool isExpanded;
  final Widget child;

  @override
  State<_AnimatedExpandSection> createState() => _AnimatedExpandSectionState();
}

class _AnimatedExpandSectionState extends State<_AnimatedExpandSection>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _sizeFactor;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AnimDurations.medium,
      value: widget.isExpanded ? 1.0 : 0.0,
    );
    _sizeFactor = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    );
  }

  @override
  void didUpdateWidget(covariant _AnimatedExpandSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isExpanded != oldWidget.isExpanded) {
      if (widget.isExpanded) {
        unawaited(_controller.forward());
      } else {
        unawaited(_controller.reverse());
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizeTransition(
      sizeFactor: _sizeFactor,
      axisAlignment: -1.0,
      child: widget.child,
    );
  }
}

// ---------------------------------------------------------------------------
// Recent servers carousel
// ---------------------------------------------------------------------------

/// Horizontal scrolling carousel of recently connected servers.
///
/// Renders as a [SliverToBoxAdapter] containing a horizontal [ListView].
/// If no recent servers exist, shows a subtle empty-state text.
class _RecentServersCarousel extends ConsumerWidget {
  const _RecentServersCarousel({
    required this.onServerTap,
    required this.onServerLongPress,
  });

  final void Function(ServerEntity) onServerTap;
  final void Function(ServerEntity) onServerLongPress;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recentServers = ref.watch(recentServersProvider);
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    if (recentServers.isEmpty) {
      return SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.md,
            vertical: Spacing.xs,
          ),
          child: Text(
            l10n.serverNoRecentServers,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      );
    }

    return SliverToBoxAdapter(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              Spacing.md, Spacing.xs, Spacing.md, Spacing.xs,
            ),
            child: Text(
              l10n.serverRecentServers,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          SizedBox(
            height: 100,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              itemCount: recentServers.length,
              separatorBuilder: (_, _) =>
                  const SizedBox(width: Spacing.sm),
              itemBuilder: (context, index) {
                final server = recentServers[index];
                return ServerMiniCard(
                  server: server,
                  onTap: () => onServerTap(server),
                  onLongPress: () => onServerLongPress(server),
                );
              },
            ),
          ),
          const SizedBox(height: Spacing.xs),
        ],
      ),
    );
  }
}
