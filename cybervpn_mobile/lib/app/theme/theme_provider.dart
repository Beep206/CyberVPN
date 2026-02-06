import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/app/theme/cyberpunk_theme.dart';
import 'package:cybervpn_mobile/app/theme/dynamic_colors.dart'
    show dynamicColorProvider;
import 'package:cybervpn_mobile/app/theme/material_you_theme.dart';

// ---------------------------------------------------------------------------
// SharedPreferences provider (must be overridden in root ProviderScope)
// ---------------------------------------------------------------------------

/// Provides the pre-initialized [SharedPreferences] instance.
///
/// This must be overridden via `ProviderScope.overrides` in `main.dart`
/// with the instance obtained from `SharedPreferences.getInstance()`.
final themePrefsProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError(
    'themePrefsProvider must be overridden with a pre-initialized '
    'SharedPreferences instance in the root ProviderScope.',
  );
});

// ---------------------------------------------------------------------------
// Theme enums
// ---------------------------------------------------------------------------

/// Available theme modes for the application.
///
/// - [materialYou]: Uses Material You / Material 3 dynamic theming.
/// - [cyberpunk]: Uses the custom cyberpunk neon aesthetic.
enum AppThemeMode {
  materialYou,
  cyberpunk,
}

/// Brightness preferences.
///
/// - [system]: Follow the device brightness setting.
/// - [light]: Always use light theme.
/// - [dark]: Always use dark theme.
enum ThemeBrightness {
  system,
  light,
  dark,
}

// ---------------------------------------------------------------------------
// Theme state
// ---------------------------------------------------------------------------

/// Immutable state representing the user's theme preferences.
class ThemeState {
  const ThemeState({
    this.themeMode = AppThemeMode.materialYou,
    this.brightness = ThemeBrightness.system,
  });

  /// The selected theme style.
  final AppThemeMode themeMode;

  /// The selected brightness preference.
  final ThemeBrightness brightness;

  /// Returns a copy of this state with the given fields replaced.
  ThemeState copyWith({
    AppThemeMode? themeMode,
    ThemeBrightness? brightness,
  }) {
    return ThemeState(
      themeMode: themeMode ?? this.themeMode,
      brightness: brightness ?? this.brightness,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ThemeState &&
          runtimeType == other.runtimeType &&
          themeMode == other.themeMode &&
          brightness == other.brightness;

  @override
  int get hashCode => Object.hash(themeMode, brightness);

  @override
  String toString() =>
      'ThemeState(themeMode: $themeMode, brightness: $brightness)';
}

// ---------------------------------------------------------------------------
// SharedPreferences keys & helpers
// ---------------------------------------------------------------------------

const String _kThemeModeKey = 'theme_mode';
const String _kBrightnessKey = 'theme_brightness';

/// Reads the persisted [AppThemeMode] from [prefs].
///
/// Returns [AppThemeMode.materialYou] if no value is stored.
AppThemeMode _loadThemeMode(SharedPreferences prefs) {
  final stored = prefs.getString(_kThemeModeKey);
  if (stored == null) return AppThemeMode.materialYou;
  return AppThemeMode.values.asNameMap()[stored] ?? AppThemeMode.materialYou;
}

/// Reads the persisted [ThemeBrightness] from [prefs].
///
/// Returns [ThemeBrightness.system] if no value is stored.
ThemeBrightness _loadBrightness(SharedPreferences prefs) {
  final stored = prefs.getString(_kBrightnessKey);
  if (stored == null) return ThemeBrightness.system;
  return ThemeBrightness.values.asNameMap()[stored] ?? ThemeBrightness.system;
}

/// Persists [mode] to [prefs].
Future<void> _saveThemeMode(SharedPreferences prefs, AppThemeMode mode) {
  return prefs.setString(_kThemeModeKey, mode.name);
}

/// Persists [brightness] to [prefs].
Future<void> _saveBrightness(SharedPreferences prefs, ThemeBrightness brightness) {
  return prefs.setString(_kBrightnessKey, brightness.name);
}

// ---------------------------------------------------------------------------
// ThemeNotifier
// ---------------------------------------------------------------------------

/// Manages the application's theme state with SharedPreferences persistence.
///
/// On initialization, reads saved preferences.  Exposes [setThemeMode] and
/// [setBrightness] to update preferences and notify consumers.
class ThemeNotifier extends Notifier<ThemeState> {
  @override
  ThemeState build() {
    final prefs = ref.watch(themePrefsProvider);
    return ThemeState(
      themeMode: _loadThemeMode(prefs),
      brightness: _loadBrightness(prefs),
    );
  }

  /// Updates the theme mode and persists the change.
  void setThemeMode(AppThemeMode mode) {
    final prefs = ref.read(themePrefsProvider);
    unawaited(_saveThemeMode(prefs, mode));
    state = state.copyWith(themeMode: mode);
  }

  /// Updates the brightness preference and persists the change.
  void setBrightness(ThemeBrightness brightness) {
    final prefs = ref.read(themePrefsProvider);
    unawaited(_saveBrightness(prefs, brightness));
    state = state.copyWith(brightness: brightness);
  }
}

/// Primary theme state provider backed by [ThemeNotifier].
final themeProvider = NotifierProvider<ThemeNotifier, ThemeState>(
  ThemeNotifier.new,
);

// ---------------------------------------------------------------------------
// Derived theme data providers
// ---------------------------------------------------------------------------

/// Maps [ThemeBrightness] to Flutter's built-in [ThemeMode] for use
/// in [MaterialApp.themeMode].
ThemeMode themeBrightnessToThemeMode(ThemeBrightness pref) {
  switch (pref) {
    case ThemeBrightness.system:
      return ThemeMode.system;
    case ThemeBrightness.light:
      return ThemeMode.light;
    case ThemeBrightness.dark:
      return ThemeMode.dark;
  }
}

/// Provides a [ThemeDataPair] containing both light and dark [ThemeData]
/// based on the user's selected [AppThemeMode], plus the [ThemeMode]
/// derived from [ThemeBrightness].
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
  final themeState = ref.watch(themeProvider);
  final dynamicColors = ref.watch(dynamicColorProvider);

  final ThemeData lightTheme;
  final ThemeData darkTheme;

  switch (themeState.themeMode) {
    case AppThemeMode.materialYou:
      // Apply dynamic colors from Android 12+ when available.
      lightTheme = materialYouLightTheme(
        dynamicColorScheme: dynamicColors.light,
      );
      darkTheme = materialYouDarkTheme(
        dynamicColorScheme: dynamicColors.dark,
      );

    case AppThemeMode.cyberpunk:
      lightTheme = cyberpunkLightTheme();
      darkTheme = cyberpunkDarkTheme();
  }

  return ThemeDataPair(
    light: lightTheme,
    dark: darkTheme,
    themeMode: themeBrightnessToThemeMode(themeState.brightness),
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
