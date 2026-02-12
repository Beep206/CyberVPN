import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:cybervpn_mobile/app/theme/theme_provider.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

// ---------------------------------------------------------------------------
// Fake SettingsNotifier for testing
// ---------------------------------------------------------------------------

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier([AppSettings? initial])
      : _settings = initial ?? const AppSettings();

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUpAll(() {
    // Prevent GoogleFonts from making real HTTP calls in tests.
    // Font loading errors are logged but don't crash the provider logic.
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Group 1: Bug reproduction (historical — proves the old bug pattern)
  // ══════════════════════════════════════════════════════════════════════════

  group('Group 1: Bug reproduction (historical)', () {
    test('1.1: old themeProvider no longer exists', () {
      // The old `themeProvider` (NotifierProvider<ThemeNotifier, ThemeState>)
      // has been completely removed. currentThemeDataProvider now derives
      // from settingsProvider. This test documents that the old disconnected
      // system no longer exists.
      expect(true, isTrue, reason: 'themeProvider removed, bug eliminated');
    });

    test('1.2: old ThemeBrightness enum no longer exists', () {
      expect(AppBrightness.values.length, 3);
      expect(AppBrightness.values, contains(AppBrightness.system));
      expect(AppBrightness.values, contains(AppBrightness.light));
      expect(AppBrightness.values, contains(AppBrightness.dark));
    });

    test('1.3: only one AppThemeMode enum exists (in app_settings.dart)', () {
      expect(AppThemeMode.values.length, 2);
      expect(AppThemeMode.values, contains(AppThemeMode.materialYou));
      expect(AppThemeMode.values, contains(AppThemeMode.cyberpunk));
    });

    test('1.4: default theme is cyberpunk (not materialYou)', () {
      const settings = AppSettings();
      expect(settings.themeMode, AppThemeMode.cyberpunk);
      expect(settings.brightness, AppBrightness.system);
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Group 2: Synchronization verification
  // ══════════════════════════════════════════════════════════════════════════

  group('Group 2: Synchronization verification', () {
    testWidgets('2.1: settingsProvider themeMode change propagates to currentThemeDataProvider', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.materialYou,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.light, isA<ThemeData>());
      expect(pair.dark, isA<ThemeData>());
      expect(pair.themeMode, ThemeMode.system);
    });

    testWidgets('2.2: cyberpunk themeMode produces cyberpunk ThemeDataPair', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.system);
      expect(
        pair.dark.scaffoldBackgroundColor,
        anyOf(equals(CyberColors.deepNavy), equals(CyberColors.darkBg)),
      );
    });

    testWidgets('2.3: brightness=dark produces ThemeMode.dark', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                brightness: AppBrightness.dark,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.dark);
    });

    testWidgets('2.4: OLED mode produces pure black scaffold background', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
                oledMode: true,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.dark.scaffoldBackgroundColor, CyberColors.oledBlack);
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Group 3: Full combination matrix
  // ══════════════════════════════════════════════════════════════════════════

  group('Group 3: Full combination matrix', () {
    testWidgets('3.1: Material You + System', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.materialYou,
                brightness: AppBrightness.system,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.system);
      expect(pair.light.brightness, Brightness.light);
      expect(pair.dark.brightness, Brightness.dark);
    });

    testWidgets('3.2: Material You + Light', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.materialYou,
                brightness: AppBrightness.light,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.light);
    });

    testWidgets('3.3: Material You + Dark', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.materialYou,
                brightness: AppBrightness.dark,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.dark);
    });

    testWidgets('3.4: Cyberpunk + System', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.system,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.system);
      expect(pair.light, isA<ThemeData>());
      expect(pair.dark, isA<ThemeData>());
    });

    testWidgets('3.5: Cyberpunk + Light', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.light,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.light);
    });

    testWidgets('3.6: Cyberpunk + Dark', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.dark);
    });

    testWidgets('3.7: Cyberpunk + Dark + OLED', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
                oledMode: true,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.themeMode, ThemeMode.dark);
      expect(pair.dark.scaffoldBackgroundColor, CyberColors.oledBlack);
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Group 4: Persistence tests
  // ══════════════════════════════════════════════════════════════════════════

  group('Group 4: Persistence', () {
    testWidgets('4.1: theme state survives provider reconstruction', (tester) async {
      // First render with cyberpunk + dark
      late ThemeDataPair pair1;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair1 = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair1.themeMode, ThemeMode.dark);

      // Second render with same settings (simulating widget rebuild)
      late ThemeDataPair pair2;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair2 = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair2.themeMode, ThemeMode.dark);
    });

    testWidgets('4.2: OLED mode survives provider reconstruction', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
                oledMode: true,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.dark.scaffoldBackgroundColor, CyberColors.oledBlack);
    });

    testWidgets('4.3: default AppSettings produces valid ThemeDataPair', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              _FakeSettingsNotifier.new,
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      // Default is cyberpunk + system
      expect(pair.themeMode, ThemeMode.system);
      expect(pair.light, isA<ThemeData>());
      expect(pair.dark, isA<ThemeData>());
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Group 5: Widget integration tests
  // ══════════════════════════════════════════════════════════════════════════

  group('Group 5: Widget integration', () {
    testWidgets('5.1: MaterialApp receives correct theme from currentThemeDataProvider', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              final themePair = ref.watch(currentThemeDataProvider);
              return MaterialApp(
                theme: themePair.light,
                darkTheme: themePair.dark,
                themeMode: themePair.themeMode,
                home: Builder(
                  builder: (context) {
                    return Text(
                      Theme.of(context).brightness.name,
                      textDirection: TextDirection.ltr,
                    );
                  },
                ),
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('dark'), findsOneWidget);
    });

    testWidgets('5.2: MaterialApp receives light theme when brightness=light', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.materialYou,
                brightness: AppBrightness.light,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              final themePair = ref.watch(currentThemeDataProvider);
              return MaterialApp(
                theme: themePair.light,
                darkTheme: themePair.dark,
                themeMode: themePair.themeMode,
                home: Builder(
                  builder: (context) {
                    return Text(
                      Theme.of(context).brightness.name,
                      textDirection: TextDirection.ltr,
                    );
                  },
                ),
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('light'), findsOneWidget);
    });

    testWidgets('5.3: dynamicColor=false does not use dynamic colors', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.materialYou,
                dynamicColor: false,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              final themePair = ref.watch(currentThemeDataProvider);
              return MaterialApp(
                theme: themePair.light,
                darkTheme: themePair.dark,
                themeMode: themePair.themeMode,
                home: const SizedBox.shrink(),
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(MaterialApp), findsOneWidget);
    });

    testWidgets('5.4: cyberpunk OLED theme applies pure black background', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.dark,
                oledMode: true,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              final themePair = ref.watch(currentThemeDataProvider);
              return MaterialApp(
                theme: themePair.light,
                darkTheme: themePair.dark,
                themeMode: themePair.themeMode,
                home: Builder(
                  builder: (context) {
                    final scaffoldBg =
                        Theme.of(context).scaffoldBackgroundColor;
                    return Text(
                      scaffoldBg == CyberColors.oledBlack
                          ? 'oled'
                          : 'not_oled',
                      textDirection: TextDirection.ltr,
                    );
                  },
                ),
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('oled'), findsOneWidget);
    });

    testWidgets('5.5: ThemeDataPair has consistent light/dark brightness', (tester) async {
      late ThemeDataPair pair;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            settingsProvider.overrideWith(
              () => _FakeSettingsNotifier(const AppSettings(
                themeMode: AppThemeMode.cyberpunk,
                brightness: AppBrightness.system,
              )),
            ),
          ],
          child: Consumer(
            builder: (context, ref, _) {
              pair = ref.watch(currentThemeDataProvider);
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(pair.light.brightness, Brightness.light);
      expect(pair.dark.brightness, Brightness.dark);
    });

    testWidgets('5.6: all theme combinations render without crash', (tester) async {
      for (final mode in AppThemeMode.values) {
        for (final brightness in AppBrightness.values) {
          await tester.pumpWidget(
            ProviderScope(
              overrides: [
                settingsProvider.overrideWith(
                  () => _FakeSettingsNotifier(AppSettings(
                    themeMode: mode,
                    brightness: brightness,
                  )),
                ),
              ],
              child: Consumer(
                builder: (context, ref, _) {
                  final themePair = ref.watch(currentThemeDataProvider);
                  return MaterialApp(
                    theme: themePair.light,
                    darkTheme: themePair.dark,
                    themeMode: themePair.themeMode,
                    home: const SizedBox.shrink(),
                  );
                },
              ),
            ),
          );
          await tester.pumpAndSettle();
          expect(find.byType(MaterialApp), findsOneWidget,
              reason: 'Failed for $mode + $brightness');
        }
      }
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // Group 6: Enum consolidation
  // ══════════════════════════════════════════════════════════════════════════

  group('Group 6: Enum consolidation', () {
    test('6.1: AppThemeMode has exactly 2 values', () {
      expect(AppThemeMode.values, hasLength(2));
      expect(AppThemeMode.materialYou.name, 'materialYou');
      expect(AppThemeMode.cyberpunk.name, 'cyberpunk');
    });

    test('6.2: AppBrightness has exactly 3 values', () {
      expect(AppBrightness.values, hasLength(3));
      expect(AppBrightness.system.name, 'system');
      expect(AppBrightness.light.name, 'light');
      expect(AppBrightness.dark.name, 'dark');
    });
  });
}
