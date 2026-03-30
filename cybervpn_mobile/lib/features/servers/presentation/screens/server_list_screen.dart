import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:lottie/lottie.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/profile_aware_server_list.dart';
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
      unawaited(
        ref
            .read(sharedPreferencesProvider)
            .setString(_selectedServerKey, server.id),
      );
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
      await ref
          .read(vpnConnectionProvider.notifier)
          .connectFromCustomServer(config);

      // Show success snackbar
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              AppLocalizations.of(
                context,
              ).serverDetailConnectingTo(config.name),
            ),
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
            content: Text(
              AppLocalizations.of(
                context,
              ).serverDetailFailedToConnect(e.toString()),
            ),
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

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(profileAwareServerListProvider);
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
            Text(
              AppLocalizations.of(context).serverFailedToLoad,
              style: theme.textTheme.bodyLarge,
            ),
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
            final sidebarWidth = (constraints.maxWidth * 0.28).clamp(
              280.0,
              400.0,
            );

            return Row(
              children: [
                ConstrainedBox(
                  constraints: const BoxConstraints(
                    minWidth: 280,
                    maxWidth: 400,
                  ),
                  child: SizedBox(width: sidebarWidth, child: listContent),
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
              unawaited(
                ref
                    .read(settingsProvider.notifier)
                    .updatePreferMapView(!preferMap),
              );
            },
          ),
        ],
      ),
      body: preferMap ? const ServerMapScreen() : listContent,
    );
  }

  Widget _buildBody(BuildContext context, ServerListState state) {
    final theme = Theme.of(context);
    final viewModel = ref.watch(serverListViewProvider);
    final favoriteServerIds = viewModel.favoriteServerIds;
    final filteredGroupedServers = viewModel.groupedServers;
    final hasSearchResults = !viewModel.hasActiveSearch || viewModel.hasResults;

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
                padding: const EdgeInsets.fromLTRB(
                  Spacing.md,
                  Spacing.sm + 4,
                  Spacing.md,
                  Spacing.xs,
                ),
                child: Row(
                  children: [
                    // Search
                    Expanded(
                      child: Semantics(
                        label: AppLocalizations.of(context).a11ySearchField,
                        hint:
                            'Type to filter servers by name, city, or country',
                        textField: true,
                        child: const _ServerSearchField(),
                      ),
                    ),
                    const SizedBox(width: Spacing.sm),

                    // Sort dropdown
                    Flexible(
                      flex: 0,
                      child: Semantics(
                        label:
                            'Sort servers by ${_sortModeLabel(state.sortMode)}',
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
                padding: const EdgeInsets.symmetric(
                  horizontal: Spacing.md,
                  vertical: Spacing.xs,
                ),
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
                      label: AppLocalizations.of(
                        context,
                      ).a11ySelectFastestServer,
                      button: true,
                      hint: AppLocalizations.of(
                        context,
                      ).a11ySelectFastestServerHint,
                      child: ActionChip(
                        key: _fastestButtonKey,
                        avatar: const ExcludeSemantics(
                          child: Icon(
                            Icons.bolt,
                            size: 16,
                            color: Colors.amber,
                          ),
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
            if (favoriteServerIds.isNotEmpty) ...[
              SliverToBoxAdapter(
                child: _buildFavoritesHeader(favoriteServerIds.length),
              ),
              if (_favoritesExpanded)
                SliverList(
                  delegate: SliverChildBuilderDelegate((context, index) {
                    final serverId = favoriteServerIds[index];
                    return StaggeredListItem(
                      index: index,
                      child: _ServerCardById(
                        serverId: serverId,
                        onTap: _onServerTap,
                      ),
                    );
                  }, childCount: favoriteServerIds.length),
                ),
              const SliverToBoxAdapter(
                child: Divider(indent: 16, endIndent: 16),
              ),
            ],

            // --- Merged grouped server list (includes custom servers) ---
            if (!hasSearchResults)
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
                        frameRate: const FrameRate(24),
                        backgroundLoading: true,
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
                        onPressed: () => ref
                            .read(serverSearchQueryProvider.notifier)
                            .clear(),
                        child: Text(
                          AppLocalizations.of(context).serverListClearSearch,
                        ),
                      ),
                    ],
                  ),
                ),
              )
            else
              ...filteredGroupedServers.expand((group) {
                final countryCode = group.countryCode;
                final serverData = group.entries;

                final isExpanded = _expandedCountries[countryCode] ?? true;
                final countryName = group.countryName;

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
                              unawaited(
                                Scrollable.ensureVisible(
                                  ctx,
                                  duration: AnimDurations.medium,
                                  curve: Curves.easeInOut,
                                  alignmentPolicy: ScrollPositionAlignmentPolicy
                                      .keepVisibleAtEnd,
                                ),
                              );
                            }
                          });
                        }
                      },
                    ),
                  ),
                  if (isExpanded)
                    SliverList(
                      delegate: SliverChildBuilderDelegate((context, index) {
                        final data = serverData[index];
                        final isCustom = data.isCustom;
                        final configId = data.configId;

                        return StaggeredListItem(
                          index: index,
                          child: isCustom
                              ? ServerCard(
                                  server: data.customServer!,
                                  onTap: configId == null
                                      ? null
                                      : () => _onCustomServerTap(configId),
                                  isCustomServer: true,
                                )
                              : _ServerCardById(
                                  serverId: data.serverId,
                                  onTap: _onServerTap,
                                ),
                        );
                      }, childCount: serverData.length),
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
            SliverPadding(
              padding: EdgeInsets.only(
                bottom: Spacing.navBarClearance(context),
              ),
            ),
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
      label:
          '${AppLocalizations.of(context).serverFavoritesTitle}, $count servers',
      hint:
          'Double tap to ${_favoritesExpanded ? 'collapse' : 'expand'} favorites',
      button: true,
      expanded: _favoritesExpanded,
      child: InkWell(
        onTap: () => setState(() => _favoritesExpanded = !_favoritesExpanded),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.md,
            vertical: Spacing.sm + 2,
          ),
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
                  padding: const EdgeInsets.symmetric(
                    horizontal: Spacing.sm - 1,
                    vertical: 2,
                  ),
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

class _ServerCardById extends ConsumerWidget {
  const _ServerCardById({required this.serverId, required this.onTap});

  final String serverId;
  final ValueChanged<ServerEntity> onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final server = ref.watch(serverByIdProvider(serverId));
    if (server == null) {
      return const SizedBox.shrink();
    }

    return ServerCard(server: server, onTap: () => onTap(server));
  }
}

class _ServerSearchField extends ConsumerStatefulWidget {
  const _ServerSearchField();

  @override
  ConsumerState<_ServerSearchField> createState() => _ServerSearchFieldState();
}

class _ServerSearchFieldState extends ConsumerState<_ServerSearchField> {
  static const _debounceDuration = Duration(milliseconds: 180);

  late final TextEditingController _controller;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(
      text: ref.read(serverSearchQueryProvider),
    )..addListener(_handleControllerChanged);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller
      ..removeListener(_handleControllerChanged)
      ..dispose();
    super.dispose();
  }

  void _handleControllerChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  void _scheduleSearch(String value) {
    _debounce?.cancel();
    _debounce = Timer(_debounceDuration, () {
      ref.read(serverSearchQueryProvider.notifier).setQuery(value);
    });
  }

  void _clearSearch() {
    _debounce?.cancel();
    _controller.clear();
    ref.read(serverSearchQueryProvider.notifier).clear();
  }

  @override
  Widget build(BuildContext context) {
    final activeQuery = ref.watch(serverSearchQueryProvider);
    if (_controller.text != activeQuery) {
      _controller.value = TextEditingValue(
        text: activeQuery,
        selection: TextSelection.collapsed(offset: activeQuery.length),
      );
    }

    return TextField(
      controller: _controller,
      decoration: InputDecoration(
        hintText: AppLocalizations.of(context).serverListSearchHint,
        prefixIcon: const Icon(Icons.search, size: 20),
        suffixIcon: _controller.text.isNotEmpty
            ? Semantics(
                label: 'Clear search',
                hint: 'Double tap to clear search text',
                button: true,
                child: IconButton(
                  icon: const Icon(Icons.clear, size: 18),
                  onPressed: _clearSearch,
                ),
              )
            : null,
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 10,
        ),
      ),
      onChanged: _scheduleSearch,
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
              Spacing.md,
              Spacing.xs,
              Spacing.md,
              Spacing.xs,
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
              separatorBuilder: (_, _) => const SizedBox(width: Spacing.sm),
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
