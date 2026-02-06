import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

/// Branded splash / loading screen shown while the app initialises
/// authentication state, onboarding status, and deferred services.
///
/// The screen displays the CyberVPN logo text using the cyberpunk colour
/// palette and a [CircularProgressIndicator] below it.  It is intentionally
/// minimal so it renders instantly on cold start.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final brightness = theme.brightness;
    final isDark = brightness == Brightness.dark;

    // Pick brand colours that work in both light and dark modes.
    final primaryColor =
        isDark ? CyberColors.matrixGreen : CyberColors.matrixGreenDark;
    final backgroundColor =
        isDark ? CyberColors.deepNavy : theme.colorScheme.surface;
    final subtitleColor =
        isDark ? CyberColors.textGrayDark : CyberColors.textGrayLight;

    return Scaffold(
      backgroundColor: backgroundColor,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // -- Brand icon -----------------------------------------------
            Icon(
              Icons.shield_outlined,
              size: 72,
              color: primaryColor,
            ),
            const SizedBox(height: Spacing.md),

            // -- Brand name -----------------------------------------------
            Text(
              'CyberVPN',
              style: theme.textTheme.headlineMedium?.copyWith(
                color: primaryColor,
                fontWeight: FontWeight.w700,
                letterSpacing: AppTypography.headingLetterSpacing,
              ),
            ),
            const SizedBox(height: Spacing.sm),

            // -- Tagline --------------------------------------------------
            Text(
              'Secure. Private. Fast.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: subtitleColor,
                letterSpacing: AppTypography.bodyLetterSpacing,
              ),
            ),
            const SizedBox(height: Spacing.xl),

            // -- Loading indicator ----------------------------------------
            SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                valueColor: AlwaysStoppedAnimation<Color>(primaryColor),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
