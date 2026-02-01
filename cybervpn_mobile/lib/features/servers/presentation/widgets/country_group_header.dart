import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/shared/widgets/flag_widget.dart';

/// Sticky header for a group of servers sharing the same country.
///
/// Displays a country flag emoji, country name, server count badge, and a
/// collapsible expand/collapse arrow with smooth animation.
class CountryGroupHeader extends ConsumerStatefulWidget {
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
  ConsumerState<CountryGroupHeader> createState() =>
      _CountryGroupHeaderState();
}

class _CountryGroupHeaderState extends ConsumerState<CountryGroupHeader>
    with SingleTickerProviderStateMixin {
  late final AnimationController _arrowController;
  late final Animation<double> _arrowTurns;

  @override
  void initState() {
    super.initState();
    _arrowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
      value: widget.isExpanded ? 1.0 : 0.0,
    );
    _arrowTurns = Tween<double>(begin: 0.0, end: 0.5).animate(
      CurvedAnimation(parent: _arrowController, curve: Curves.easeInOut),
    );
  }

  @override
  void didUpdateWidget(covariant CountryGroupHeader oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isExpanded != oldWidget.isExpanded) {
      if (widget.isExpanded) {
        _arrowController.forward();
      } else {
        _arrowController.reverse();
      }
    }
  }

  @override
  void dispose() {
    _arrowController.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Material(
      color: colorScheme.surfaceContainerHighest.withValues(alpha: 0.6),
      child: InkWell(
        onTap: widget.onToggle,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(
            children: [
              // Country flag
              FlagWidget(
                countryCode: widget.countryCode,
                size: FlagSize.small,
              ),
              const SizedBox(width: 12),

              // Country name
              Expanded(
                child: Text(
                  widget.countryName,
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: colorScheme.onSurface,
                  ),
                ),
              ),

              // Server count badge
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 3,
                ),
                decoration: BoxDecoration(
                  color: colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${widget.serverCount}',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: colorScheme.onPrimaryContainer,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 8),

              // Expand / collapse arrow
              RotationTransition(
                turns: _arrowTurns,
                child: Icon(
                  Icons.expand_more,
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
