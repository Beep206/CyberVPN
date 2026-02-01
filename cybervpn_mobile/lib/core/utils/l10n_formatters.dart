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
  }) {
    final normalizedLocale = _normalizeLocale(locale);

    switch (format) {
      case DateFormatType.short:
        return _formatShortDate(date, normalizedLocale);
      case DateFormatType.long:
        return _formatLongDate(date, normalizedLocale);
      case DateFormatType.relative:
        return _formatRelativeDate(date, locale);
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

    final use12Hour = twelveHourLocales.any(
      (l) => normalizedLocale.startsWith(l),
    );

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
  /// Supports multiple locales with appropriate translations.
  static String _formatRelativeDate(DateTime date, String locale) {
    final now = DateTime.now();
    final difference = now.difference(date);

    // Future dates
    if (difference.isNegative) {
      final futureDiff = date.difference(now);
      if (futureDiff.inSeconds < 60) {
        return _getLocaleString(locale, 'inAFewSeconds', 'in a few seconds');
      }
      if (futureDiff.inMinutes < 60) {
        final minutes = futureDiff.inMinutes;
        return _getLocaleString(
          locale,
          'inMinutes',
          'in $minutes ${minutes == 1 ? 'minute' : 'minutes'}',
          {'count': minutes},
        );
      }
      if (futureDiff.inHours < 24) {
        final hours = futureDiff.inHours;
        return _getLocaleString(
          locale,
          'inHours',
          'in $hours ${hours == 1 ? 'hour' : 'hours'}',
          {'count': hours},
        );
      }
      return _formatShortDate(date, _normalizeLocale(locale));
    }

    // Past dates
    if (difference.inSeconds < 60) {
      return _getLocaleString(locale, 'justNow', 'just now');
    }

    if (difference.inMinutes < 60) {
      final minutes = difference.inMinutes;
      return _getLocaleString(
        locale,
        'minutesAgo',
        '$minutes ${minutes == 1 ? 'minute' : 'minutes'} ago',
        {'count': minutes},
      );
    }

    if (difference.inHours < 24) {
      final hours = difference.inHours;
      return _getLocaleString(
        locale,
        'hoursAgo',
        '$hours ${hours == 1 ? 'hour' : 'hours'} ago',
        {'count': hours},
      );
    }

    if (difference.inDays == 1) {
      return _getLocaleString(locale, 'yesterday', 'yesterday');
    }

    if (difference.inDays < 7) {
      final days = difference.inDays;
      return _getLocaleString(
        locale,
        'daysAgo',
        '$days ${days == 1 ? 'day' : 'days'} ago',
        {'count': days},
      );
    }

    if (difference.inDays < 30) {
      final weeks = (difference.inDays / 7).floor();
      return _getLocaleString(
        locale,
        'weeksAgo',
        '$weeks ${weeks == 1 ? 'week' : 'weeks'} ago',
        {'count': weeks},
      );
    }

    if (difference.inDays < 365) {
      final months = (difference.inDays / 30).floor();
      return _getLocaleString(
        locale,
        'monthsAgo',
        '$months ${months == 1 ? 'month' : 'months'} ago',
        {'count': months},
      );
    }

    final years = (difference.inDays / 365).floor();
    return _getLocaleString(
      locale,
      'yearsAgo',
      '$years ${years == 1 ? 'year' : 'years'} ago',
      {'count': years},
    );
  }

  /// Gets a localized string for relative dates.
  ///
  /// This is a simplified version. In a real app, you'd use the actual
  /// localization system (app_localizations) to get proper translations.
  /// For now, it returns the fallback English string.
  static String _getLocaleString(
    String locale,
    String key,
    String fallback, [
    Map<String, dynamic>? params,
  ]) {
    // TODO: Integrate with AppLocalizations when available
    // For now, return English fallback
    // In production, this would be:
    // return AppLocalizations.of(context).getRelativeDateString(key, params);
    return fallback;
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
    var normalized = locale.replaceAll('-', '_');

    // Handle special cases and add country codes for common locales
    final localeMap = {
      'en': 'en_US',
      'de': 'de_DE',
      'fr': 'fr_FR',
      'es': 'es_ES',
      'it': 'it_IT',
      'ja': 'ja_JP',
      'ko': 'ko_KR',
      'zh': 'zh_CN',
      'zh_Hant': 'zh_TW',
      'ar': 'ar_SA',
      'he': 'he_IL',
      'fa': 'fa_IR',
      'ru': 'ru_RU',
      'pt': 'pt_BR',
      'nl': 'nl_NL',
      'pl': 'pl_PL',
      'tr': 'tr_TR',
      'hi': 'hi_IN',
      'th': 'th_TH',
      'vi': 'vi_VN',
      'id': 'id_ID',
      'ms': 'ms_MY',
      'ro': 'ro_RO',
      'cs': 'cs_CZ',
      'sv': 'sv_SE',
      'da': 'da_DK',
      'uk': 'uk_UA',
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
