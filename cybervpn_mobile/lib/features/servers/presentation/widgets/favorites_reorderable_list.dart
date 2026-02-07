import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/server_card.dart';

/// A reorderable list of favorite servers with drag-and-drop support.
///
/// Each item renders a [ServerCard] with a leading drag handle. Reordering
/// persists the new order via the [ServerListNotifier].
class FavoritesReorderableList extends ConsumerWidget {
  const FavoritesReorderableList({
    super.key,
    required this.favorites,
    this.onServerTap,
  });

  /// The ordered list of favorite servers.
  final List<ServerEntity> favorites;

  /// Called when a server card is tapped (e.g. to navigate to details).
  final void Function(ServerEntity server)? onServerTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (favorites.isEmpty) {
      return _buildEmptyState(context);
    }

    return ReorderableListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: favorites.length,
      proxyDecorator: _proxyDecorator,
      onReorder: (int oldIndex, int newIndex) {
        unawaited(ref
            .read(serverListProvider.notifier)
            .reorderFavorites(oldIndex, newIndex));
      },
      itemBuilder: (BuildContext context, int index) {
        final server = favorites[index];
        return _FavoriteServerItem(
          key: ValueKey<String>(server.id),
          server: server,
          index: index,
          onTap: onServerTap != null ? () => onServerTap!(server) : null,
        );
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.star_border_rounded,
            size: 48,
            color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5),
          ),
          const SizedBox(height: 12),
          Text(
            l10n.serverNoFavoritesTitle,
            style: theme.textTheme.titleSmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            l10n.serverNoFavoritesDescription,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }

  /// Visual feedback when dragging a favorite item.
  Widget _proxyDecorator(
    Widget child,
    int index,
    Animation<double> animation,
  ) {
    return AnimatedBuilder(
      animation: animation,
      builder: (BuildContext context, Widget? childWidget) {
        final double elevation = Tween<double>(begin: 0, end: 8)
            .animate(CurvedAnimation(
              parent: animation,
              curve: Curves.easeInOut,
            ))
            .value;
        final double opacity = Tween<double>(begin: 1.0, end: 0.85)
            .animate(CurvedAnimation(
              parent: animation,
              curve: Curves.easeInOut,
            ))
            .value;

        return Opacity(
          opacity: opacity,
          child: Material(
            elevation: elevation,
            borderRadius: BorderRadius.circular(16),
            shadowColor: Colors.black45,
            child: childWidget,
          ),
        );
      },
      child: child,
    );
  }
}

// ---------------------------------------------------------------------------
// Individual favorite item with drag handle and animated star toggle
// ---------------------------------------------------------------------------

class _FavoriteServerItem extends ConsumerStatefulWidget {
  const _FavoriteServerItem({
    super.key,
    required this.server,
    required this.index,
    this.onTap,
  });

  final ServerEntity server;
  final int index;
  final VoidCallback? onTap;

  @override
  ConsumerState<_FavoriteServerItem> createState() =>
      _FavoriteServerItemState();
}

class _FavoriteServerItemState extends ConsumerState<_FavoriteServerItem>
    with SingleTickerProviderStateMixin {
  late final AnimationController _starScaleController;
  late final Animation<double> _starScaleAnimation;

  @override
  void initState() {
    super.initState();
    _starScaleController = AnimationController(
      vsync: this,
      duration: AnimDurations.normal,
    );
    _starScaleAnimation = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.0, end: 0.5)
            .chain(CurveTween(curve: Curves.easeIn)),
        weight: 40,
      ),
      TweenSequenceItem(
        tween: Tween<double>(begin: 0.5, end: 1.0)
            .chain(CurveTween(curve: Curves.elasticOut)),
        weight: 60,
      ),
    ]).animate(_starScaleController);
  }

  @override
  void dispose() {
    _starScaleController.dispose();
    super.dispose();
  }

  void _handleToggleFavorite() {
    unawaited(_starScaleController.forward(from: 0.0));
    unawaited(ref
        .read(serverListProvider.notifier)
        .toggleFavorite(widget.server.id));
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      child: Row(
        children: [
          // Drag handle
          ReorderableDragStartListener(
            index: widget.index,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
              child: Icon(
                Icons.drag_handle,
                color: colorScheme.onSurfaceVariant.withValues(alpha: 0.6),
                size: 24,
              ),
            ),
          ),

          // Server card
          Expanded(
            child: ServerCard(
              server: widget.server,
              onTap: widget.onTap,
            ),
          ),

          // Animated star toggle
          ScaleTransition(
            scale: _starScaleAnimation,
            child: IconButton(
              icon: Icon(
                widget.server.isFavorite ? Icons.star : Icons.star_border,
                color: widget.server.isFavorite
                    ? Colors.amber
                    : colorScheme.onSurfaceVariant,
                size: 24,
              ),
              onPressed: _handleToggleFavorite,
            ),
          ),
        ],
      ),
    );
  }
}
