import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';

// ---------------------------------------------------------------------------
// ThemePreviewCard
// ---------------------------------------------------------------------------

/// A compact preview card showing how a theme combination looks.
///
/// Displays a 120x80px miniature mockup of the connection screen with
/// theme-specific colors for background, connect button, and accent bar.
/// Used in appearance settings to preview Material You and Cyberpunk themes.
///
/// Example:
/// ```dart
/// ThemePreviewCard(
///   theme: AppThemeMode.cyberpunk,
///   isSelected: true,
///   onTap: () => selectTheme(AppThemeMode.cyberpunk),
/// )
/// ```
class ThemePreviewCard extends StatelessWidget {
  const ThemePreviewCard({
    super.key,
    required this.theme,
    required this.isSelected,
    required this.onTap,
  });

  /// The theme mode to preview.
  final AppThemeMode theme;

  /// Whether this theme is currently selected.
  final bool isSelected;

  /// Callback invoked when the card is tapped.
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = _getPreviewColors(theme);
    final borderColor = isSelected
        ? colors.accentColor
        : Colors.grey.withValues(alpha: 0.2);
    final borderWidth = isSelected ? 2.0 : 1.0;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: AnimDurations.fast,
        width: 120,
        height: 80,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(Radii.sm),
          border: Border.all(
            color: borderColor,
            width: borderWidth,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: colors.accentColor.withValues(alpha: 0.2),
                    blurRadius: 8,
                    spreadRadius: 0,
                  ),
                ]
              : null,
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(
          children: [
            // Background
            Positioned.fill(
              child: ColoredBox(color: colors.backgroundColor),
            ),

            // Connect button mockup (centered)
            Positioned(
              left: 35,
              right: 35,
              top: 25,
              bottom: 30,
              child: Container(
                decoration: BoxDecoration(
                  color: colors.buttonColor,
                  borderRadius: BorderRadius.circular(25),
                ),
              ),
            ),

            // Accent bar at bottom
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Container(
                height: 4,
                color: colors.accentColor,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Maps theme mode to preview colors.
  _PreviewColors _getPreviewColors(AppThemeMode theme) {
    switch (theme) {
      case AppThemeMode.cyberpunk:
        return const _PreviewColors(
          backgroundColor: CyberColors.deepNavy,
          buttonColor: CyberColors.matrixGreen,
          accentColor: CyberColors.neonCyan,
        );

      case AppThemeMode.materialYou:
        // Use Material 3 colors derived from seed color
        // These approximate the ColorScheme.fromSeed output
        return const _PreviewColors(
          backgroundColor: Color(0xFFFCFCFC), // Light surface
          buttonColor: Color(0xFF00897B), // Primary derived from seed
          accentColor: Color(0xFF4DB6AC), // Secondary/accent tone
        );
    }
  }
}

// ---------------------------------------------------------------------------
// _PreviewColors
// ---------------------------------------------------------------------------

/// Color set for theme preview rendering.
class _PreviewColors {
  const _PreviewColors({
    required this.backgroundColor,
    required this.buttonColor,
    required this.accentColor,
  });

  /// Background color for the preview.
  final Color backgroundColor;

  /// Color for the connect button mockup.
  final Color buttonColor;

  /// Color for the accent bar at the bottom.
  final Color accentColor;
}
