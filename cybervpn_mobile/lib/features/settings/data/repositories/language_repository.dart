import 'package:cybervpn_mobile/features/settings/domain/models/language_item.dart';

/// Repository providing the list of supported languages.
///
/// Currently supports English and Russian. Additional locales will be
/// added in Wave 3. The list is intentionally kept in a static constant
/// so it can be extended without changing the API.
class LanguageRepository {
  const LanguageRepository();

  /// All supported languages, ordered for display in the picker.
  ///
  /// Add new [LanguageItem] entries here to support additional locales.
  static const List<LanguageItem> _supportedLanguages = [
    LanguageItem(
      localeCode: 'en',
      nativeName: 'English',
      englishName: 'English',
      flagEmoji: '\u{1F1EC}\u{1F1E7}', // GB flag
    ),
    LanguageItem(
      localeCode: 'ru',
      nativeName: '\u0420\u0443\u0441\u0441\u043A\u0438\u0439',
      englishName: 'Russian',
      flagEmoji: '\u{1F1F7}\u{1F1FA}', // RU flag
    ),
    LanguageItem(
      localeCode: 'uk',
      nativeName: '\u0423\u043A\u0440\u0430\u0457\u043D\u0441\u044C\u043A\u0430',
      englishName: 'Ukrainian',
      flagEmoji: '\u{1F1FA}\u{1F1E6}', // UA flag
    ),
    LanguageItem(
      localeCode: 'de',
      nativeName: 'Deutsch',
      englishName: 'German',
      flagEmoji: '\u{1F1E9}\u{1F1EA}', // DE flag
    ),
    LanguageItem(
      localeCode: 'fr',
      nativeName: 'Fran\u00E7ais',
      englishName: 'French',
      flagEmoji: '\u{1F1EB}\u{1F1F7}', // FR flag
    ),
    LanguageItem(
      localeCode: 'es',
      nativeName: 'Espa\u00F1ol',
      englishName: 'Spanish',
      flagEmoji: '\u{1F1EA}\u{1F1F8}', // ES flag
    ),
    LanguageItem(
      localeCode: 'pt',
      nativeName: 'Portugu\u00EAs',
      englishName: 'Portuguese',
      flagEmoji: '\u{1F1F5}\u{1F1F9}', // PT flag
    ),
    LanguageItem(
      localeCode: 'it',
      nativeName: 'Italiano',
      englishName: 'Italian',
      flagEmoji: '\u{1F1EE}\u{1F1F9}', // IT flag
    ),
    LanguageItem(
      localeCode: 'tr',
      nativeName: 'T\u00FCrk\u00E7e',
      englishName: 'Turkish',
      flagEmoji: '\u{1F1F9}\u{1F1F7}', // TR flag
    ),
    LanguageItem(
      localeCode: 'ar',
      nativeName: '\u0627\u0644\u0639\u0631\u0628\u064A\u0629',
      englishName: 'Arabic',
      flagEmoji: '\u{1F1F8}\u{1F1E6}', // SA flag
    ),
    LanguageItem(
      localeCode: 'fa',
      nativeName: '\u0641\u0627\u0631\u0633\u06CC',
      englishName: 'Farsi',
      flagEmoji: '\u{1F1EE}\u{1F1F7}', // IR flag
    ),
    LanguageItem(
      localeCode: 'zh',
      nativeName: '\u4E2D\u6587',
      englishName: 'Chinese',
      flagEmoji: '\u{1F1E8}\u{1F1F3}', // CN flag
    ),
    LanguageItem(
      localeCode: 'ja',
      nativeName: '\u65E5\u672C\u8A9E',
      englishName: 'Japanese',
      flagEmoji: '\u{1F1EF}\u{1F1F5}', // JP flag
    ),
    LanguageItem(
      localeCode: 'ko',
      nativeName: '\uD55C\uAD6D\uC5B4',
      englishName: 'Korean',
      flagEmoji: '\u{1F1F0}\u{1F1F7}', // KR flag
    ),
  ];

  /// Returns the list of all available languages.
  List<LanguageItem> getAvailableLanguages() {
    return _supportedLanguages;
  }

  /// Returns the [LanguageItem] matching the given [localeCode], or `null`
  /// if no match is found.
  LanguageItem? getByLocaleCode(String localeCode) {
    for (final lang in _supportedLanguages) {
      if (lang.localeCode == localeCode) return lang;
    }
    return null;
  }

  /// Returns the set of supported locale codes for quick membership checks.
  Set<String> get supportedLocaleCodes =>
      _supportedLanguages.map((l) => l.localeCode).toSet();
}
