/// Represents a selectable language in the language picker.
///
/// Each item contains the locale code, native name, English name, and
/// a flag emoji for visual identification in the UI.
class LanguageItem {
  const LanguageItem({
    required this.localeCode,
    required this.nativeName,
    required this.englishName,
    required this.flagEmoji,
  });

  /// The locale code used by the app (e.g. 'en', 'ru').
  final String localeCode;

  /// The name of the language in its own script (e.g. 'English', 'Русский').
  final String nativeName;

  /// The name of the language in English (e.g. 'English', 'Russian').
  final String englishName;

  /// A flag emoji representing the language's primary country.
  final String flagEmoji;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is LanguageItem &&
        other.localeCode == localeCode &&
        other.nativeName == nativeName &&
        other.englishName == englishName &&
        other.flagEmoji == flagEmoji;
  }

  @override
  int get hashCode => Object.hash(localeCode, nativeName, englishName, flagEmoji);

  @override
  String toString() =>
      'LanguageItem(localeCode: $localeCode, nativeName: $nativeName, '
      'englishName: $englishName, flagEmoji: $flagEmoji)';
}
