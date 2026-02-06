import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

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
}) {
  return ProviderScope(
    overrides: [
      settingsProvider.overrideWith(() => _FakeSettingsNotifier(settings)),
    ],
    child: const MaterialApp(
      home: LanguageScreen(),
    ),
  );
}

/// A fake [SettingsNotifier] that returns the provided settings synchronously.
class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier(this._initial);

  final AppSettings _initial;

  @override
  Future<AppSettings> build() async => _initial;
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
        expect(find.text(lang.nativeName), findsOneWidget);
        expect(find.text(lang.englishName), findsOneWidget);
      }
    });

    testWidgets('shows checkmark for current locale', (tester) async {
      await tester.pumpWidget(
        _buildTestWidget(settings: const AppSettings(locale: 'en')),
      );
      await tester.pumpAndSettle();

      // The English tile should have a check icon.
      final englishTile = find.ancestor(
        of: find.text('English'),
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
      await tester.enterText(find.byKey(const Key('language_search_field')), 'Eng');
      await tester.pumpAndSettle();

      // English should still be visible.
      expect(find.text('English'), findsWidgets);

      // Russian native name should not appear.
      expect(
        find.text('\u0420\u0443\u0441\u0441\u043A\u0438\u0439'),
        findsNothing,
      );
    });

    testWidgets('search filters by native name', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Search by Russian native name.
      await tester.enterText(
        find.byKey(const Key('language_search_field')),
        '\u0420\u0443\u0441',
      );
      await tester.pumpAndSettle();

      // Russian should be visible.
      expect(find.text('Russian'), findsOneWidget);

      // English should not appear (English native name does not contain the query).
      expect(find.text('English'), findsNothing);
    });

    testWidgets('clear button clears search', (tester) async {
      await tester.pumpWidget(_buildTestWidget());
      await tester.pumpAndSettle();

      // Enter search text.
      await tester.enterText(find.byKey(const Key('language_search_field')), 'Eng');
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
        expect(find.text(lang.nativeName), findsOneWidget);
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
      await tester.pumpWidget(
        _buildTestWidget(settings: const AppSettings(locale: 'en')),
      );
      await tester.pumpAndSettle();

      // Tap on the Russian language tile.
      await tester.tap(find.text('Russian'));
      await tester.pumpAndSettle();

      // The screen should pop (Navigator.pop). We verify by checking
      // the LanguageScreen is no longer in the tree.
      expect(find.byType(LanguageScreen), findsNothing);
    });
  });

  group('LanguageRepository', () {
    test('getAvailableLanguages returns non-empty list', () {
      const repo = LanguageRepository();
      final languages = repo.getAvailableLanguages();

      expect(languages, isNotEmpty);
      expect(languages.length, greaterThanOrEqualTo(2));
    });

    test('getAvailableLanguages includes en and ru', () {
      const repo = LanguageRepository();
      final languages = repo.getAvailableLanguages();
      final codes = languages.map((l) => l.localeCode).toSet();

      expect(codes.contains('en'), isTrue);
      expect(codes.contains('ru'), isTrue);
    });

    test('getByLocaleCode returns correct item', () {
      const repo = LanguageRepository();

      final en = repo.getByLocaleCode('en');
      expect(en, isNotNull);
      expect(en!.englishName, 'English');
      expect(en.nativeName, 'English');

      final ru = repo.getByLocaleCode('ru');
      expect(ru, isNotNull);
      expect(ru!.englishName, 'Russian');
    });

    test('getByLocaleCode returns null for unknown code', () {
      const repo = LanguageRepository();
      expect(repo.getByLocaleCode('xx'), isNull);
    });

    test('supportedLocaleCodes returns correct set', () {
      const repo = LanguageRepository();
      final codes = repo.supportedLocaleCodes;

      expect(codes, contains('en'));
      expect(codes, contains('ru'));
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
