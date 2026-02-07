import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/entities/onboarding_page.dart';

/// Renders a single onboarding page with a Lottie animation, title, and
/// description.
///
/// Each page displays a themed Lottie animation that auto-plays when the
/// page is visible and pauses when hidden.
class OnboardingPageWidget extends StatelessWidget {
  const OnboardingPageWidget({
    super.key,
    required this.page,
    required this.pageIndex,
    this.isVisible = true,
  });

  /// The onboarding page data to display.
  final OnboardingPage page;

  /// Zero-based index used to select the Lottie animation asset.
  final int pageIndex;

  /// Whether this page is currently visible in the PageView.
  /// Controls auto-play/pause of the Lottie animation.
  final bool isVisible;

  /// Lottie animation asset paths corresponding to each onboarding page.
  static const _lottieAssets = [
    'assets/animations/onboarding_privacy.json',
    'assets/animations/onboarding_connect.json',
    'assets/animations/onboarding_globe.json',
    'assets/animations/get_started.json',
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.xl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // -- Lottie animation area --
          SizedBox(
            width: 200,
            height: 200,
            child: pageIndex < _lottieAssets.length
                ? Lottie.asset(
                    _lottieAssets[pageIndex],
                    width: 200,
                    height: 200,
                    fit: BoxFit.contain,
                    animate: isVisible && !disableAnimations,
                    errorBuilder: (_, __, ___) =>
                        _buildFallbackIcon(colorScheme),
                  )
                : _buildFallbackIcon(colorScheme),
          ),
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

  /// Fallback icon for pages beyond the known Lottie assets.
  Widget _buildFallbackIcon(ColorScheme colorScheme) {
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: colorScheme.primary.withAlpha(20),
        border: Border.all(
          color: colorScheme.primary.withAlpha(60),
          width: 2,
        ),
      ),
      child: Icon(
        Icons.star,
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
