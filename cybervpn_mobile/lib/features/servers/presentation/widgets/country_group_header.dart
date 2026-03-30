import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/shared/widgets/flag_widget.dart';

/// Sticky header for a group of servers sharing the same country.
///
/// Displays a country flag emoji, country name, server count badge, and a
/// collapsible expand/collapse arrow with smooth animation.
class CountryGroupHeader extends StatelessWidget {
  const CountryGroupHeader({
    super.key,
    required this.countryCode,
    required this.countryName,
    required this.serverCount,
    required this.isExpanded,
    required this.onToggle,
  });

  /// ISO 3166-1 alpha-2 country code (e.g. 'US', 'DE').
  final String countryCode;

  /// Human-readable country name.
  final String countryName;

  /// Number of servers in this group.
  final int serverCount;

  /// Whether the group is currently expanded.
  final bool isExpanded;

  /// Called when the user taps to expand or collapse.
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Semantics(
      label: '$countryName, $serverCount servers',
      hint: 'Double tap to ${isExpanded ? 'collapse' : 'expand'} server list',
      button: true,
      expanded: isExpanded,
      child: Material(
        color: colorScheme.surfaceContainerHighest.withValues(alpha: 0.6),
        child: InkWell(
          onTap: onToggle,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Row(
              children: [
                // Country flag
                ExcludeSemantics(
                  child: FlagWidget(
                    countryCode: countryCode,
                    size: FlagSize.small,
                    renderMode: FlagRenderMode.compactEmoji,
                  ),
                ),
                const SizedBox(width: 12),

                // Country name
                Expanded(
                  child: ExcludeSemantics(
                    child: Text(
                      countryName,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: colorScheme.onSurface,
                      ),
                    ),
                  ),
                ),

                // Server count badge
                ExcludeSemantics(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '$serverCount',
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: colorScheme.onPrimaryContainer,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),

                // Expand / collapse arrow
                ExcludeSemantics(
                  child: AnimatedRotation(
                    turns: isExpanded ? 0.5 : 0.0,
                    duration: AnimDurations.medium,
                    curve: Curves.easeInOut,
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
      ),
    );
  }
}
