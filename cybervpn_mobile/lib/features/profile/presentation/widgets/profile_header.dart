import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';

/// Profile header widget displaying avatar and user information.
///
/// Shows a circular avatar with user initials, username/email, and member since date.
/// This widget is theme-aware and adapts to both light and dark cyberpunk themes.
class ProfileHeader extends StatelessWidget {
  /// User profile data to display.
  final Profile profile;

  /// Avatar radius. Defaults to 40.
  final double avatarRadius;

  const ProfileHeader({
    super.key,
    required this.profile,
    this.avatarRadius = 40,
  });

  /// Generate initials from username or email.
  ///
  /// Takes the first letter of the first two words if available,
  /// otherwise uses the first character.
  String _initials() {
    final name = profile.username ?? profile.email;
    final parts = name.split(RegExp(r'[\s@.]+'));
    if (parts.length >= 2) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return name.isNotEmpty ? name[0].toUpperCase() : '?';
  }

  /// Format the member since date.
  String _memberSince() {
    final date = profile.createdAt;
    if (date == null) return '';
    return 'Member since ${DateFormat.yMMMM().format(date)}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Column(
      children: [
        // Avatar
        CircleAvatar(
          radius: avatarRadius,
          backgroundColor: colorScheme.primary.withAlpha(40),
          child: Text(
            _initials(),
            style: theme.textTheme.headlineMedium?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(height: Spacing.sm),

        // Username
        Text(
          profile.username ?? profile.email.split('@').first,
          style: theme.textTheme.titleLarge,
        ),
        const SizedBox(height: Spacing.xs),

        // Email
        Text(
          profile.email,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),

        // Member since
        if (profile.createdAt != null) ...[
          const SizedBox(height: Spacing.xs),
          Text(
            _memberSince(),
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ],
    );
  }
}
