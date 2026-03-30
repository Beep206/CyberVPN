import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/ping_indicator.dart';
import 'package:cybervpn_mobile/features/servers/presentation/widgets/server_quick_actions_sheet.dart';
import 'package:cybervpn_mobile/shared/widgets/flag_widget.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// ListTile-based card for a single VPN server.
///
/// Leading: country flag emoji.
/// Title: server name.
/// Subtitle: city + protocol badge.
/// Trailing: latency chip + load bar + favorite star.
/// Tap: connect to server.
///
/// Wrapped in [RepaintBoundary] to optimize list rendering performance.
class ServerCard extends ConsumerStatefulWidget {
  const ServerCard({
    super.key,
    required this.server,
    this.onTap,
    this.onPingTap,
    this.isCustomServer = false,
  });

  /// The server entity to display.
  final ServerEntity server;

  /// Called when the card is tapped (connect).
  final VoidCallback? onTap;

  /// Called when the ping chip is tapped (re-test).
  final VoidCallback? onPingTap;

  /// Whether this is a custom imported server.
  final bool isCustomServer;

  @override
  ConsumerState<ServerCard> createState() => _ServerCardState();
}

class _ServerCardState extends ConsumerState<ServerCard> {
  double _favoriteScale = 1.0;
  int _favoriteAnimationToken = 0;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Color _loadColor(double load, ColorScheme colorScheme) {
    if (load < 0.5) return colorScheme.tertiary;
    if (load < 0.7) return Colors.orange;
    return colorScheme.error;
  }

  void _handleFavoriteTap() {
    // Trigger haptic feedback on favorite toggle.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());

    _pulseFavoriteIcon();

    // Toggle favorite via provider.
    unawaited(
      ref.read(serverListProvider.notifier).toggleFavorite(widget.server.id),
    );
  }

  void _pulseFavoriteIcon() {
    if (MediaQuery.maybeOf(context)?.disableAnimations ?? false) {
      return;
    }

    final token = ++_favoriteAnimationToken;
    setState(() {
      _favoriteScale = 1.12;
    });

    unawaited(
      Future<void>.delayed(const Duration(milliseconds: 160)).then((_) {
        if (!mounted || token != _favoriteAnimationToken) {
          return;
        }

        setState(() {
          _favoriteScale = 1.0;
        });
      }),
    );
  }

  void _handleServerTap() {
    // Trigger haptic feedback on server selection.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.selection());

    // Call the provided onTap callback.
    widget.onTap?.call();
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final server = widget.server;
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final l10n = AppLocalizations.of(context);

    // Build semantic label for the server card
    final statusText = server.isAvailable
        ? l10n.a11yStatusOnline
        : l10n.a11yStatusOffline;
    final latencyText = server.ping != null
        ? l10n.a11yLatencyMsShort(server.ping!)
        : l10n.a11yLatencyUnknownShort;
    final loadText = server.load != null
        ? l10n.a11yLoadPercent((server.load! * 100).toInt())
        : '';
    final premiumText = server.isPremium ? ', ${l10n.a11yPremiumServer}' : '';
    final customText = widget.isCustomServer
        ? ', ${l10n.a11yCustomServer}'
        : '';

    final semanticLabel =
        '${l10n.a11yServerInCity(server.name, server.city)}, $statusText, $latencyText$loadText$premiumText$customText';

    return RepaintBoundary(
      child: Semantics(
        label: semanticLabel,
        button: true,
        hint: l10n.a11yServerCardHint,
        child: Card(
          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: InkWell(
            onTap: _handleServerTap,
            onLongPress: () {
              final haptics = ref.read(hapticServiceProvider);
              unawaited(haptics.impact());
              unawaited(ServerQuickActionsSheet.show(context, widget.server));
            },
            borderRadius: BorderRadius.circular(16),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  // Leading: compact flag optimized for dense scrolling lists
                  ExcludeSemantics(
                    child: FlagWidget(
                      countryCode: server.countryCode,
                      size: FlagSize.medium,
                      renderMode: FlagRenderMode.compactEmoji,
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Title + Subtitle
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Server name
                        Text(
                          server.name,
                          style: theme.textTheme.bodyLarge?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: colorScheme.onSurface,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),

                        // City + protocol badge row
                        Wrap(
                          spacing: 8,
                          runSpacing: 4,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Text(
                              server.city,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: colorScheme.onSurfaceVariant,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            _ProtocolBadge(protocol: server.protocol),
                            if (widget.isCustomServer)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 5,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: colorScheme.secondaryContainer,
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.add_circle_outline,
                                      size: 10,
                                      color: colorScheme.onSecondaryContainer,
                                    ),
                                    const SizedBox(width: 3),
                                    Text(
                                      l10n.serverCustomBadge,
                                      style: TextStyle(
                                        fontSize: 9,
                                        fontWeight: FontWeight.w700,
                                        color: colorScheme.onSecondaryContainer,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            if (server.isPremium)
                              Icon(
                                Icons.workspace_premium,
                                size: 14,
                                color: Colors.amber.shade600,
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),

                  // Trailing section: latency + load + favorite
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Ping indicator
                      PingIndicator(
                        latencyMs: server.ping,
                        onTap: widget.onPingTap,
                      ),
                      const SizedBox(height: 6),

                      // Load bar
                      SizedBox(
                        width: 48,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(2),
                          child: LinearProgressIndicator(
                            value: (server.load ?? 0).clamp(0.0, 1.0),
                            minHeight: 3,
                            backgroundColor: colorScheme.onSurface.withValues(
                              alpha: 0.12,
                            ),
                            valueColor: AlwaysStoppedAnimation<Color>(
                              _loadColor(server.load ?? 0, colorScheme),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(width: 8),

                  // Favorite star with scale animation (hidden for custom servers)
                  if (!widget.isCustomServer)
                    Semantics(
                      label: server.isFavorite
                          ? l10n.serverListRemoveFavorite
                          : l10n.serverListAddFavorite,
                      button: true,
                      hint: l10n.a11yToggleFavoriteHint,
                      child: AnimatedScale(
                        scale: _favoriteScale,
                        duration: const Duration(milliseconds: 160),
                        curve: Curves.easeOutBack,
                        child: IconButton(
                          icon: Icon(
                            server.isFavorite ? Icons.star : Icons.star_border,
                            color: server.isFavorite
                                ? Colors.amber
                                : colorScheme.onSurfaceVariant,
                            size: 22,
                          ),
                          onPressed: _handleFavoriteTap,
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(
                            minWidth: 44,
                            minHeight: 44,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Protocol badge
// ---------------------------------------------------------------------------

class _ProtocolBadge extends StatelessWidget {
  const _ProtocolBadge({required this.protocol});

  final String protocol;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: colorScheme.tertiaryContainer,
        borderRadius: BorderRadius.circular(6),
        boxShadow: CyberColors.isCyberpunkTheme(context)
            ? CyberEffects.neonGlow(colorScheme.tertiary, intensity: 0.3)
            : null,
      ),
      child: Text(
        protocol.toUpperCase(),
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w700,
          color: colorScheme.onTertiaryContainer,
        ),
      ),
    );
  }
}
