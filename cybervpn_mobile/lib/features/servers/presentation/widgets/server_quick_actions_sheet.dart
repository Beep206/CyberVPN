import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/servers/presentation/providers/server_list_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

/// A bottom sheet displaying quick actions for a given VPN server.
///
/// Actions:
/// - **Connect** -- initiates a VPN connection to the server.
/// - **Favorite / Unfavorite** -- toggles the server's favorite status.
/// - **Copy Address** -- copies `address:port` to the clipboard.
/// - **View Details** -- navigates to the [ServerDetailScreen].
/// - **Report Issue** -- shows a confirmation snackbar (stub).
///
/// Theme-aware: uses [CyberColors] decoration when the cyberpunk theme is
/// active, and standard Material surface colors otherwise.
class ServerQuickActionsSheet extends ConsumerWidget {
  const ServerQuickActionsSheet({
    super.key,
    required this.server,
  });

  /// The server entity to act upon.
  final ServerEntity server;

  /// Shows the bottom sheet from the given [context].
  ///
  /// Returns the selected action as a [String] key, or `null` if dismissed.
  static Future<String?> show(BuildContext context, ServerEntity server) {
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(Radii.lg)),
      ),
      builder: (_) => ServerQuickActionsSheet(server: server),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isCyber = CyberColors.isCyberpunkTheme(context);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.only(bottom: Spacing.sm),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Drag handle
            const SizedBox(height: Spacing.sm),
            Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: Spacing.md),

            // Server name header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              child: Text(
                server.name,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: colorScheme.onSurface,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              child: Text(
                '${server.city}, ${server.countryName}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(height: Spacing.sm),
            const Divider(height: 1),

            // ---- Actions ----

            // 1. Connect
            _ActionTile(
              icon: Icons.power_settings_new,
              iconColor: isCyber ? CyberColors.matrixGreen : colorScheme.primary,
              title: l10n.serverQuickConnect,
              enabled: server.isAvailable,
              onTap: () => _handleConnect(context, ref),
            ),

            // 2. Favorite / Unfavorite
            _ActionTile(
              icon: server.isFavorite ? Icons.star : Icons.star_border,
              iconColor: server.isFavorite
                  ? Colors.amber
                  : colorScheme.onSurfaceVariant,
              title: server.isFavorite
                  ? l10n.serverQuickUnfavorite
                  : l10n.serverQuickFavorite,
              onTap: () => _handleFavorite(context, ref),
            ),

            // 3. Copy Address
            _ActionTile(
              icon: Icons.copy,
              iconColor: colorScheme.onSurfaceVariant,
              title: l10n.serverQuickCopyAddress,
              onTap: () => _handleCopyAddress(context, ref),
            ),

            // 4. View Details
            _ActionTile(
              icon: Icons.info_outline,
              iconColor: colorScheme.onSurfaceVariant,
              title: l10n.serverQuickViewDetails,
              onTap: () => _handleViewDetails(context, ref),
            ),

            // 5. Report Issue
            _ActionTile(
              icon: Icons.flag_outlined,
              iconColor: colorScheme.error,
              title: l10n.serverQuickReport,
              onTap: () => _handleReport(context, ref),
            ),
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Action handlers
  // ---------------------------------------------------------------------------

  void _handleConnect(BuildContext context, WidgetRef ref) {
    Navigator.of(context).pop('connect');
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());
    unawaited(
      ref.read(vpnConnectionProvider.notifier).connect(server),
    );
  }

  void _handleFavorite(BuildContext context, WidgetRef ref) {
    Navigator.of(context).pop('favorite');
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());
    unawaited(
      ref.read(serverListProvider.notifier).toggleFavorite(server.id),
    );
  }

  void _handleCopyAddress(BuildContext context, WidgetRef ref) {
    final address = '${server.address}:${server.port}';
    Clipboard.setData(ClipboardData(text: address));
    Navigator.of(context).pop('copy');
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.selection());
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(AppLocalizations.of(context).serverAddressCopied),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _handleViewDetails(BuildContext context, WidgetRef ref) {
    Navigator.of(context).pop('details');
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.selection());
    context.pushNamed('server-detail', pathParameters: {'id': server.id});
  }

  void _handleReport(BuildContext context, WidgetRef ref) {
    Navigator.of(context).pop('report');
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.impact());
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(AppLocalizations.of(context).serverReportSubmitted),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 3),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Private action tile widget
// ---------------------------------------------------------------------------

class _ActionTile extends StatelessWidget {
  const _ActionTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.onTap,
    this.enabled = true,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final VoidCallback onTap;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return ListTile(
      leading: Icon(
        icon,
        color: enabled ? iconColor : colorScheme.onSurface.withValues(alpha: 0.38),
        size: 24,
      ),
      title: Text(
        title,
        style: theme.textTheme.bodyLarge?.copyWith(
          color: enabled
              ? colorScheme.onSurface
              : colorScheme.onSurface.withValues(alpha: 0.38),
        ),
      ),
      enabled: enabled,
      onTap: enabled ? onTap : null,
      contentPadding: const EdgeInsets.symmetric(horizontal: Spacing.lg),
      minTileHeight: 52,
    );
  }
}
