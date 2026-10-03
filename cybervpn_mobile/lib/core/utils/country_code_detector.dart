/// Utility to detect country code and country name from server remarks,
/// emojis, or node names.
class DetectedCountry {
  const DetectedCountry({required this.code, required this.name});

  /// Two-letter uppercase ISO 3166-1 alpha-2 code, or 'XX' if unidentified.
  final String code;

  /// Human-readable country name.
  final String name;

  bool get isIdentified => code != 'XX' && code.isNotEmpty;
}

/// Detects country codes and display names from node names, remarks, or emoji flags.
class CountryCodeDetector {
  const CountryCodeDetector._();

  static const _countryNames = <String, String>{
    'DE': 'Germany',
    'NL': 'Netherlands',
    'RU': 'Russia',
    'US': 'United States',
    'FI': 'Finland',
    'FR': 'France',
    'GB': 'United Kingdom',
    'SE': 'Sweden',
    'PL': 'Poland',
    'TR': 'Turkey',
    'SG': 'Singapore',
    'JP': 'Japan',
    'KZ': 'Kazakhstan',
    'CA': 'Canada',
    'CH': 'Switzerland',
    'AT': 'Austria',
    'ES': 'Spain',
    'IT': 'Italy',
    'NO': 'Norway',
    'CZ': 'Czech Republic',
    'AE': 'United Arab Emirates',
    'HK': 'Hong Kong',
    'EE': 'Estonia',
    'LV': 'Latvia',
    'LT': 'Lithuania',
    'GE': 'Georgia',
    'AM': 'Armenia',
    'MD': 'Moldova',
    'UA': 'Ukraine',
    'BY': 'Belarus',
    'IL': 'Israel',
    'IN': 'India',
    'BR': 'Brazil',
    'AU': 'Australia',
    'KR': 'South Korea',
  };

  static final List<(List<String> keywords, String code)> _keywords = [
    (
      [
        'germany',
        'германия',
        'deutschland',
        'frankfurt',
        'франкфурт',
        'berlin',
        'берлин',
      ],
      'DE',
    ),
    (
      [
        'netherlands',
        'нидерланды',
        'holland',
        'голландия',
        'amsterdam',
        'амстердам',
      ],
      'NL',
    ),
    (
      [
        'russia',
        'россия',
        'рф',
        'moscow',
        'москва',
        'spb',
        'питер',
        'санкт-петербург',
        'sankt-peterburg',
      ],
      'RU',
    ),
    (
      [
        'united states',
        'usa',
        'сша',
        'america',
        'америка',
        'new york',
        'los angeles',
        'miami',
      ],
      'US',
    ),
    (['finland', 'финляндия', 'helsinki', 'хельсинки'], 'FI'),
    (['france', 'франция', 'paris', 'париж'], 'FR'),
    (
      [
        'united kingdom',
        'great britain',
        'uk',
        'великобритания',
        'англия',
        'london',
        'лондон',
      ],
      'GB',
    ),
    (['sweden', 'швеция', 'stockholm', 'стокгольм'], 'SE'),
    (['poland', 'польша', 'warsaw', 'варшава'], 'PL'),
    (['turkey', 'турция', 'türkiye', 'istanbul', 'стамбул'], 'TR'),
    (['singapore', 'сингапур'], 'SG'),
    (['japan', 'япония', 'tokyo', 'токио'], 'JP'),
    (['kazakhstan', 'казахстан', 'almaty', 'алматы', 'astana', 'астана'], 'KZ'),
    (['canada', 'канада', 'toronto', 'montreal'], 'CA'),
    (['switzerland', 'швейцария', 'zurich', 'цюрих'], 'CH'),
    (['austria', 'австрия', 'vienna', 'вена'], 'AT'),
    (['spain', 'испания', 'madrid', 'barcelona'], 'ES'),
    (['italy', 'италия', 'rome', 'milan', 'милан'], 'IT'),
    (['norway', 'норвегия', 'oslo', 'осло'], 'NO'),
    (['czech', 'чехия', 'prague', 'прага'], 'CZ'),
    (['uae', 'оаэ', 'dubai', 'дубай'], 'AE'),
    (['hong kong', 'гонконг', 'hongkong'], 'HK'),
    (['estonia', 'эстония', 'tallinn', 'таллин'], 'EE'),
    (['latvia', 'латвия', 'riga', 'рига'], 'LV'),
    (['lithuania', 'литва', 'vilnius', 'вильнюс'], 'LT'),
    (['georgia', 'грузия', 'tbilisi', 'тбилиси'], 'GE'),
    (['armenia', 'армения', 'yerevan', 'ереван'], 'AM'),
    (['moldova', 'молдова', 'chisinau', 'кишинев'], 'MD'),
    (['ukraine', 'украина', 'kyiv', 'киев'], 'UA'),
    (['belarus', 'беларусь', 'белоруссия', 'minsk', 'минск'], 'BY'),
    (['israel', 'израиль', 'tel aviv', 'тель-авив'], 'IL'),
    (['india', 'индия', 'mumbai', 'delhi', 'дели'], 'IN'),
    (['brazil', 'бразилия', 'sao paulo'], 'BR'),
    (['australia', 'австралия', 'sydney', 'melbourne'], 'AU'),
    (['korea', 'корея', 'seoul', 'сеул'], 'KR'),
  ];

  /// Detects country from [name] or optional [remark].
  static DetectedCountry detect(String? name, [String? remark]) {
    final combined = '${name ?? ''} ${remark ?? ''}'.trim();
    if (combined.isEmpty) {
      return const DetectedCountry(code: 'XX', name: 'Custom');
    }

    // 1. Try extracting from flag emoji
    final emojiCode = extractFromEmoji(combined);
    if (emojiCode != null) {
      final code = emojiCode.toUpperCase();
      return DetectedCountry(code: code, name: _countryNames[code] ?? code);
    }

    // 2. Try bracketed/tagged codes: [DE], (NL), |RU|, DE-, etc.
    final taggedCode = extractTaggedIsoCode(combined);
    if (taggedCode != null) {
      final code = taggedCode.toUpperCase();
      return DetectedCountry(code: code, name: _countryNames[code] ?? code);
    }

    // 3. Try matching known country names or city names
    final namedCode = extractFromName(combined);
    if (namedCode != null) {
      final code = namedCode.toUpperCase();
      return DetectedCountry(code: code, name: _countryNames[code] ?? code);
    }

    // 4. Try generic two-letter uppercase word matching known countries
    final genericIso = extractKnownIsoWord(combined);
    if (genericIso != null) {
      final code = genericIso.toUpperCase();
      return DetectedCountry(code: code, name: _countryNames[code] ?? code);
    }

    return const DetectedCountry(code: 'XX', name: 'Custom');
  }

  /// Extracts ISO-2 code from Unicode Regional Indicator flag emoji pairs.
  static String? extractFromEmoji(String text) {
    final runes = text.runes.toList();
    for (var i = 0; i < runes.length - 1; i++) {
      final r1 = runes[i];
      final r2 = runes[i + 1];
      if (r1 >= 0x1F1E6 && r1 <= 0x1F1FF && r2 >= 0x1F1E6 && r2 <= 0x1F1FF) {
        final c1 = String.fromCharCode(r1 - 0x1F1E6 + 65);
        final c2 = String.fromCharCode(r2 - 0x1F1E6 + 65);
        return '$c1$c2';
      }
    }
    return null;
  }

  /// Extracts tagged ISO codes like [DE], (NL), -US-, |RU|, etc.
  static String? extractTaggedIsoCode(String text) {
    final bracketPattern = RegExp(r'[\[\(\{\|]([A-Za-z]{2})[\]\)\}\|]');
    final match = bracketPattern.firstMatch(text);
    if (match != null) {
      final candidate = match.group(1)!.toUpperCase();
      if (_countryNames.containsKey(candidate)) {
        return candidate;
      }
    }
    return null;
  }

  /// Extracts ISO code by keyword matching in country names and cities.
  static String? extractFromName(String text) {
    final lower = text.toLowerCase();
    for (final item in _keywords) {
      for (final kw in item.$1) {
        // Match word boundaries for Latin or Cyrillic characters
        final pattern = RegExp(
          '(?:^|[^a-zA-Zа-яА-ЯёЁ0-9])${RegExp.escape(kw)}(?:\$|[^a-zA-Zа-яА-ЯёЁ0-9])',
          caseSensitive: false,
        );
        if (pattern.hasMatch(lower)) {
          return item.$2;
        }
      }
    }
    return null;
  }

  /// Extracts standalone 2-letter uppercase word if it is a known country code.
  static String? extractKnownIsoWord(String text) {
    final wordPattern = RegExp(
      r'(?:^|[^a-zA-Z0-9])([A-Z]{2})(?:$|[^a-zA-Z0-9])',
    );
    for (final match in wordPattern.allMatches(text)) {
      final candidate = match.group(1)!;
      if (_countryNames.containsKey(candidate)) {
        return candidate;
      }
    }
    return null;
  }
}
