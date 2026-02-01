import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';

/// Renders a single onboarding page with a placeholder icon, title, and
/// description.
///
/// Lottie animations are not yet available, so each page displays a themed
/// [Icon] inside a decorated container as a visual placeholder.
class OnboardingPageWidget extends StatelessWidget {
  const OnboardingPageWidget({
    super.key,
    required this.page,
    required this.pageIndex,
  });

  /// The onboarding page data to display.
  final OnboardingPage page;

  /// Zero-based index used to select the placeholder icon.
  final int pageIndex;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.xl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // -- Placeholder animation area --
          _buildPlaceholderIcon(colorScheme),
          const SizedBox(height: Spacing.xl),

          // -- Title --
          Text(
            _resolveTitle(page.titleKey),
            style: theme.textTheme.headlineMedium?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.md),

          // -- Description --
          Text(
            _resolveDescription(page.descriptionKey),
            style: theme.textTheme.bodyLarge?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  /// Builds a circular container with a themed icon as a placeholder for the
  /// Lottie animation that will be added later.
  Widget _buildPlaceholderIcon(ColorScheme colorScheme) {
    final icons = [
      Icons.shield_outlined,
      Icons.wifi_lock_outlined,
      Icons.public_outlined,
      Icons.rocket_launch_outlined,
    ];

    final icon = pageIndex < icons.length ? icons[pageIndex] : Icons.star;

    return Container(
      width: 200,
      height: 200,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: colorScheme.primary.withAlpha(20),
        border: Border.all(
          color: colorScheme.primary.withAlpha(60),
          width: 2,
        ),
      ),
      child: Icon(
        icon,
        size: 80,
        color: colorScheme.primary,
      ),
    );
  }

  /// Returns a user-facing title string from the localisation key.
  ///
  /// Since the app does not yet have full l10n wiring for onboarding, we
  /// derive a readable fallback from the key itself.
  String _resolveTitle(String key) {
    return _fallbackText(key);
  }

  /// Returns a user-facing description string from the localisation key.
  String _resolveDescription(String key) {
    return _fallbackText(key);
  }

  /// Extracts a readable fallback string from a dotted localisation key.
  ///
  /// For example, `'onboarding.privacy.title'` becomes `'Privacy Title'`.
  static String _fallbackText(String key) {
    final parts = key.split('.');
    if (parts.length < 2) return key;
    // Take the last two segments and title-case them.
    return parts
        .skip(1)
        .map((s) => s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}')
        .join(' ');
  }
}
