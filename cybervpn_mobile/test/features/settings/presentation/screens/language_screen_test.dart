import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/settings/data/repositories/language_repository.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/models/language_item.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/screens/language_screen.dart';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Builds a [LanguageScreen] inside a [ProviderScope] with the given
/// [settingsOverride] providing the initial [AppSettings].
Widget _buildTestWidget({
  AppSettings settings = const AppSettings(),
  _FakeSettingsNotifier? notifier,
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(
        () => notifier ?? _FakeSettingsNotifier(settings),
      ),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: Locale('en'),
      home: LanguageScreen(),
    ),
  );
}

/// A fake [SettingsNotifier] that returns the provided settings synchronously.
class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier(this._initial);

  final AppSettings _initial;
  String? updatedLocale;

  @override
  Future<AppSettings> build() async => _initial;

  @override
  Future<void> updateLocale(String locale) async {
    updatedLocale = locale;
    state = AsyncData(_initial.copyWith(locale: locale));
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('LanguageScreen', () {
    testWidgets('renders all available languages', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      const repo = LanguageRepository();
      final languages = repo.getAvailableLanguages();

      for (final lang in languages) {
        final expectedCount = lang.nativeName == lang.englishName ? 2 : 1;
        expect(find.text(lang.nativeName), findsNWidgets(expectedCount));
        if (lang.nativeName != lang.englishName) {
          expect(find.text(lang.englishName), findsOneWidget);
        }
      }
    });

    testWidgets('shows checkmark for current locale', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(settings: const AppSettings(locale: 'en')),
      );
      await tester.pumpAndSettle();

      // The English tile should have a check icon.
      final englishTile = find.ancestor(
        of: find.text('English').first,
        matching: find.byType(ListTile),
      );
      expect(englishTile, findsOneWidget);

      // There should be exactly one check icon (for the selected language).
      expect(find.byIcon(Icons.check), findsOneWidget);
    });

    testWidgets('search filters by English name', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Type 'Eng' in the search field.
      await tester.enterText(
        find.byKey(const Key('language_search_field')),
        'Eng',
      );
      await tester.pumpAndSettle();

      // English should still be visible.
      expect(find.text('English'), findsWidgets);

      // Russian native name should not appear.
      expect(
        find.text('\u0420\u0443\u0441\u0441\u043A\u0438\u0439'),
        findsNothing,
      );
    });

    testWidgets('search hides fallback-only languages', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Russian exists as a fallback-only ARB resource, but is not selectable.
      await tester.enterText(
        find.byKey(const Key('language_search_field')),
        '\u0420\u0443\u0441',
      );
      await tester.pumpAndSettle();

      expect(find.text('No languages found'), findsOneWidget);
      expect(find.text('Russian'), findsNothing);
      expect(find.text('English'), findsNothing);
    });

    testWidgets('clear button clears search', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Enter search text.
      await tester.enterText(
        find.byKey(const Key('language_search_field')),
        'Eng',
      );
      await tester.pumpAndSettle();

      // Clear button should appear.
      expect(find.byKey(const Key('language_search_clear')), findsOneWidget);

      // Tap clear.
      await tester.tap(find.byKey(const Key('language_search_clear')));
      await tester.pumpAndSettle();

      // All languages should be visible again.
      const repo = LanguageRepository();
      final languages = repo.getAvailableLanguages();
      for (final lang in languages) {
        final expectedCount = lang.nativeName == lang.englishName ? 2 : 1;
        expect(find.text(lang.nativeName), findsNWidgets(expectedCount));
      }
    });

    testWidgets('empty state shown when no languages match', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('language_search_field')),
        'zzzzzzz',
      );
      await tester.pumpAndSettle();

      expect(find.text('No languages found'), findsOneWidget);
    });

    testWidgets('selecting a language updates the provider', (tester) async {
      final notifier = _FakeSettingsNotifier(const AppSettings(locale: 'en'));
      await tester.pumpWidget(_buildTestWidget(notifier: notifier));
      await tester.pumpAndSettle();

      // Tap on the reviewed English language tile.
      await tester.tap(find.text('English').first);
      await tester.pumpAndSettle();

      expect(notifier.updatedLocale, 'en');
    });
  });

  group('LanguageRepository', () {
    test('getAvailableLanguages returns non-empty list', () {
      const repo = LanguageRepository();
      final languages = repo.getAvailableLanguages();

      expect(languages, isNotEmpty);
      expect(languages, hasLength(1));
    });

    test('getAvailableLanguages exposes reviewed locales only', () {
      const repo = LanguageRepository();
      final languages = repo.getAvailableLanguages();
      final codes = languages.map((l) => l.localeCode).toSet();

      expect(codes, equals({'en'}));
      expect(codes.contains('ru'), isFalse);
      expect(codes.contains('zh_Hant'), isFalse);
    });

    test('getByLocaleCode returns correct item', () {
      const repo = LanguageRepository();

      final en = repo.getByLocaleCode('en');
      expect(en, isNotNull);
      expect(en!.englishName, 'English');
      expect(en.nativeName, 'English');

      final ru = repo.getByLocaleCode('ru');
      expect(ru, isNull);
    });

    test('getByLocaleCode returns null for unknown code', () {
      const repo = LanguageRepository();
      expect(repo.getByLocaleCode('xx'), isNull);
    });

    test('supportedLocaleCodes returns correct set', () {
      const repo = LanguageRepository();
      final codes = repo.supportedLocaleCodes;

      expect(codes, contains('en'));
      expect(codes, isNot(contains('ru')));
      expect(codes, isNot(contains('zh_Hant')));
      expect(codes, isNot(contains('xx')));
    });
  });

  group('LanguageItem', () {
    test('equality and hashCode', () {
      const a = LanguageItem(
        localeCode: 'en',
        nativeName: 'English',
        englishName: 'English',
        flagEmoji: '\u{1F1EC}\u{1F1E7}',
      );
      const b = LanguageItem(
        localeCode: 'en',
        nativeName: 'English',
        englishName: 'English',
        flagEmoji: '\u{1F1EC}\u{1F1E7}',
      );

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('toString contains all fields', () {
      const item = LanguageItem(
        localeCode: 'en',
        nativeName: 'English',
        englishName: 'English',
        flagEmoji: '\u{1F1EC}\u{1F1E7}',
      );

      expect(item.toString(), contains('en'));
      expect(item.toString(), contains('English'));
    });
  });
}
