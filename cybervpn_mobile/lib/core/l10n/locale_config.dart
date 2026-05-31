import 'dart:ui' show Locale;

/// Locale policy for the application.
///
/// [supportedLocaleCodes] is the active ARB resource inventory. Locale codes
/// not listed here are outside the mobile inventory even if stale generated
/// files or old settings still reference them.
///
/// [selectableLocaleCodes] is the reviewed language-picker inventory. Non-
/// selectable resources are fallback-only until translation and RTL QA are
/// approved.
///
/// RTL locales: `ar`, `he`, `fa`, `ur`, `ku`.
class LocaleConfig {
  LocaleConfig._();

  /// Default locale used when no preference is set or locale is unsupported.
  static const String defaultLocaleCode = 'en';

  /// RTL (right-to-left) locale codes.
  static const Set<String> rtlLocaleCodes = {'ar', 'he', 'fa', 'ur', 'ku'};

  /// Reviewed locales that can be selected by users.
  static const Set<String> selectableLocaleCodes = {'en'};

  /// Active ARB resource locale codes in order.
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
  /// Handles future script-based locales by splitting on `_` and using
  /// [Locale.fromSubtags].
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

  /// Whether the given locale code is reviewed and user-selectable.
  static bool isSelectable(String code) => selectableLocaleCodes.contains(code);

  /// Falls back to the default locale when a stored locale is not selectable.
  static String normalizeSelectableLocaleCode(String code) {
    return isSelectable(code) ? code : defaultLocaleCode;
  }
}
