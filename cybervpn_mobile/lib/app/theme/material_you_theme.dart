import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';

// ---------------------------------------------------------------------------
// Material You ColorScheme builders
// ---------------------------------------------------------------------------

/// Creates a **light** Material You [ColorScheme].
///
/// If [dynamicColorScheme] is provided (from [DynamicColorBuilder] on
/// Android 12+), it is returned directly.  Otherwise a scheme is generated
/// from [MaterialColors.seed].
ColorScheme _lightColorScheme({ColorScheme? dynamicColorScheme}) {
  return dynamicColorScheme ??
      ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.light,
      );
}

/// Creates a **dark** Material You [ColorScheme].
///
/// If [dynamicColorScheme] is provided (from [DynamicColorBuilder] on
/// Android 12+), it is returned directly.  Otherwise a scheme is generated
/// from [MaterialColors.seed].
ColorScheme _darkColorScheme({ColorScheme? dynamicColorScheme}) {
  return dynamicColorScheme ??
      ColorScheme.fromSeed(
        seedColor: MaterialColors.seed,
        brightness: Brightness.dark,
      );
}

// ---------------------------------------------------------------------------
// VPN state color extension
// ---------------------------------------------------------------------------

/// Semantic colors for VPN connection states derived from the active
/// [ColorScheme].
extension VpnStateColors on ColorScheme {
  /// Color representing an active, healthy connection (green accent).
  Color get vpnConnected =>
      brightness == Brightness.dark ? const Color(0xFF66BB6A) : const Color(0xFF2E7D32);

  /// Color representing an idle / disconnected state (neutral).
  Color get vpnDisconnected => onSurfaceVariant;

  /// Color representing an error / failed connection state (red).
  Color get vpnError => error;
}

// ---------------------------------------------------------------------------
// Component theme helpers (shared between light & dark)
// ---------------------------------------------------------------------------

/// Builds a [ThemeData] for the Material You style, reusing [colorScheme].
ThemeData _buildMaterialYouTheme(ColorScheme colorScheme) {
  final bool isDark = colorScheme.brightness == Brightness.dark;

  return ThemeData(
    useMaterial3: true,
    brightness: colorScheme.brightness,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: colorScheme.surface,

    // --- AppBar ---
    appBarTheme: AppBarTheme(
      centerTitle: true,
      elevation: 0,
      backgroundColor: colorScheme.surface,
      foregroundColor: colorScheme.onSurface,
      surfaceTintColor: colorScheme.surfaceTint,
    ),

    // --- Card (radius 16) ---
    cardTheme: CardThemeData(
      elevation: isDark ? Elevation.medium : Elevation.low,
      color: colorScheme.surfaceContainerHighest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Radii.lg),
      ),
    ),

    // --- ElevatedButton (radius 12) ---
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: colorScheme.primary,
        foregroundColor: colorScheme.onPrimary,
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.xl,
          vertical: Spacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.md),
        ),
      ),
    ),

    // --- OutlinedButton (radius 12) ---
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: colorScheme.primary,
        side: BorderSide(color: colorScheme.outline),
        padding: const EdgeInsets.symmetric(
          horizontal: Spacing.xl,
          vertical: Spacing.md,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.md),
        ),
      ),
    ),

    // --- TextButton ---
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: colorScheme.primary,
      ),
    ),

    // --- InputDecoration (filled, radius 12) ---
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: colorScheme.surfaceContainerHighest,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.sm + 6,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.md),
        borderSide: BorderSide(color: colorScheme.outline),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.md),
        borderSide: BorderSide(color: colorScheme.outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Radii.md),
        borderSide: BorderSide(color: colorScheme.primary, width: 2),
      ),
    ),

    // --- BottomNavigationBar ---
    bottomNavigationBarTheme: BottomNavigationBarThemeData(
      backgroundColor: colorScheme.surface,
      selectedItemColor: colorScheme.primary,
      unselectedItemColor: colorScheme.onSurfaceVariant,
    ),

    // --- NavigationBar (Material 3) ---
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: colorScheme.surface,
      indicatorColor: colorScheme.secondaryContainer,
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return IconThemeData(color: colorScheme.onSecondaryContainer);
        }
        return IconThemeData(color: colorScheme.onSurfaceVariant);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: colorScheme.onSurface,
          );
        }
        return TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: colorScheme.onSurfaceVariant,
        );
      }),
    ),

    // --- Divider ---
    dividerTheme: DividerThemeData(
      color: colorScheme.outlineVariant,
      thickness: 1,
    ),

    // --- Icon ---
    iconTheme: IconThemeData(
      color: colorScheme.onSurface,
    ),

    // --- Chip ---
    chipTheme: ChipThemeData(
      backgroundColor: colorScheme.surfaceContainerHighest,
      side: BorderSide(color: colorScheme.outline),
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: colorScheme.onSurface,
      ),
    ),

    // --- Switch ---
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return colorScheme.onPrimary;
        }
        return colorScheme.outline;
      }),
      trackColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return colorScheme.primary;
        }
        return colorScheme.surfaceContainerHighest;
      }),
    ),

    // --- ProgressIndicator ---
    progressIndicatorTheme: ProgressIndicatorThemeData(
      color: colorScheme.primary,
      linearTrackColor: colorScheme.surfaceContainerHighest,
    ),
  );
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/// Returns a **light** Material You [ThemeData].
///
/// Pass an optional [dynamicColorScheme] obtained from [DynamicColorBuilder]
/// to apply the user's wallpaper-based palette on Android 12+.  When `null`,
/// the theme falls back to [MaterialColors.seed] generated scheme.
ThemeData materialYouLightTheme({ColorScheme? dynamicColorScheme}) {
  final colorScheme = _lightColorScheme(dynamicColorScheme: dynamicColorScheme);
  return _buildMaterialYouTheme(colorScheme);
}

/// Returns a **dark** Material You [ThemeData].
///
/// Pass an optional [dynamicColorScheme] obtained from [DynamicColorBuilder]
/// to apply the user's wallpaper-based palette on Android 12+.  When `null`,
/// the theme falls back to [MaterialColors.seed] generated scheme.
ThemeData materialYouDarkTheme({ColorScheme? dynamicColorScheme}) {
  final colorScheme = _darkColorScheme(dynamicColorScheme: dynamicColorScheme);
  return _buildMaterialYouTheme(colorScheme);
}
