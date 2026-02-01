import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// Groups related settings tiles under a styled section header.
///
/// Usage:
/// ```dart
/// SettingsSection(
///   title: 'Appearance',
///   children: [
///     SettingsTile.toggle(title: 'Dark mode', ...),
///     SettingsTile.navigation(title: 'Theme', ...),
///   ],
/// )
/// ```
class SettingsSection extends StatelessWidget {
  const SettingsSection({
    super.key,
    required this.title,
    required this.children,
  });

  /// The section header text displayed above the tiles.
  final String title;

  /// The list of settings tiles within this section.
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header
        Padding(
          padding: const EdgeInsets.symmetric(
            vertical: Spacing.sm,
            horizontal: Spacing.md,
          ),
          child: Text(
            title,
            style: theme.textTheme.titleMedium?.copyWith(
              color: theme.colorScheme.primary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),

        // Child tiles
        ...children,

        // Bottom spacing between sections
        const SizedBox(height: Spacing.sm),
      ],
    );
  }
}
