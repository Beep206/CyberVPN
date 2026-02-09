import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:intl/intl.dart';

/// Utility class providing locale-aware formatting methods for dates, times,
/// numbers, traffic, speed, and currency throughout the CyberVPN application.
///
/// All methods support multiple locales and handle edge cases with fallback
/// to English (en-US) when an invalid locale is provided.
///
/// **Note on locale initialization**: This class uses the `intl` package but
/// does not require explicit locale initialization. It relies on Flutter's
/// automatic locale initialization when used within a localized app context.
/// For standalone usage or tests, ensure `IntlGlobalizations.delegate` is
/// properly configured in your MaterialApp.
///
/// Example usage:
/// ```dart
/// final formatted = L10nFormatters.formatDate(
///   DateTime.now(),
///   'de',
///   format: DateFormatType.long,
/// ); // Will format according to device/app locale
/// ```
class L10nFormatters {
  const L10nFormatters._();

  /// Default locale used when no preference is set or locale is unsupported.
  static const String _defaultLocale = 'en_US';

  /// Formats a [DateTime] into a locale-aware date string.
  ///
  /// Supports three format types:
  /// - [DateFormatType.short]: Numeric date (e.g., "02/01/2026", "01.02.2026")
  /// - [DateFormatType.long]: Full date (e.g., "February 1, 2026", "1. Februar 2026")
  /// - [DateFormatType.relative]: Relative time (e.g., "2 hours ago", "yesterday")
  ///
  /// Parameters:
  /// - [date]: The DateTime to format
  /// - [locale]: Locale code (e.g., 'en', 'de', 'ar-SA')
  /// - [format]: Format type (defaults to [DateFormatType.short])
  /// - [l10n]: Required for [DateFormatType.relative] to provide localized strings
  ///
  /// Returns a formatted date string.
  ///
  /// Example:
  /// ```dart
  /// formatDate(DateTime(2026, 2, 1), 'en'); // "2/1/2026"
  /// formatDate(DateTime(2026, 2, 1), 'de', format: DateFormatType.long);
  /// // "1. Februar 2026"
  /// ```
  static String formatDate(
    DateTime date,
    String locale, {
    DateFormatType format = DateFormatType.short,
    AppLocalizations? l10n,
  }) {
    final normalizedLocale = _normalizeLocale(locale);

    switch (format) {
      case DateFormatType.short:
        return _formatShortDate(date, normalizedLocale);
      case DateFormatType.long:
        return _formatLongDate(date, normalizedLocale);
      case DateFormatType.relative:
        return _formatRelativeDate(date, l10n);
    }
  }

  /// Formats a short date based on locale conventions.
  static String _formatShortDate(DateTime date, String locale) {
    try {
      final formatter = DateFormat.yMd(locale);
      return formatter.format(date);
    } catch (e) {
      // Fallback to simple ISO format
      return '${date.month}/${date.day}/${date.year}';
    }
  }

  /// Formats a long date based on locale conventions.
  static String _formatLongDate(DateTime date, String locale) {
    try {
      final formatter = DateFormat.yMMMMd(locale);
      return formatter.format(date);
    } catch (e) {
      // Fallback to English month names
      const months = [
        'January',
        'February',
        'March',
        'April',
        'May',
        'June',
        'July',
        'August',
        'September',
        'October',
        'November',
        'December',
      ];
      return '${months[date.month - 1]} ${date.day}, ${date.year}';
    }
  }

  /// Formats a [DateTime] into a locale-aware time string.
  ///
  /// Automatically uses 12-hour format with AM/PM for locales like en-US,
  /// and 24-hour format for locales like de-DE, fr-FR, ja-JP.
  ///
  /// Parameters:
  /// - [time]: The DateTime to format
  /// - [locale]: Locale code (e.g., 'en', 'de', 'ar-SA')
  ///
  /// Returns a formatted time string.
  ///
  /// Example:
  /// ```dart
  /// final dt = DateTime(2026, 2, 1, 14, 30);
  /// formatTime(dt, 'en'); // "2:30 PM"
  /// formatTime(dt, 'de'); // "14:30"
  /// formatTime(dt, 'ja'); // "14:30"
  /// ```
  static String formatTime(DateTime time, String locale) {
    final normalizedLocale = _normalizeLocale(locale);

    // Locales that prefer 12-hour format
    const twelveHourLocales = {
      'en',
      'en_US',
      'en_GB', // UK uses both, but 12-hour is common
      'hi',
      'th',
    };

    final use12Hour = twelveHourLocales.any(normalizedLocale.startsWith);

    try {
      if (use12Hour) {
        final formatter = DateFormat.jm(normalizedLocale);
        return formatter.format(time);
      } else {
        final formatter = DateFormat.Hm(normalizedLocale);
        return formatter.format(time);
      }
    } catch (e) {
      // Fallback to manual formatting
      if (use12Hour) {
        final hour = time.hour == 0
            ? 12
            : (time.hour > 12 ? time.hour - 12 : time.hour);
        final period = time.hour >= 12 ? 'PM' : 'AM';
        return '$hour:${time.minute.toString().padLeft(2, '0')} $period';
      } else {
        return '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
      }
    }
  }

  /// Formats a relative date like "2 hours ago", "yesterday", "last week".
  ///
  /// Uses [AppLocalizations] for proper localized strings when provided,
  /// otherwise falls back to English.
  static String _formatRelativeDate(DateTime date, AppLocalizations? l10n) {
    final now = DateTime.now();
    final difference = now.difference(date);

    // Future dates
    if (difference.isNegative) {
      final futureDiff = date.difference(now);
      if (futureDiff.inSeconds < 60) {
        return l10n?.relativeInSeconds ?? 'in a few seconds';
      }
      if (futureDiff.inMinutes < 60) {
        final minutes = futureDiff.inMinutes;
        return l10n?.relativeInMinutes(minutes) ??
            'in $minutes ${minutes == 1 ? 'minute' : 'minutes'}';
      }
      if (futureDiff.inHours < 24) {
        final hours = futureDiff.inHours;
        return l10n?.relativeInHours(hours) ??
            'in $hours ${hours == 1 ? 'hour' : 'hours'}';
      }
      return _formatShortDate(date, _defaultLocale);
    }

    // Past dates
    if (difference.inSeconds < 60) {
      return l10n?.relativeJustNow ?? 'just now';
    }

    if (difference.inMinutes < 60) {
      final minutes = difference.inMinutes;
      return l10n?.relativeMinutesAgo(minutes) ??
          '$minutes ${minutes == 1 ? 'minute' : 'minutes'} ago';
    }

    if (difference.inHours < 24) {
      final hours = difference.inHours;
      return l10n?.relativeHoursAgo(hours) ??
          '$hours ${hours == 1 ? 'hour' : 'hours'} ago';
    }

    if (difference.inDays == 1) {
      return l10n?.relativeYesterday ?? 'yesterday';
    }

    if (difference.inDays < 7) {
      final days = difference.inDays;
      return l10n?.relativeDaysAgo(days) ??
          '$days ${days == 1 ? 'day' : 'days'} ago';
    }

    if (difference.inDays < 30) {
      final weeks = (difference.inDays / 7).floor();
      return l10n?.relativeWeeksAgo(weeks) ??
          '$weeks ${weeks == 1 ? 'week' : 'weeks'} ago';
    }

    if (difference.inDays < 365) {
      final months = (difference.inDays / 30).floor();
      return l10n?.relativeMonthsAgo(months) ??
          '$months ${months == 1 ? 'month' : 'months'} ago';
    }

    final years = (difference.inDays / 365).floor();
    return l10n?.relativeYearsAgo(years) ??
        '$years ${years == 1 ? 'year' : 'years'} ago';
  }

  /// Formats a number with locale-specific decimal and thousand separators.
  ///
  /// Automatically applies locale conventions:
  /// - en-US: 1,234.56
  /// - de-DE: 1.234,56
  /// - fr-FR: 1 234,56
  ///
  /// Parameters:
  /// - [value]: The number to format
  /// - [locale]: Locale code (e.g., 'en', 'de', 'fr')
  /// - [decimalDigits]: Number of decimal places (defaults to 2)
  ///
  /// Returns a formatted number string.
  ///
  /// Example:
  /// ```dart
  /// formatNumber(1234.56, 'en'); // "1,234.56"
  /// formatNumber(1234.56, 'de'); // "1.234,56"
  /// formatNumber(1234.56, 'fr'); // "1 234,56"
  /// formatNumber(1234, 'en', decimalDigits: 0); // "1,234"
  /// ```
  static String formatNumber(
    num value,
    String locale, {
    int decimalDigits = 2,
  }) {
    final normalizedLocale = _normalizeLocale(locale);

    try {
      final formatter = NumberFormat.decimalPatternDigits(
        locale: normalizedLocale,
        decimalDigits: decimalDigits,
      );
      return formatter.format(value);
    } catch (e) {
      // Fallback to simple formatting
      return value.toStringAsFixed(decimalDigits);
    }
  }

  /// Formats traffic data in bytes with automatic unit scaling.
  ///
  /// Automatically scales to appropriate unit (B, KB, MB, GB, TB) using
  /// 1024-based conversion and applies locale number formatting.
  ///
  /// Parameters:
  /// - [bytes]: Number of bytes to format
  /// - [locale]: Locale code for number formatting
  ///
  /// Returns formatted traffic string with unit (e.g., "1.5 MB").
  ///
  /// Example:
  /// ```dart
  /// formatTraffic(1023, 'en'); // "1,023 B"
  /// formatTraffic(1024, 'en'); // "1.0 KB"
  /// formatTraffic(1500000, 'en'); // "1.5 MB"
  /// formatTraffic(2500000000, 'de'); // "2,3 GB"
  /// formatTraffic(3500000000000, 'fr'); // "3,3 TB"
  /// ```
  static String formatTraffic(int bytes, String locale) {
    if (bytes < 0) {
      return '0 B';
    }

    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const divisor = 1024;

    // Handle zero and very small values
    if (bytes < divisor) {
      return '${formatNumber(bytes, locale, decimalDigits: 0)} B';
    }

    var value = bytes.toDouble();
    var unitIndex = 0;

    // Scale down until we find the appropriate unit
    while (value >= divisor && unitIndex < units.length - 1) {
      value /= divisor;
      unitIndex++;
    }

    // Use 1 decimal place for KB and above
    final formattedValue = formatNumber(value, locale, decimalDigits: 1);
    return '$formattedValue ${units[unitIndex]}';
  }

  /// Formats network speed in bits per second with automatic unit scaling.
  ///
  /// Automatically scales to Kbps, Mbps, or Gbps using 1000-based conversion
  /// (as per networking standards) and applies locale number formatting.
  ///
  /// Parameters:
  /// - [bitsPerSecond]: Speed in bits per second
  /// - [locale]: Locale code for number formatting
  ///
  /// Returns formatted speed string with unit (e.g., "1.5 Mbps").
  ///
  /// Example:
  /// ```dart
  /// formatSpeed(800, 'en'); // "800 bps"
  /// formatSpeed(1500, 'en'); // "1.5 Kbps"
  /// formatSpeed(1500000, 'en'); // "1.5 Mbps"
  /// formatSpeed(2500000000, 'de'); // "2,5 Gbps"
  /// ```
  static String formatSpeed(double bitsPerSecond, String locale) {
    if (bitsPerSecond < 0) {
      return '0 bps';
    }

    const units = ['bps', 'Kbps', 'Mbps', 'Gbps'];
    const divisor = 1000; // Networking uses 1000, not 1024

    // Handle zero and very small values
    if (bitsPerSecond < divisor) {
      return '${formatNumber(bitsPerSecond, locale, decimalDigits: 0)} bps';
    }

    var value = bitsPerSecond;
    var unitIndex = 0;

    // Scale down until we find the appropriate unit
    while (value >= divisor && unitIndex < units.length - 1) {
      value /= divisor;
      unitIndex++;
    }

    // Use 1 decimal place for Kbps and above
    final formattedValue = formatNumber(value, locale, decimalDigits: 1);
    return '$formattedValue ${units[unitIndex]}';
  }

  /// Formats currency amounts with locale-specific formatting.
  ///
  /// Handles currency symbols, decimal places, and locale-specific formatting
  /// conventions including right-to-left currencies for Arabic locales.
  ///
  /// Supports major currencies:
  /// - USD: US Dollar ($)
  /// - EUR: Euro (€)
  /// - GBP: British Pound (£)
  /// - RUB: Russian Ruble (₽)
  /// - CNY: Chinese Yuan (¥)
  /// - JPY: Japanese Yen (¥)
  ///
  /// Parameters:
  /// - [amount]: The currency amount to format
  /// - [currencyCode]: ISO 4217 currency code (e.g., 'USD', 'EUR', 'JPY')
  /// - [locale]: Locale code for formatting conventions
  ///
  /// Returns a formatted currency string.
  ///
  /// Example:
  /// ```dart
  /// formatCurrency(1234.56, 'USD', 'en'); // "$1,234.56"
  /// formatCurrency(1234.56, 'EUR', 'de'); // "1.234,56 €"
  /// formatCurrency(1234.56, 'GBP', 'en_GB'); // "£1,234.56"
  /// formatCurrency(1234, 'JPY', 'ja'); // "¥1,234"
  /// formatCurrency(-50.25, 'USD', 'en'); // "-$50.25"
  /// ```
  static String formatCurrency(
    double amount,
    String currencyCode,
    String locale,
  ) {
    final normalizedLocale = _normalizeLocale(locale);

    try {
      final formatter = NumberFormat.currency(
        locale: normalizedLocale,
        symbol: _getCurrencySymbol(currencyCode),
        decimalDigits: _getCurrencyDecimalDigits(currencyCode),
      );
      return formatter.format(amount);
    } catch (e) {
      // Fallback to simple formatting
      final symbol = _getCurrencySymbol(currencyCode);
      final decimals = _getCurrencyDecimalDigits(currencyCode);
      final formattedAmount = amount.abs().toStringAsFixed(decimals);
      final prefix = amount < 0 ? '-' : '';
      return '$prefix$symbol$formattedAmount';
    }
  }

  /// Gets the currency symbol for a given currency code.
  static String _getCurrencySymbol(String currencyCode) {
    const symbolMap = {
      'USD': r'$',
      'EUR': '€',
      'GBP': '£',
      'RUB': '₽',
      'CNY': '¥',
      'JPY': '¥',
      'KRW': '₩',
      'INR': '₹',
      'BRL': r'R$',
      'AUD': r'A$',
      'CAD': r'C$',
      'CHF': 'Fr',
      'MXN': r'$',
      'TRY': '₺',
      'AED': 'د.إ',
      'SAR': 'ر.س',
    };

    return symbolMap[currencyCode.toUpperCase()] ?? currencyCode;
  }

  /// Gets the number of decimal digits for a currency.
  static int _getCurrencyDecimalDigits(String currencyCode) {
    // Currencies with no decimal places
    const zeroDecimalCurrencies = {
      'JPY', // Japanese Yen
      'KRW', // Korean Won
      'VND', // Vietnamese Dong
      'IDR', // Indonesian Rupiah
      'CLP', // Chilean Peso
    };

    return zeroDecimalCurrencies.contains(currencyCode.toUpperCase()) ? 0 : 2;
  }

  /// Normalizes a locale code to the format expected by intl package.
  ///
  /// Handles various locale formats:
  /// - 'en' -> 'en_US'
  /// - 'en-US' -> 'en_US'
  /// - 'zh_Hant' -> 'zh_TW'
  /// - 'ar-SA' -> 'ar_SA'
  /// - 'de' -> 'de_DE'
  static String _normalizeLocale(String locale) {
    if (locale.isEmpty) return _defaultLocale;

    // Replace hyphens with underscores for intl compatibility
    final normalized = locale.replaceAll('-', '_');

    // Handle special cases and add country codes for common locales
    final localeMap = {
      // High priority
      'en': 'en_US',
      'hi': 'hi_IN',
      'id': 'id_ID',
      'ru': 'ru_RU',
      'zh': 'zh_CN',
      // Medium priority
      'ar': 'ar_SA',
      'fa': 'fa_IR',
      'tr': 'tr_TR',
      'vi': 'vi_VN',
      'ur': 'ur_PK',
      // Low priority
      'th': 'th_TH',
      'bn': 'bn_BD',
      'ms': 'ms_MY',
      'es': 'es_ES',
      'kk': 'kk_KZ',
      'be': 'be_BY',
      'my': 'my_MM',
      'uz': 'uz_UZ',
      // Non-viable
      'ha': 'ha_NG',
      'yo': 'yo_NG',
      'ku': 'ku_IQ',
      'am': 'am_ET',
      'fr': 'fr_FR',
      'tk': 'tk_TM',
      // Additional
      'ja': 'ja_JP',
      'ko': 'ko_KR',
      'he': 'he_IL',
      'de': 'de_DE',
      'pt': 'pt_PT',
      'it': 'it_IT',
      'nl': 'nl_NL',
      'pl': 'pl_PL',
      'fil': 'fil_PH',
      'uk': 'uk_UA',
      'cs': 'cs_CZ',
      'ro': 'ro_RO',
      'hu': 'hu_HU',
      'sv': 'sv_SE',
    };

    // Check if we have a mapping for this locale
    if (localeMap.containsKey(normalized)) {
      return localeMap[normalized]!;
    }

    return normalized;
  }
}

/// Date format types for [L10nFormatters.formatDate].
enum DateFormatType {
  /// Short numeric format (e.g., "02/01/2026", "01.02.2026")
  short,

  /// Long textual format (e.g., "February 1, 2026", "1. Februar 2026")
  long,

  /// Relative format (e.g., "2 hours ago", "yesterday")
  relative,
}
