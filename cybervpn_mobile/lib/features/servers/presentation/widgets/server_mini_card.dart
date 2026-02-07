import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/shared/widgets/flag_widget.dart';

/// Compact server card for the recent servers carousel.
///
/// Displays a country flag, city name, and optional latency badge.
/// Supports tap to connect and long-press for details.
class ServerMiniCard extends StatelessWidget {
  const ServerMiniCard({
    super.key,
    required this.server,
    this.onTap,
    this.onLongPress,
  });

  final ServerEntity server;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final ping = server.ping;

    return SizedBox(
      width: 120,
      child: Card(
        clipBehavior: Clip.antiAlias,
        elevation: 1,
        child: InkWell(
          onTap: onTap,
          onLongPress: onLongPress,
          child: Padding(
            padding: const EdgeInsets.all(Spacing.sm),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Flag
                FlagWidget(
                  countryCode: server.countryCode,
                  size: FlagSize.medium,
                ),
                const SizedBox(height: Spacing.xs),

                // City / Server name
                Text(
                  server.city.isNotEmpty ? server.city : server.name,
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                ),

                // Latency badge
                if (ping != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      '${ping}ms',
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: ping < 50
                            ? CyberColors.matrixGreen
                            : ping < 100
                                ? Colors.amber
                                : colorScheme.error,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
