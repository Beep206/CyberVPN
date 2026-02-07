import 'package:flutter/material.dart';

/// Design token system for CyberVPN mobile app
/// Provides centralized constants for colors, spacing, typography, and more

/// Cyberpunk-themed color palette
class CyberColors {
  CyberColors._();

  // Primary cyberpunk colors (bright variants for dark mode)
  static const Color matrixGreen = Color(0xFF00FF88);
  static const Color neonCyan = Color(0xFF00FFFF);
  static const Color neonPink = Color(0xFFFF00FF);

  // WCAG AA compliant dark variants for light mode (4.5:1 contrast on white)
  static const Color matrixGreenDark = Color(0xFF007756); // ~5.0:1 on white, better on light bg
  static const Color neonCyanDark = Color(0xFF007B7B); // 5.02:1 on white
  static const Color neonPinkDark = Color(0xFF9A009A); // 5.18:1 on white

  // Accessible gray for text/icons (improved for both themes)
  static const Color textGrayDark = Color(0xFF7B8A9A); // ~4.5:1 on dark navy (deepNavy)
  static const Color textGrayLight = Color(0xFF6B7280); // 4.83:1 on white

  // Background colors
  static const Color deepNavy = Color(0xFF0A0E1A);
  static const Color darkBg = Color(0xFF111827);

  // Pure black for OLED mode
  static const Color oledBlack = Color(0xFF000000);

  /// Returns `true` when the active theme is the cyberpunk neon theme.
  ///
  /// Detection heuristic: the cyberpunk dark theme sets the scaffold
  /// background to [deepNavy] (or pure black in OLED mode), while
  /// Material You uses dynamic or standard surface colors.
  static bool isCyberpunkTheme(BuildContext context) {
    final bg = Theme.of(context).scaffoldBackgroundColor;
    return bg == deepNavy || bg == oledBlack;
  }
}

/// Material Design color configuration
class MaterialColors {
  MaterialColors._();

  // Seed color for Material 3 ColorScheme generation
  static const Color seed = Color(0xFF00BFA5);
}

/// Spacing scale tokens
class Spacing {
  Spacing._();

  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;

  /// Returns the bottom padding needed to clear the system navigation bar
  /// plus a comfortable margin above it.
  ///
  /// Use this instead of hardcoded `SizedBox(height: 80)` at the bottom
  /// of scrollable content that sits behind a bottom navigation bar.
  static double navBarClearance(BuildContext context) {
    final viewPadding = MediaQuery.viewPaddingOf(context);
    return viewPadding.bottom + 80;
  }
}

/// Border radius tokens
class Radii {
  Radii._();

  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double lg = 16.0;
  static const double xl = 24.0;
}

/// Elevation (shadow depth) tokens
class Elevation {
  Elevation._();

  static const double none = 0.0;
  static const double low = 1.0;
  static const double medium = 2.0;
  static const double high = 4.0;
}

/// Animation duration tokens
class AnimDurations {
  AnimDurations._();

  static const Duration fast = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 500);
}

/// Cyberpunk visual effect tokens for the Cyberpunk theme.
///
/// These define standard glow, pulse, and animation parameters
/// used by CyberButton, CyberCard, GlitchText, and other cyber widgets.
class CyberEffects {
  CyberEffects._();

  // Glow parameters
  static const double glowBlurMin = 8.0;
  static const double glowBlurMax = 20.0;
  static const double glowSpreadMin = 0.0;
  static const double glowSpreadMax = 4.0;
  static const double glowOpacityMin = 0.3;
  static const double glowOpacityMax = 0.7;

  // Pulse animation
  static const Duration pulseDuration = Duration(milliseconds: 2000);
  static const Curve pulseCurve = Curves.easeInOut;

  // Glitch animation
  static const Duration glitchInterval = Duration(milliseconds: 100);
  static const double glitchMaxOffset = 2.0;

  // Neon border
  static const double neonBorderWidth = 1.5;
  static const double neonBorderWidthActive = 2.0;

  // Standard neon glow BoxShadow factory
  static List<BoxShadow> neonGlow(Color color, {double intensity = 0.5}) {
    return [
      BoxShadow(
        color: color.withValues(alpha: 0.3 * intensity),
        blurRadius: glowBlurMin + (glowBlurMax - glowBlurMin) * intensity,
        spreadRadius: glowSpreadMax * intensity,
      ),
    ];
  }
}

/// Typography token system with theme-aware TextStyle factories.
///
/// Each factory accepts a [fontFamily] parameter so that the active theme
/// (cyberpunk vs material) can supply its own typeface.  Typical usage:
///
/// ```dart
/// // Cyberpunk theme
/// AppTypography.heading(fontFamily: 'Orbitron');
/// AppTypography.data(fontFamily: 'JetBrains Mono');
///
/// // Material theme
/// AppTypography.heading(fontFamily: 'Roboto');
/// ```
class AppTypography {
  AppTypography._();

  // Letter spacing constants
  static const double headingLetterSpacing = 1.2;
  static const double bodyLetterSpacing = 0.5;
  static const double labelLetterSpacing = 0.8;
  static const double dataLetterSpacing = 1.0;

  /// Large heading style — used for page titles and hero text.
  static TextStyle heading({required String fontFamily}) => TextStyle(
        fontFamily: fontFamily,
        fontSize: 24,
        fontWeight: FontWeight.w700,
        letterSpacing: headingLetterSpacing,
      );

  /// Body text style — used for paragraphs and general content.
  static TextStyle body({required String fontFamily}) => TextStyle(
        fontFamily: fontFamily,
        fontSize: 16,
        fontWeight: FontWeight.w400,
        letterSpacing: bodyLetterSpacing,
      );

  /// Label style — used for buttons, chips, and small captions.
  static TextStyle label({required String fontFamily}) => TextStyle(
        fontFamily: fontFamily,
        fontSize: 12,
        fontWeight: FontWeight.w500,
        letterSpacing: labelLetterSpacing,
      );

  /// Data/monospace style — used for stats, codes, and technical values.
  static TextStyle data({required String fontFamily}) => TextStyle(
        fontFamily: fontFamily,
        fontSize: 14,
        fontWeight: FontWeight.w400,
        letterSpacing: dataLetterSpacing,
      );
}
