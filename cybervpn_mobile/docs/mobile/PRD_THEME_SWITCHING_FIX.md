# PRD: Theme Switching Fix -- Unified Theme State Management

**Status:** Draft
**Priority:** P0 (Critical)
**Author:** AI Analysis Team (6 parallel agents)
**Date:** 2026-02-07
**Affects:** CyberVPN Mobile (Flutter)

---

## 1. Problem Statement

Theme switching between Material You, Cyberpunk Dark, and Cyberpunk Light **does not work**. When a user selects a theme in the Appearance screen, the `MaterialApp` never updates. The app continues rendering the stale theme from initialization.

### Root Cause

Two completely independent state management systems manage theme preferences with **zero synchronization**:

| Aspect | System A (`themeProvider`) | System B (`settingsProvider`) |
|--------|---------------------------|-------------------------------|
| File | `lib/app/theme/theme_provider.dart` | `lib/features/settings/presentation/providers/settings_provider.dart` |
| Consumed by | `MaterialApp` in `app.dart:63` | `AppearanceScreen` UI |
| SP Keys | `theme_mode`, `theme_brightness`, `theme_oled_mode` | `settings.themeMode`, `settings.brightness` |
| Default theme | `materialYou` | `cyberpunk` |
| Theme enum | `AppThemeMode` (theme_provider.dart:34) | `AppThemeMode` (app_settings.dart:6) |
| Brightness enum | `ThemeBrightness` (theme_provider.dart:44) | `AppBrightness` (app_settings.dart:12) |
| Mutator callers | **None (dead code)** | AppearanceScreen, SettingsScreen |

**Data flow diagram showing the break:**

```
User taps "Cyberpunk" in AppearanceScreen
     |
     v
SettingsNotifier.updateThemeMode(AppThemeMode.cyberpunk)     [System B]
     |
     v
SettingsRepository writes "settings.themeMode" = "cyberpunk"
     |
     v
settingsProvider.state updated --> AppearanceScreen rebuilds (shows Cyberpunk selected)
     |
     X  NO BRIDGE -- No ref.watch, ref.listen, or shared key
     |
ThemeNotifier.state UNCHANGED --> themeProvider still has materialYou
     |
     v
currentThemeDataProvider UNCHANGED --> MaterialApp still renders Material You
```

---

## 2. Complete Bug Inventory

### BUG-1: Disconnected State Systems (CRITICAL)

**Impact:** Theme switching is completely non-functional.

- `AppearanceScreen` calls `settingsProvider.notifier.updateThemeMode()` which writes to `settings.themeMode`
- `MaterialApp` watches `currentThemeDataProvider` which derives from `themeProvider` reading `theme_mode`
- Different keys, different providers, zero bridge code
- **Files:** `theme_provider.dart:105-107`, `settings_repository_impl.dart:22-23`, `app.dart:63`

### BUG-2: Different SharedPreferences Keys (CRITICAL)

**Impact:** Even after app restart, themes are read from stale System A keys.

| Setting | System A Key | System B Key |
|---------|-------------|-------------|
| Theme mode | `theme_mode` | `settings.themeMode` |
| Brightness | `theme_brightness` | `settings.brightness` |
| OLED mode | `theme_oled_mode` | **(not persisted)** |

### BUG-3: Default Theme Mismatch (MODERATE)

**Impact:** Fresh install shows Material You rendered but Cyberpunk selected in settings UI.

- `ThemeState` defaults to `AppThemeMode.materialYou` (theme_provider.dart:57)
- `AppSettings` defaults to `AppThemeMode.cyberpunk` (app_settings.dart:71)

### BUG-4: `dynamicColor` Toggle is Cosmetic (MODERATE)

**Impact:** User toggles Dynamic Color on/off but nothing changes visually.

- `AppearanceScreen` has a Dynamic Color toggle calling `notifier.updateDynamicColor(value)`
- `currentThemeDataProvider` unconditionally passes `dynamicColors.light/dark` to Material You themes
- No conditional check on `settings.dynamicColor` flag
- **Files:** `appearance_screen.dart:164-178`, `theme_provider.dart:231-238`

### BUG-5: Duplicate `AppThemeMode` Enum Definitions (MODERATE)

**Impact:** Type confusion, fragile code, potential import errors.

- `enum AppThemeMode { materialYou, cyberpunk }` defined in **two separate files**
- `ThemeBrightness` vs `AppBrightness` -- same values, different type names, no mapping
- **Files:** `theme_provider.dart:34,44` and `app_settings.dart:6,12`

### BUG-6: 5 AppSettings Fields Not Persisted (MODERATE)

**Impact:** OLED mode, scanline effect, text scale, haptics, trusted WiFi reset to defaults on every app restart.

| Field | In AppSettings | In SettingsRepositoryImpl | Persisted? |
|-------|---------------|--------------------------|-----------|
| `oledMode` | Yes (line 74) | No key constant | **NO** |
| `scanlineEffect` | Yes (line 75) | No key constant | **NO** |
| `textScale` | Yes (line 76) | No key constant | **NO** |
| `hapticsEnabled` | Yes (line 115) | No key constant | **NO** |
| `trustedWifiNetworks` | Yes (line 85) | No key constant | **NO** |

**File:** `settings_repository_impl.dart` -- missing from `_allKeys`, `getSettings()`, and `updateSettings()`

### BUG-7: `LocalStorageWrapper.themeKey` Collision (MINOR)

**Impact:** Potential third writer to `theme_mode` key.

- `LocalStorageWrapper.themeKey = 'theme_mode'` (local_storage.dart:60)
- Same value as `ThemeNotifier._kThemeModeKey`
- If any code path uses `LocalStorageWrapper` for theme, it silently writes to System A keys

### BUG-8: DynamicColorBuilder Post-Frame Flash (MINOR)

**Impact:** One-frame visual flash on Android 12+ first launch.

- `_syncDynamicColors()` in `app.dart:143-154` uses `addPostFrameCallback`
- First frame renders without wallpaper-derived colors, second frame corrects
- Visible as brief color jump on app startup

### BUG-9: `ThemeNotifier` Mutators are Dead Code (MINOR)

**Impact:** Code maintenance confusion.

- `setThemeMode()`, `setBrightness()`, `setOledMode()` are defined but never called from any UI
- Grep across entire codebase confirms zero external callers

---

## 3. Architectural Decision

### Recommendation: Eliminate System A, Unify on System B

**Rationale:**
- `settingsProvider` is already the single source of truth for **all** user-configurable settings (14 consumers across the app)
- `settingsProvider` uses the Clean Architecture repository pattern with optimistic updates and rollback
- `ThemeNotifier` mutators are dead code -- no UI calls them
- Unification eliminates 2 enum types, 3 SharedPreferences keys, and ~140 lines of dead code

**Alternative considered (bridge the two systems):** Adding `ref.listen(settingsProvider)` in `ThemeNotifier` to sync changes. Rejected because it maintains fragile coupling between two systems that should not both exist, does not fix the default mismatch, and does not address the 5 missing persistence fields.

---

## 4. Implementation Plan

### Phase 1: Fix the Bug (Critical Path)

#### 1.1 Rewrite `currentThemeDataProvider` to derive from `settingsProvider`

**File:** `lib/app/theme/theme_provider.dart`

Replace the current provider that watches `themeProvider` with one that watches `settingsProvider`:

```dart
final currentThemeDataProvider = Provider<ThemeDataPair>((ref) {
  final asyncSettings = ref.watch(settingsProvider);
  final settings = asyncSettings.valueOrNull ?? const AppSettings();
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

  return ThemeDataPair(light: lightTheme, dark: darkTheme, themeMode: themeMode);
});
```

#### 1.2 Add missing persistence to `SettingsRepositoryImpl`

**File:** `lib/features/settings/data/repositories/settings_repository_impl.dart`

Add key constants and read/write logic for:
- `settings.oledMode` (bool)
- `settings.scanlineEffect` (bool)
- `settings.textScale` (string enum)
- `settings.hapticsEnabled` (bool)
- `settings.trustedWifiNetworks` (string list, JSON-encoded)

#### 1.3 Align default theme mode

**File:** `lib/features/settings/domain/entities/app_settings.dart`

Ensure `AppSettings.themeMode` default matches what the app should show on fresh install. Recommended: `cyberpunk` (matches current `app_settings.dart` default).

#### 1.4 Gate dynamic colors on `settings.dynamicColor` flag

In the rewritten `currentThemeDataProvider`, conditionally pass `dynamicColors` only when `settings.dynamicColor == true` (already shown in 1.1 above).

### Phase 2: Delete Dead Code

#### 2.1 Remove from `theme_provider.dart`:
- `ThemeNotifier` class
- `ThemeState` class
- `themeProvider` provider
- `themePrefsProvider` provider
- `AppThemeMode` enum (duplicate)
- `ThemeBrightness` enum (replaced by `AppBrightness`)
- SharedPreferences key constants (`_kThemeModeKey`, `_kBrightnessKey`, `_kOledModeKey`)

**Keep in `theme_provider.dart`:**
- `ThemeDataPair` class
- `currentThemeDataProvider` (rewritten)

#### 2.2 Remove `themePrefsProvider` override from `buildProviderOverrides()`

**File:** `lib/core/di/providers.dart` (line ~542)

#### 2.3 Remove `LocalStorageWrapper.themeKey`

**File:** `lib/core/storage/local_storage.dart` (line 60)

Verify no code references it first. If referenced, redirect to `settingsProvider`.

#### 2.4 Update `ThemePreviewCard` imports

**File:** `lib/features/settings/presentation/widgets/theme_preview_card.dart`

Change `AppThemeMode` import from `theme_provider.dart` to `app_settings.dart`.

### Phase 3: Data Migration

#### 3.1 One-time migration of existing user preferences

In `SettingsRepositoryImpl.getSettings()`, add migration logic:

```dart
// Migrate legacy theme keys (one-time)
if (!_prefs.containsKey(_kThemeMode)) {
  final legacyMode = _prefs.getString('theme_mode');
  if (legacyMode != null) {
    await _prefs.setString(_kThemeMode, legacyMode);
    await _prefs.setString(_kBrightness, _prefs.getString('theme_brightness') ?? 'system');
    await _prefs.setBool(_kOledMode, _prefs.getBool('theme_oled_mode') ?? false);
    // Clean up legacy keys
    await _prefs.remove('theme_mode');
    await _prefs.remove('theme_brightness');
    await _prefs.remove('theme_oled_mode');
  }
}
```

---

## 5. Files to Modify

| File | Action | Phase |
|------|--------|-------|
| `lib/app/theme/theme_provider.dart` | Rewrite `currentThemeDataProvider`, delete dead code | 1.1, 2.1 |
| `lib/features/settings/data/repositories/settings_repository_impl.dart` | Add 5 missing persistence keys + migration | 1.2, 3.1 |
| `lib/features/settings/domain/entities/app_settings.dart` | Verify/align default | 1.3 |
| `lib/core/di/providers.dart` | Remove `themePrefsProvider` override | 2.2 |
| `lib/core/storage/local_storage.dart` | Remove `themeKey` constant | 2.3 |
| `lib/features/settings/presentation/widgets/theme_preview_card.dart` | Update import | 2.4 |
| `lib/app/app.dart` | No change needed (already watches `currentThemeDataProvider`) | -- |
| `lib/main.dart` | May remove theme prefs init if no longer needed | 2.2 |

---

## 6. Test Plan

### 23 test cases across 6 groups:

#### Group 1: Bug Reproduction (4 tests)
| ID | Test | Purpose |
|----|------|---------|
| 1.1 | `settingsProvider.updateThemeMode does not update themeProvider` | Prove disconnect (passes today, fails after fix) |
| 1.2 | `settingsProvider.updateBrightness does not update themeProvider` | Prove brightness disconnect |
| 1.3 | `AppearanceScreen tap does not change MaterialApp theme` | Full UI-level bug proof |
| 1.4 | `Default theme mismatch between systems` | Prove default inconsistency |

#### Group 2: Synchronization Verification (4 tests)
| ID | Test | Purpose |
|----|------|---------|
| 2.1 | `settingsProvider themeMode change propagates to currentThemeDataProvider` | Verify fix works |
| 2.2 | `settingsProvider brightness change propagates to currentThemeDataProvider` | Verify brightness propagation |
| 2.3 | `settingsProvider OLED mode change propagates to theme` | Verify OLED produces #000000 |
| 2.4 | `themeProvider is read-only derived from settingsProvider` | Verify no direct mutation path |

#### Group 3: Full Combination Matrix (7 tests)
| ID | Combination | Assertions |
|----|-------------|-----------|
| 3.1 | Material You + System | ThemeMode.system, MY colors |
| 3.2 | Material You + Light | ThemeMode.light |
| 3.3 | Material You + Dark | ThemeMode.dark |
| 3.4 | Cyberpunk + System | ThemeMode.system, matrixGreen |
| 3.5 | Cyberpunk + Light | ThemeMode.light, cyberpunk colors |
| 3.6 | Cyberpunk + Dark | ThemeMode.dark, cyberpunk colors |
| 3.7 | Cyberpunk + Dark + OLED | scaffoldBg == #000000 |

#### Group 4: Persistence (3 tests)
| ID | Test | Purpose |
|----|------|---------|
| 4.1 | Theme persists across provider reconstruction | Simulate app restart |
| 4.2 | OLED mode persists across provider reconstruction | Verify new persistence works |
| 4.3 | Invalid persisted values produce safe defaults | Graceful degradation |

#### Group 5: Widget Integration (6 tests)
| ID | Test | Purpose |
|----|------|---------|
| 5.1 | Cyberpunk card tap updates theme | Full tap-to-theme flow |
| 5.2 | Brightness segment button changes theme | Brightness UI flow |
| 5.3 | OLED toggle visible only when brightness != light | Conditional visibility |
| 5.4 | Scanline toggle visible only for cyberpunk | Conditional visibility |
| 5.5 | Rapid theme switching produces consistent state | Stress test |
| 5.6 | Theme switch mid-navigation preserves route | No route reset |

#### Group 6: Enum Consolidation (2 tests -- static analysis)
| ID | Test | Purpose |
|----|------|---------|
| 6.1 | Only one `AppThemeMode` enum in codebase | Prevent regression |
| 6.2 | Only one brightness enum in codebase | Prevent regression |

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Existing users lose theme preference | Phase 3 migration reads old keys, writes new keys |
| `AsyncValue` loading state shows blank screen | Default to `AppSettings()` while loading |
| Breaking `CyberColors.isCyberpunkTheme(context)` | Will work correctly once theme actually matches selection |
| Downstream providers watching `themeProvider` | Grep confirmed only `currentThemeDataProvider` watches it |
| `theme_preview_card.dart` import of `AppThemeMode` | Update import path in Phase 2.4 |

---

## 8. Success Criteria

1. User selects Cyberpunk Dark in AppearanceScreen --> app immediately renders cyberpunk dark theme
2. User selects Material You Light --> app immediately renders Material You light theme
3. All 7 theme combinations work correctly
4. Theme preference survives app restart
5. OLED mode, scanline effect, text scale survive app restart
6. Dynamic Color toggle actually enables/disables wallpaper-derived colors
7. No visual flash on first launch
8. All 23 tests pass
9. Zero duplicate enum definitions in codebase

---

## 9. Provider Dependency Graph (After Fix)

```
SharedPreferences (created in main.dart)
    |
    +--[override]--> sharedPreferencesProvider
                         |
                         v
                     settingsRepositoryProvider
                         |
                         v
                     settingsProvider (AsyncNotifier<AppSettings>)  <-- SINGLE SOURCE OF TRUTH
                         |
                         +---> currentThemeDataProvider ---> MaterialApp (theme, darkTheme, themeMode)
                         |         also watches: dynamicColorProvider
                         |
                         +---> currentLocaleProvider ---> MaterialApp (locale)
                         +---> currentTextScaleProvider ---> MaterialApp (builder)
                         +---> AppearanceScreen (UI)
                         +---> SettingsScreen (UI)
                         +---> 12 other consumers
```

No more System A. One provider graph. One set of SharedPreferences keys. One set of enums. One default.
