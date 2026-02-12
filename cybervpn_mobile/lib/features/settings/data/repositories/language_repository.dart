import 'package:cybervpn_mobile/features/settings/domain/models/language_item.dart';

/// Repository providing the list of supported languages.
///
/// All 39 locales matching `AppLocalizations.supportedLocales` are listed.
/// The list is intentionally kept in a static constant so it can be extended
/// without changing the API.
class LanguageRepository {
  const LanguageRepository();

  /// All supported languages, ordered alphabetically by English name.
  static const List<LanguageItem> _supportedLanguages = [
    LanguageItem(
      localeCode: 'am',
      nativeName: '\u12A0\u121B\u122D\u129B',
      englishName: 'Amharic',
      flagEmoji: '\u{1F1EA}\u{1F1F9}', // ET flag
    ),
    LanguageItem(
      localeCode: 'ar',
      nativeName: '\u0627\u0644\u0639\u0631\u0628\u064A\u0629',
      englishName: 'Arabic',
      flagEmoji: '\u{1F1F8}\u{1F1E6}', // SA flag
    ),
    LanguageItem(
      localeCode: 'be',
      nativeName: '\u0411\u0435\u043B\u0430\u0440\u0443\u0441\u043A\u0430\u044F',
      englishName: 'Belarusian',
      flagEmoji: '\u{1F1E7}\u{1F1FE}', // BY flag
    ),
    LanguageItem(
      localeCode: 'bn',
      nativeName: '\u09AC\u09BE\u0982\u09B2\u09BE',
      englishName: 'Bengali',
      flagEmoji: '\u{1F1E7}\u{1F1E9}', // BD flag
    ),
    LanguageItem(
      localeCode: 'my',
      nativeName: '\u1019\u103C\u1014\u103A\u1019\u102C',
      englishName: 'Burmese',
      flagEmoji: '\u{1F1F2}\u{1F1F2}', // MM flag
    ),
    LanguageItem(
      localeCode: 'zh',
      nativeName: '\u4E2D\u6587\u7B80\u4F53',
      englishName: 'Chinese (Simplified)',
      flagEmoji: '\u{1F1E8}\u{1F1F3}', // CN flag
    ),
    LanguageItem(
      localeCode: 'zh_Hant',
      nativeName: '\u4E2D\u6587\u7E41\u9AD4',
      englishName: 'Chinese (Traditional)',
      flagEmoji: '\u{1F1F9}\u{1F1FC}', // TW flag
    ),
    LanguageItem(
      localeCode: 'cs',
      nativeName: '\u010Ce\u0161tina',
      englishName: 'Czech',
      flagEmoji: '\u{1F1E8}\u{1F1FF}', // CZ flag
    ),
    LanguageItem(
      localeCode: 'nl',
      nativeName: 'Nederlands',
      englishName: 'Dutch',
      flagEmoji: '\u{1F1F3}\u{1F1F1}', // NL flag
    ),
    LanguageItem(
      localeCode: 'en',
      nativeName: 'English',
      englishName: 'English',
      flagEmoji: '\u{1F1EC}\u{1F1E7}', // GB flag
    ),
    LanguageItem(
      localeCode: 'fa',
      nativeName: '\u0641\u0627\u0631\u0633\u06CC',
      englishName: 'Farsi',
      flagEmoji: '\u{1F1EE}\u{1F1F7}', // IR flag
    ),
    LanguageItem(
      localeCode: 'fil',
      nativeName: 'Filipino',
      englishName: 'Filipino',
      flagEmoji: '\u{1F1F5}\u{1F1ED}', // PH flag
    ),
    LanguageItem(
      localeCode: 'fr',
      nativeName: 'Fran\u00E7ais',
      englishName: 'French',
      flagEmoji: '\u{1F1EB}\u{1F1F7}', // FR flag
    ),
    LanguageItem(
      localeCode: 'de',
      nativeName: 'Deutsch',
      englishName: 'German',
      flagEmoji: '\u{1F1E9}\u{1F1EA}', // DE flag
    ),
    LanguageItem(
      localeCode: 'ha',
      nativeName: 'Hausa',
      englishName: 'Hausa',
      flagEmoji: '\u{1F1F3}\u{1F1EC}', // NG flag
    ),
    LanguageItem(
      localeCode: 'he',
      nativeName: '\u05E2\u05D1\u05E8\u05D9\u05EA',
      englishName: 'Hebrew',
      flagEmoji: '\u{1F1EE}\u{1F1F1}', // IL flag
    ),
    LanguageItem(
      localeCode: 'hi',
      nativeName: '\u0939\u093F\u0928\u094D\u0926\u0940',
      englishName: 'Hindi',
      flagEmoji: '\u{1F1EE}\u{1F1F3}', // IN flag
    ),
    LanguageItem(
      localeCode: 'hu',
      nativeName: 'Magyar',
      englishName: 'Hungarian',
      flagEmoji: '\u{1F1ED}\u{1F1FA}', // HU flag
    ),
    LanguageItem(
      localeCode: 'id',
      nativeName: 'Bahasa Indonesia',
      englishName: 'Indonesian',
      flagEmoji: '\u{1F1EE}\u{1F1E9}', // ID flag
    ),
    LanguageItem(
      localeCode: 'it',
      nativeName: 'Italiano',
      englishName: 'Italian',
      flagEmoji: '\u{1F1EE}\u{1F1F9}', // IT flag
    ),
    LanguageItem(
      localeCode: 'ja',
      nativeName: '\u65E5\u672C\u8A9E',
      englishName: 'Japanese',
      flagEmoji: '\u{1F1EF}\u{1F1F5}', // JP flag
    ),
    LanguageItem(
      localeCode: 'kk',
      nativeName: '\u049A\u0430\u0437\u0430\u049B\u0448\u0430',
      englishName: 'Kazakh',
      flagEmoji: '\u{1F1F0}\u{1F1FF}', // KZ flag
    ),
    LanguageItem(
      localeCode: 'ko',
      nativeName: '\uD55C\uAD6D\uC5B4',
      englishName: 'Korean',
      flagEmoji: '\u{1F1F0}\u{1F1F7}', // KR flag
    ),
    LanguageItem(
      localeCode: 'ku',
      nativeName: '\u06A9\u0648\u0631\u062F\u06CC',
      englishName: 'Kurdish',
      flagEmoji: '\u{1F1EE}\u{1F1F6}', // IQ flag
    ),
    LanguageItem(
      localeCode: 'ms',
      nativeName: 'Bahasa Melayu',
      englishName: 'Malay',
      flagEmoji: '\u{1F1F2}\u{1F1FE}', // MY flag
    ),
    LanguageItem(
      localeCode: 'pl',
      nativeName: 'Polski',
      englishName: 'Polish',
      flagEmoji: '\u{1F1F5}\u{1F1F1}', // PL flag
    ),
    LanguageItem(
      localeCode: 'pt',
      nativeName: 'Portugu\u00EAs',
      englishName: 'Portuguese',
      flagEmoji: '\u{1F1F5}\u{1F1F9}', // PT flag
    ),
    LanguageItem(
      localeCode: 'ro',
      nativeName: 'Rom\u00E2n\u0103',
      englishName: 'Romanian',
      flagEmoji: '\u{1F1F7}\u{1F1F4}', // RO flag
    ),
    LanguageItem(
      localeCode: 'ru',
      nativeName: '\u0420\u0443\u0441\u0441\u043A\u0438\u0439',
      englishName: 'Russian',
      flagEmoji: '\u{1F1F7}\u{1F1FA}', // RU flag
    ),
    LanguageItem(
      localeCode: 'es',
      nativeName: 'Espa\u00F1ol',
      englishName: 'Spanish',
      flagEmoji: '\u{1F1EA}\u{1F1F8}', // ES flag
    ),
    LanguageItem(
      localeCode: 'sv',
      nativeName: 'Svenska',
      englishName: 'Swedish',
      flagEmoji: '\u{1F1F8}\u{1F1EA}', // SE flag
    ),
    LanguageItem(
      localeCode: 'th',
      nativeName: '\u0E44\u0E17\u0E22',
      englishName: 'Thai',
      flagEmoji: '\u{1F1F9}\u{1F1ED}', // TH flag
    ),
    LanguageItem(
      localeCode: 'tr',
      nativeName: 'T\u00FCrk\u00E7e',
      englishName: 'Turkish',
      flagEmoji: '\u{1F1F9}\u{1F1F7}', // TR flag
    ),
    LanguageItem(
      localeCode: 'tk',
      nativeName: 'T\u00FCrkmen',
      englishName: 'Turkmen',
      flagEmoji: '\u{1F1F9}\u{1F1F2}', // TM flag
    ),
    LanguageItem(
      localeCode: 'uk',
      nativeName: '\u0423\u043A\u0440\u0430\u0457\u043D\u0441\u044C\u043A\u0430',
      englishName: 'Ukrainian',
      flagEmoji: '\u{1F1FA}\u{1F1E6}', // UA flag
    ),
    LanguageItem(
      localeCode: 'ur',
      nativeName: '\u0627\u0631\u062F\u0648',
      englishName: 'Urdu',
      flagEmoji: '\u{1F1F5}\u{1F1F0}', // PK flag
    ),
    LanguageItem(
      localeCode: 'uz',
      nativeName: 'O\u02BBzbekcha',
      englishName: 'Uzbek',
      flagEmoji: '\u{1F1FA}\u{1F1FF}', // UZ flag
    ),
    LanguageItem(
      localeCode: 'vi',
      nativeName: 'Ti\u1EBFng Vi\u1EC7t',
      englishName: 'Vietnamese',
      flagEmoji: '\u{1F1FB}\u{1F1F3}', // VN flag
    ),
    LanguageItem(
      localeCode: 'yo',
      nativeName: 'Yor\u00F9b\u00E1',
      englishName: 'Yoruba',
      flagEmoji: '\u{1F1F3}\u{1F1EC}', // NG flag
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
