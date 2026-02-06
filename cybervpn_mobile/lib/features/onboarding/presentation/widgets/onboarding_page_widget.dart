import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
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
    final l10n = AppLocalizations.of(context);

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
            _resolveTitle(l10n, page.titleKey),
            style: theme.textTheme.headlineMedium?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.md),

          // -- Description --
          Text(
            _resolveDescription(l10n, page.descriptionKey),
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

  /// Maps a dotted localisation key (e.g. `onboarding.privacy.title`) to the
  /// corresponding [AppLocalizations] title getter.
  String _resolveTitle(AppLocalizations l10n, String key) {
    return _l10nTitleMap(l10n)[key] ?? _fallbackText(key);
  }

  /// Maps a dotted localisation key to the corresponding description getter.
  String _resolveDescription(AppLocalizations l10n, String key) {
    return _l10nDescriptionMap(l10n)[key] ?? _fallbackText(key);
  }

  /// Title lookup from dotted key to [AppLocalizations] getter.
  static Map<String, String> _l10nTitleMap(AppLocalizations l10n) => {
        'onboarding.privacy.title': l10n.onboardingPrivacyTitle,
        'onboarding.connect.title': l10n.onboardingConnectTitle,
        'onboarding.globe.title': l10n.onboardingGlobeTitle,
        'onboarding.getStarted.title': l10n.onboardingGetStartedTitle,
      };

  /// Description lookup from dotted key to [AppLocalizations] getter.
  static Map<String, String> _l10nDescriptionMap(AppLocalizations l10n) => {
        'onboarding.privacy.description': l10n.onboardingPrivacyDescription,
        'onboarding.connect.description': l10n.onboardingConnectDescription,
        'onboarding.globe.description': l10n.onboardingGlobeDescription,
        'onboarding.getStarted.description':
            l10n.onboardingGetStartedDescription,
      };

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
