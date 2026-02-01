import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/app/theme/theme_provider.dart';

void main() {
  // ── AppThemeMode enum ──────────────────────────────────────────────────

  group('AppThemeMode', () {
    test('has materialYou and cyberpunk values', () {
      expect(AppThemeMode.values, containsAll([
        AppThemeMode.materialYou,
        AppThemeMode.cyberpunk,
      ]));
      expect(AppThemeMode.values.length, 2);
    });
  });

  // ── ThemeBrightness enum ───────────────────────────────────────────────

  group('ThemeBrightness', () {
    test('has system, light, dark values', () {
      expect(ThemeBrightness.values, containsAll([
        ThemeBrightness.system,
        ThemeBrightness.light,
        ThemeBrightness.dark,
      ]));
      expect(ThemeBrightness.values.length, 3);
    });
  });

  // ── ThemeState ─────────────────────────────────────────────────────────

  group('ThemeState', () {
    test('default constructor uses materialYou and system', () {
      const state = ThemeState();
      expect(state.themeMode, AppThemeMode.materialYou);
      expect(state.brightness, ThemeBrightness.system);
    });

    test('copyWith replaces themeMode', () {
      const state = ThemeState();
      final updated = state.copyWith(themeMode: AppThemeMode.cyberpunk);
      expect(updated.themeMode, AppThemeMode.cyberpunk);
      expect(updated.brightness, ThemeBrightness.system);
    });

    test('copyWith replaces brightness', () {
      const state = ThemeState();
      final updated = state.copyWith(brightness: ThemeBrightness.dark);
      expect(updated.themeMode, AppThemeMode.materialYou);
      expect(updated.brightness, ThemeBrightness.dark);
    });

    test('equality', () {
      const a = ThemeState(
        themeMode: AppThemeMode.cyberpunk,
        brightness: ThemeBrightness.dark,
      );
      const b = ThemeState(
        themeMode: AppThemeMode.cyberpunk,
        brightness: ThemeBrightness.dark,
      );
      expect(a, equals(b));
      expect(a.hashCode, b.hashCode);
    });

    test('inequality', () {
      const a = ThemeState(
        themeMode: AppThemeMode.materialYou,
        brightness: ThemeBrightness.light,
      );
      const b = ThemeState(
        themeMode: AppThemeMode.cyberpunk,
        brightness: ThemeBrightness.light,
      );
      expect(a, isNot(equals(b)));
    });
  });

  // ── themeBrightnessToThemeMode ─────────────────────────────────────────

  group('themeBrightnessToThemeMode', () {
    test('system maps to ThemeMode.system', () {
      expect(
        themeBrightnessToThemeMode(ThemeBrightness.system),
        ThemeMode.system,
      );
    });

    test('light maps to ThemeMode.light', () {
      expect(
        themeBrightnessToThemeMode(ThemeBrightness.light),
        ThemeMode.light,
      );
    });

    test('dark maps to ThemeMode.dark', () {
      expect(
        themeBrightnessToThemeMode(ThemeBrightness.dark),
        ThemeMode.dark,
      );
    });
  });

  // ── ThemeNotifier ──────────────────────────────────────────────────────

  group('ThemeNotifier', () {
    late ProviderContainer container;

    Future<ProviderContainer> createContainer({
      Map<String, Object>? prefsValues,
    }) async {
      SharedPreferences.setMockInitialValues(prefsValues ?? {});
      final prefs = await SharedPreferences.getInstance();
      return ProviderContainer(
        overrides: [
          themePrefsProvider.overrideWithValue(prefs),
        ],
      );
    }

    tearDown(() {
      container.dispose();
    });

    test('initializes with defaults when no prefs exist', () async {
      container = await createContainer();
      final state = container.read(themeProvider);
      expect(state.themeMode, AppThemeMode.materialYou);
      expect(state.brightness, ThemeBrightness.system);
    });

    test('initializes from persisted preferences', () async {
      container = await createContainer(prefsValues: {
        'theme_mode': 'cyberpunk',
        'theme_brightness': 'dark',
      });
      final state = container.read(themeProvider);
      expect(state.themeMode, AppThemeMode.cyberpunk);
      expect(state.brightness, ThemeBrightness.dark);
    });

    test('setThemeMode updates state and persists', () async {
      container = await createContainer();

      final notifier = container.read(themeProvider.notifier);
      notifier.setThemeMode(AppThemeMode.cyberpunk);

      final state = container.read(themeProvider);
      expect(state.themeMode, AppThemeMode.cyberpunk);

      // Verify persistence
      final prefs = container.read(themePrefsProvider);
      expect(prefs.getString('theme_mode'), 'cyberpunk');
    });

    test('setBrightness updates state and persists', () async {
      container = await createContainer();

      final notifier = container.read(themeProvider.notifier);
      notifier.setBrightness(ThemeBrightness.light);

      final state = container.read(themeProvider);
      expect(state.brightness, ThemeBrightness.light);

      // Verify persistence
      final prefs = container.read(themePrefsProvider);
      expect(prefs.getString('theme_brightness'), 'light');
    });

    test('handles invalid persisted values gracefully', () async {
      container = await createContainer(prefsValues: {
        'theme_mode': 'invalid_value',
        'theme_brightness': 'garbage',
      });
      final state = container.read(themeProvider);
      // Should fall back to defaults
      expect(state.themeMode, AppThemeMode.materialYou);
      expect(state.brightness, ThemeBrightness.system);
    });
  });

  // ── currentThemeDataProvider ───────────────────────────────────────────

  group('currentThemeDataProvider', () {
    Future<ProviderContainer> createContainer({
      Map<String, Object>? prefsValues,
    }) async {
      SharedPreferences.setMockInitialValues(prefsValues ?? {});
      final prefs = await SharedPreferences.getInstance();
      return ProviderContainer(
        overrides: [
          themePrefsProvider.overrideWithValue(prefs),
        ],
      );
    }

    test('returns ThemeDataPair with Material You themes by default', () async {
      final container = await createContainer();
      addTearDown(container.dispose);

      final pair = container.read(currentThemeDataProvider);
      expect(pair.light, isA<ThemeData>());
      expect(pair.dark, isA<ThemeData>());
      expect(pair.themeMode, ThemeMode.system);
      expect(pair.light.brightness, Brightness.light);
      expect(pair.dark.brightness, Brightness.dark);
    });

    test('returns cyberpunk themes when mode is cyberpunk', () async {
      final container = await createContainer(prefsValues: {
        'theme_mode': 'cyberpunk',
        'theme_brightness': 'dark',
      });
      addTearDown(container.dispose);

      final pair = container.read(currentThemeDataProvider);
      expect(pair.themeMode, ThemeMode.dark);
      expect(pair.light.brightness, Brightness.light);
      expect(pair.dark.brightness, Brightness.dark);
    });

    test('themeMode reflects brightness setting', () async {
      final container = await createContainer(prefsValues: {
        'theme_brightness': 'light',
      });
      addTearDown(container.dispose);

      final pair = container.read(currentThemeDataProvider);
      expect(pair.themeMode, ThemeMode.light);
    });

    test('updates when notifier changes mode', () async {
      final container = await createContainer();
      addTearDown(container.dispose);

      // Initially Material You
      var pair = container.read(currentThemeDataProvider);
      expect(pair.themeMode, ThemeMode.system);

      // Switch to cyberpunk + dark
      container.read(themeProvider.notifier).setThemeMode(AppThemeMode.cyberpunk);
      container.read(themeProvider.notifier).setBrightness(ThemeBrightness.dark);

      pair = container.read(currentThemeDataProvider);
      expect(pair.themeMode, ThemeMode.dark);
    });
  });
}
