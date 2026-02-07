import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

// ---------------------------------------------------------------------------
// Cyberpunk glow helpers
// ---------------------------------------------------------------------------

/// Creates a neon glow [BoxShadow] used on cards and containers.
BoxShadow cyberpunkGlow({
  Color color = CyberColors.matrixGreen,
  double blurRadius = 8.0,
  double spreadRadius = 0.0,
  double opacity = 0.35,
}) {
  return BoxShadow(
    color: color.withAlpha((opacity * 255).round()),
    blurRadius: blurRadius,
    spreadRadius: spreadRadius,
  );
}

/// Reduced-intensity glow for the light theme.
BoxShadow cyberpunkGlowLight({
  Color color = CyberColors.matrixGreen,
  double blurRadius = 4.0,
  double spreadRadius = 0.0,
  double opacity = 0.15,
}) {
  return BoxShadow(
    color: color.withAlpha((opacity * 255).round()),
    blurRadius: blurRadius,
    spreadRadius: spreadRadius,
  );
}

// ---------------------------------------------------------------------------
// Light-theme specific background / surface colors
// ---------------------------------------------------------------------------

/// Light-mode background tones used by [cyberpunkLightTheme].
class _CyberpunkLightColors {
  _CyberpunkLightColors._();

  static const Color background = Color(0xFFF8F9FA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceContainer = Color(0xFFF0F1F3);
  static const Color onSurface = Color(0xFF1F2937);
  static const Color onSurfaceVariant = Color(0xFF6B7280);
}

// ---------------------------------------------------------------------------
// Shared TextTheme builder
// ---------------------------------------------------------------------------

/// Builds a [TextTheme] that mixes Orbitron for display/headline styles,
/// JetBrains Mono for body-small / label-small, and the platform default for
/// everything else.
TextTheme _buildCyberpunkTextTheme({required Brightness brightness}) {
  final Color defaultColor =
      brightness == Brightness.dark ? Colors.white : _CyberpunkLightColors.onSurface;

  return TextTheme(
    // Orbitron for display & headline
    displayLarge: GoogleFonts.orbitron(
      fontSize: 57,
      fontWeight: FontWeight.w700,
      color: defaultColor,
      letterSpacing: AppTypography.headingLetterSpacing,
    ),
    displayMedium: GoogleFonts.orbitron(
      fontSize: 45,
      fontWeight: FontWeight.w700,
      color: defaultColor,
      letterSpacing: AppTypography.headingLetterSpacing,
    ),
    displaySmall: GoogleFonts.orbitron(
      fontSize: 36,
      fontWeight: FontWeight.w700,
      color: defaultColor,
      letterSpacing: AppTypography.headingLetterSpacing,
    ),
    headlineLarge: GoogleFonts.orbitron(
      fontSize: 32,
      fontWeight: FontWeight.w700,
      color: defaultColor,
      letterSpacing: AppTypography.headingLetterSpacing,
    ),
    headlineMedium: GoogleFonts.orbitron(
      fontSize: 28,
      fontWeight: FontWeight.w600,
      color: defaultColor,
      letterSpacing: AppTypography.headingLetterSpacing,
    ),
    headlineSmall: GoogleFonts.orbitron(
      fontSize: 24,
      fontWeight: FontWeight.w600,
      color: defaultColor,
      letterSpacing: AppTypography.headingLetterSpacing,
    ),

    // System font for titles and body
    titleLarge: AppTypography.body(fontFamily: '').copyWith(
      fontSize: 22,
      fontWeight: FontWeight.w600,
      color: defaultColor,
    ),
    titleMedium: AppTypography.body(fontFamily: '').copyWith(
      fontSize: 16,
      fontWeight: FontWeight.w500,
      color: defaultColor,
    ),
    titleSmall: AppTypography.body(fontFamily: '').copyWith(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      color: defaultColor,
    ),
    bodyLarge: AppTypography.body(fontFamily: '').copyWith(
      fontSize: 16,
      fontWeight: FontWeight.w400,
      color: defaultColor,
    ),
    bodyMedium: AppTypography.body(fontFamily: '').copyWith(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      color: defaultColor,
    ),

    // JetBrains Mono for data / stats
    bodySmall: GoogleFonts.jetBrainsMono(
      fontSize: 12,
      color: defaultColor,
      letterSpacing: AppTypography.dataLetterSpacing,
    ),
    labelLarge: AppTypography.label(fontFamily: '').copyWith(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      color: defaultColor,
    ),
    labelMedium: AppTypography.label(fontFamily: '').copyWith(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      color: defaultColor,
    ),
    labelSmall: GoogleFonts.jetBrainsMono(
      fontSize: 11,
      color: defaultColor,
      letterSpacing: AppTypography.dataLetterSpacing,
    ),
  );
}

// ---------------------------------------------------------------------------
// Dark Cyberpunk Theme
// ---------------------------------------------------------------------------

/// Returns the **dark** cyberpunk [ThemeData].
///
/// Backgrounds use [CyberColors.deepNavy] / [CyberColors.darkBg],
/// primary accent is [CyberColors.matrixGreen], secondary [CyberColors.neonCyan],
/// tertiary [CyberColors.neonPink].  Components feature neon borders and subtle
/// glow effects via [BoxShadow].
///
/// When [oled] is `true`, backgrounds are replaced with pure black (#000000)
/// for maximum battery savings on OLED/AMOLED panels.
ThemeData cyberpunkDarkTheme({bool oled = false}) {
  final scaffoldBg = oled ? Colors.black : CyberColors.deepNavy;
  final surfaceColor = oled ? const Color(0xFF050505) : CyberColors.darkBg;
  final surfaceContainerColor =
      oled ? const Color(0xFF0A0A0A) : const Color(0xFF1E2538);

  final colorScheme = ColorScheme(
    brightness: Brightness.dark,
    primary: CyberColors.matrixGreen,
    onPrimary: CyberColors.deepNavy,
    secondary: CyberColors.neonCyan,
    onSecondary: CyberColors.deepNavy,
    tertiary: CyberColors.neonPink,
    onTertiary: CyberColors.deepNavy,
    error: const Color(0xFFFF5252),
    onError: Colors.white,
    surface: surfaceColor,
    onSurface: Colors.white,
    surfaceBright: oled ? const Color(0xFF1A1A1A) : const Color(0xFF2A3045),
    surfaceDim: oled ? Colors.black : const Color(0xFF080C16),
    surfaceContainerHighest: surfaceContainerColor,
    onSurfaceVariant: const Color(0xFFB0B8C8),
  );

  final textTheme = _buildCyberpunkTextTheme(brightness: Brightness.dark);

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: scaffoldBg,
    focusColor: CyberColors.neonCyan.withAlpha(60),
    hoverColor: CyberColors.neonCyan.withAlpha(30),
    textTheme: textTheme,

    // AppBar
    appBarTheme: AppBarTheme(
      centerTitle: true,
      elevation: 0,
      backgroundColor: scaffoldBg,
      foregroundColor: CyberColors.matrixGreen,
      titleTextStyle: textTheme.headlineSmall?.copyWith(
        color: CyberColors.matrixGreen,
      ),
    ),

    // Card
    cardTheme: CardThemeData(
      elevation: Elevation.medium,
      color: surfaceColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Radii.md),
        side: BorderSide(
          color: CyberColors.matrixGreen.withAlpha(60),
        ),
      ),
    ),

    // ElevatedButton
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: CyberColors.matrixGreen,
        foregroundColor: CyberColors.deepNavy,
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.xl,
          vertical: Spacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.sm),
        ),
        textStyle: textTheme.labelLarge?.copyWith(
          fontWeight: FontWeight.w700,
        ),
      ),
    ),

    // OutlinedButton
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: CyberColors.matrixGreen,
        side: const BorderSide(color: CyberColors.matrixGreen),
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.xl,
          vertical: Spacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.sm),
        ),
      ),
    ),

    // TextButton
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: CyberColors.neonCyan,
      ),
    ),

    // Input
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: surfaceContainerColor,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.sm + 6,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.sm),
        borderSide: BorderSide(
          color: CyberColors.matrixGreen.withAlpha(60),
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.sm),
        borderSide: BorderSide(
          color: CyberColors.matrixGreen.withAlpha(60),
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.sm),
        borderSide: const BorderSide(
          color: CyberColors.neonCyan,
          width: 2,
        ),
      ),
      hintStyle: textTheme.bodyMedium?.copyWith(
        color: CyberColors.textGrayDark,
      ),
    ),

    // BottomNavigationBar
    bottomNavigationBarTheme: BottomNavigationBarThemeData(
      backgroundColor: scaffoldBg,
      selectedItemColor: CyberColors.matrixGreen,
      unselectedItemColor: CyberColors.textGrayDark,
    ),

    // NavigationBar (Material 3)
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: scaffoldBg,
      indicatorColor: CyberColors.matrixGreen.withAlpha(30),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(color: CyberColors.matrixGreen);
        }
        return const IconThemeData(color: CyberColors.textGrayDark);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return textTheme.labelSmall?.copyWith(
            color: CyberColors.matrixGreen,
          );
        }
        return textTheme.labelSmall?.copyWith(
          color: CyberColors.textGrayDark,
        );
      }),
    ),

    // Divider
    dividerTheme: DividerThemeData(
      color: CyberColors.matrixGreen.withAlpha(30),
      thickness: 1,
    ),

    // Icon
    iconTheme: const IconThemeData(
      color: CyberColors.matrixGreen,
    ),

    // Chip
    chipTheme: ChipThemeData(
      backgroundColor: surfaceContainerColor,
      side: BorderSide(color: CyberColors.neonCyan.withAlpha(60)),
      labelStyle: textTheme.labelSmall?.copyWith(
        color: CyberColors.neonCyan,
      ),
    ),

    // Switch
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return CyberColors.matrixGreen;
        }
        return CyberColors.textGrayDark;
      }),
      trackColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return CyberColors.matrixGreen.withAlpha(60);
        }
        return surfaceContainerColor;
      }),
    ),

    // ProgressIndicator
    progressIndicatorTheme: ProgressIndicatorThemeData(
      color: CyberColors.matrixGreen,
      linearTrackColor: surfaceContainerColor,
    ),
  );
}

// ---------------------------------------------------------------------------
// Light Cyberpunk Theme
// ---------------------------------------------------------------------------

/// Returns the **light** cyberpunk [ThemeData].
///
/// Backgrounds use white / light-gray tones.  Neon accent colors use WCAG AA
/// compliant dark variants for sufficient contrast on light surfaces.
/// Card borders carry a subtle neon tint.
ThemeData cyberpunkLightTheme() {
  const colorScheme = ColorScheme(
    brightness: Brightness.light,
    primary: CyberColors.matrixGreenDark, // WCAG AA compliant on white
    onPrimary: Colors.white,
    secondary: CyberColors.neonCyanDark, // WCAG AA compliant on white
    onSecondary: Colors.white,
    tertiary: CyberColors.neonPinkDark, // WCAG AA compliant on white
    onTertiary: Colors.white,
    error: Color(0xFFD32F2F),
    onError: Colors.white,
    surface: _CyberpunkLightColors.surface,
    onSurface: _CyberpunkLightColors.onSurface,
    surfaceBright: Color(0xFFFFFFFF),
    surfaceDim: Color(0xFFE8E9EB),
    surfaceContainerHighest: _CyberpunkLightColors.surfaceContainer,
    onSurfaceVariant: _CyberpunkLightColors.onSurfaceVariant,
  );

  final textTheme = _buildCyberpunkTextTheme(brightness: Brightness.light);

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: _CyberpunkLightColors.background,
    focusColor: CyberColors.neonCyanDark.withAlpha(60),
    hoverColor: CyberColors.neonCyanDark.withAlpha(30),
    textTheme: textTheme,

    // AppBar
    appBarTheme: AppBarTheme(
      centerTitle: true,
      elevation: 0,
      backgroundColor: _CyberpunkLightColors.surface,
      foregroundColor: _CyberpunkLightColors.onSurface,
      titleTextStyle: textTheme.headlineSmall?.copyWith(
        color: _CyberpunkLightColors.onSurface,
      ),
    ),

    // Card
    cardTheme: CardThemeData(
      elevation: Elevation.low,
      color: _CyberpunkLightColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Radii.md),
        side: BorderSide(
          color: CyberColors.matrixGreenDark.withAlpha(80),
        ),
      ),
    ),

    // ElevatedButton
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: CyberColors.matrixGreenDark,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.xl,
          vertical: Spacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.sm),
        ),
        textStyle: textTheme.labelLarge?.copyWith(
          fontWeight: FontWeight.w700,
        ),
      ),
    ),

    // OutlinedButton
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: CyberColors.matrixGreenDark,
        side: const BorderSide(color: CyberColors.matrixGreenDark),
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.xl,
          vertical: Spacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.sm),
        ),
      ),
    ),

    // TextButton
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: CyberColors.neonCyanDark,
      ),
    ),

    // Input
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: _CyberpunkLightColors.surfaceContainer,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.sm + 6,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.sm),
        borderSide: BorderSide(
          color: CyberColors.matrixGreenDark.withAlpha(80),
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.sm),
        borderSide: BorderSide(
          color: CyberColors.matrixGreenDark.withAlpha(80),
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.sm),
        borderSide: const BorderSide(
          color: CyberColors.neonCyanDark,
          width: 2,
        ),
      ),
      hintStyle: textTheme.bodyMedium?.copyWith(
        color: _CyberpunkLightColors.onSurfaceVariant,
      ),
    ),

    // BottomNavigationBar
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: _CyberpunkLightColors.surface,
      selectedItemColor: CyberColors.matrixGreenDark,
      unselectedItemColor: _CyberpunkLightColors.onSurfaceVariant,
    ),

    // NavigationBar (Material 3)
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: _CyberpunkLightColors.surface,
      indicatorColor: CyberColors.matrixGreenDark.withAlpha(40),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(color: CyberColors.matrixGreenDark);
        }
        return const IconThemeData(color: _CyberpunkLightColors.onSurfaceVariant);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return textTheme.labelSmall?.copyWith(
            color: CyberColors.matrixGreenDark,
          );
        }
        return textTheme.labelSmall?.copyWith(
          color: _CyberpunkLightColors.onSurfaceVariant,
        );
      }),
    ),

    // Divider
    dividerTheme: DividerThemeData(
      color: CyberColors.matrixGreenDark.withAlpha(60),
      thickness: 1,
    ),

    // Icon
    iconTheme: const IconThemeData(
      color: _CyberpunkLightColors.onSurface,
    ),

    // Chip
    chipTheme: ChipThemeData(
      backgroundColor: _CyberpunkLightColors.surfaceContainer,
      side: BorderSide(color: CyberColors.neonCyanDark.withAlpha(80)),
      labelStyle: textTheme.labelSmall?.copyWith(
        color: _CyberpunkLightColors.onSurface,
      ),
    ),

    // Switch
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return CyberColors.matrixGreenDark;
        }
        return _CyberpunkLightColors.onSurfaceVariant;
      }),
      trackColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return CyberColors.matrixGreenDark.withAlpha(80);
        }
        return _CyberpunkLightColors.surfaceContainer;
      }),
    ),

    // ProgressIndicator
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: CyberColors.matrixGreenDark,
      linearTrackColor: _CyberpunkLightColors.surfaceContainer,
    ),
  );
}
