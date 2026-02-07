import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/app/theme/dynamic_colors.dart'
    show dynamicColorProvider;
import 'package:cybervpn_mobile/app/theme/material_you_theme.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

// ---------------------------------------------------------------------------
// Derived theme data provider (unified on settingsProvider)
// ---------------------------------------------------------------------------

/// Provides a [ThemeDataPair] containing both light and dark [ThemeData]
/// based on the user's [AppSettings], plus the [ThemeMode] derived from
/// [AppBrightness].
///
/// This is the single source of truth for theming in the app.
/// It watches [settingsProvider] so any change to theme mode, brightness,
/// OLED mode, or dynamic color preference triggers a rebuild.
///
/// Consumers should use this to configure [MaterialApp]:
/// ```dart
/// final themePair = ref.watch(currentThemeDataProvider);
/// MaterialApp(
///   theme: themePair.light,
///   darkTheme: themePair.dark,
///   themeMode: themePair.themeMode,
/// );
/// ```
final currentThemeDataProvider = Provider<ThemeDataPair>((ref) {
  final asyncSettings = ref.watch(settingsProvider);
  final settings = asyncSettings.value ?? const AppSettings();
  final dynamicColors = ref.watch(dynamicColorProvider);

  final ThemeData lightTheme;
  final ThemeData darkTheme;

  switch (settings.themeMode) {
    case AppThemeMode.materialYou:
      final useDynamic = settings.dynamicColor;
      lightTheme = materialYouLightTheme(
        dynamicColorScheme: useDynamic ? dynamicColors.light : null,
      );
      darkTheme = materialYouDarkTheme(
        dynamicColorScheme: useDynamic ? dynamicColors.dark : null,
      );
    case AppThemeMode.cyberpunk:
      lightTheme = cyberpunkLightTheme();
      darkTheme = cyberpunkDarkTheme(oled: settings.oledMode);
  }

  final themeMode = switch (settings.brightness) {
    AppBrightness.system => ThemeMode.system,
    AppBrightness.light => ThemeMode.light,
    AppBrightness.dark => ThemeMode.dark,
  };

  return ThemeDataPair(
    light: lightTheme,
    dark: darkTheme,
    themeMode: themeMode,
  );
});

/// Groups a light theme, dark theme, and [ThemeMode] for easy consumption
/// in [MaterialApp.router] or [MaterialApp].
class ThemeDataPair {
  const ThemeDataPair({
    required this.light,
    required this.dark,
    required this.themeMode,
  });

  /// Light [ThemeData] to use as `MaterialApp.theme`.
  final ThemeData light;

  /// Dark [ThemeData] to use as `MaterialApp.darkTheme`.
  final ThemeData dark;

  /// The [ThemeMode] controlling which theme is active.
  final ThemeMode themeMode;
}
