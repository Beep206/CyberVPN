import 'dart:ui' show Locale;

/// All 38 supported locales for the application.
///
/// Maps locale code strings (used in settings storage) to [Locale] objects.
/// The string codes follow the pattern used by the admin dashboard, mapped
/// to Flutter's [Locale] system:
///
/// - Simple language codes: `en`, `ru`, `de`, etc.
///
/// RTL locales: `ar`, `he`, `fa`, `ur`, `ku`.
class LocaleConfig {
  LocaleConfig._();

  /// Default locale used when no preference is set or locale is unsupported.
  static const String defaultLocaleCode = 'en';

  /// RTL (right-to-left) locale codes.
  static const Set<String> rtlLocaleCodes = {'ar', 'he', 'fa', 'ur', 'ku'};

  /// All supported locale codes in order.
  ///
  /// These codes are used as the storage key in [AppSettings.locale].
  static const List<String> supportedLocaleCodes = [
    // High priority
    'en', // English (en-EN)
    'hi', // Hindi (hi-IN)
    'id', // Indonesian (id-ID)
    'ru', // Russian (ru-RU)
    'zh', // Chinese Simplified (zh-CN)
    // Medium priority
    'ar', // Arabic (ar-SA)
    'fa', // Farsi / Persian (fa-IR)
    'tr', // Turkish (tr-TR)
    'vi', // Vietnamese (vi-VN)
    'ur', // Urdu (ur-PK)
    // Low priority
    'th', // Thai (th-TH)
    'bn', // Bengali (bn-BD)
    'ms', // Malay (ms-MY)
    'es', // Spanish (es-ES)
    'kk', // Kazakh (kk-KZ)
    'be', // Belarusian (be-BY)
    'my', // Burmese (my-MM)
    'uz', // Uzbek (uz-UZ)
    // Non-viable
    'ha', // Hausa (ha-NG)
    'yo', // Yoruba (yo-NG)
    'ku', // Kurdish Sorani (ku-IQ)
    'am', // Amharic (am-ET)
    'fr', // French (fr-FR)
    'tk', // Turkmen (tk-TM)
    // Additional
    'ja', // Japanese (ja-JP)
    'ko', // Korean (ko-KR)
    'he', // Hebrew (he-IL)
    'de', // German (de-DE)
    'pt', // Portuguese (pt-PT)
    'it', // Italian (it-IT)
    'nl', // Dutch (nl-NL)
    'pl', // Polish (pl-PL)
    'fil', // Filipino (fil-PH)
    'uk', // Ukrainian (uk-UA)
    'cs', // Czech (cs-CZ)
    'ro', // Romanian (ro-RO)
    'hu', // Hungarian (hu-HU)
    'sv', // Swedish (sv-SE)
  ];

  /// Converts a locale code string to a Flutter [Locale] object.
  ///
  /// Handles script-based locales like `zh_Hant` by splitting on `_` and
  /// using [Locale.fromSubtags].
  static Locale localeFromCode(String code) {
    if (code.contains('_')) {
      final parts = code.split('_');
      return Locale.fromSubtags(
        languageCode: parts[0],
        scriptCode: parts[1],
      );
    }
    return Locale(code);
  }

  /// Whether the given locale code represents an RTL language.
  static bool isRtl(String code) => rtlLocaleCodes.contains(code);
}
