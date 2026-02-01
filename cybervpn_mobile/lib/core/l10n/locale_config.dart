import 'dart:ui' show Locale;

/// All 27 supported locales for the application.
///
/// Maps locale code strings (used in settings storage) to [Locale] objects.
/// The string codes follow the pattern used by the admin dashboard, mapped
/// to Flutter's [Locale] system:
///
/// - Simple language codes: `en`, `ru`, `de`, etc.
/// - Script-based codes: `zh` (Simplified), `zh_Hant` (Traditional).
///
/// RTL locales: `ar`, `he`, `fa`.
class LocaleConfig {
  LocaleConfig._();

  /// Default locale used when no preference is set or locale is unsupported.
  static const String defaultLocaleCode = 'en';

  /// RTL (right-to-left) locale codes.
  static const Set<String> rtlLocaleCodes = {'ar', 'he', 'fa'};

  /// All supported locale codes in order.
  ///
  /// These codes are used as the storage key in [AppSettings.locale].
  static const List<String> supportedLocaleCodes = [
    'en', // English (en-EN)
    'ru', // Russian (ru-RU)
    'de', // German (de-DE)
    'fr', // French (fr-FR)
    'es', // Spanish (es-ES)
    'pt', // Portuguese (pt-BR)
    'it', // Italian (it-IT)
    'nl', // Dutch (nl-NL)
    'pl', // Polish (pl-PL)
    'uk', // Ukrainian (uk-UA)
    'tr', // Turkish (tr-TR)
    'ja', // Japanese (ja-JP)
    'ko', // Korean (ko-KR)
    'zh', // Chinese Simplified (zh-CN)
    'zh_Hant', // Chinese Traditional (zh-TW)
    'ar', // Arabic (ar-SA)
    'he', // Hebrew (he-IL)
    'fa', // Farsi / Persian (fa-IR)
    'hi', // Hindi (hi-IN)
    'th', // Thai (th-TH)
    'vi', // Vietnamese (vi-VN)
    'id', // Indonesian (id-ID)
    'ms', // Malay (ms-MY)
    'ro', // Romanian (ro-RO)
    'cs', // Czech (cs-CZ)
    'sv', // Swedish (sv-SE)
    'da', // Danish (da-DK)
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
