import 'package:intl/intl.dart';

/// Utility class providing static methods for formatting various data types
/// used throughout the CyberVPN application.
class DataFormatters {
  const DataFormatters._();

  /// Converts a byte count into a human-readable string (KB, MB, GB, etc.).
  ///
  /// Returns '0 B' for zero or negative values.
  static String formatBytes(int bytes) {
    if (bytes <= 0) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const base = 1024;

    int unitIndex = 0;
    double value = bytes.toDouble();

    while (value >= base && unitIndex < units.length - 1) {
      value /= base;
      unitIndex++;
    }

    // Show integers for bytes, one decimal for KB, two decimals for larger units.
    if (unitIndex == 0) {
      return '${value.toInt()} ${units[unitIndex]}';
    }
    if (unitIndex == 1) {
      return '${value.toStringAsFixed(1)} ${units[unitIndex]}';
    }
    return '${value.toStringAsFixed(2)} ${units[unitIndex]}';
  }

  /// Formats a [Duration] into a human-readable string.
  ///
  /// Examples:
  /// - `0d 2h 15m 30s`
  /// - `5m 12s` (omits zero days/hours)
  /// - `0s` for zero duration
  static String formatDuration(Duration duration) {
    if (duration.inSeconds <= 0) return '0s';

    final days = duration.inDays;
    final hours = duration.inHours.remainder(24);
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    final parts = <String>[];
    if (days > 0) parts.add('${days}d');
    if (hours > 0) parts.add('${hours}h');
    if (minutes > 0) parts.add('${minutes}m');
    if (seconds > 0) parts.add('${seconds}s');

    return parts.join(' ');
  }

  /// Formats a network speed given in bytes per second into a readable string.
  ///
  /// Uses standard units: B/s, KB/s, MB/s, GB/s.
  static String formatSpeed(double bytesPerSecond) {
    if (bytesPerSecond <= 0) return '0 B/s';

    const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    const base = 1024;

    int unitIndex = 0;
    double value = bytesPerSecond;

    while (value >= base && unitIndex < units.length - 1) {
      value /= base;
      unitIndex++;
    }

    if (unitIndex == 0) {
      return '${value.toInt()} ${units[unitIndex]}';
    }
    return '${value.toStringAsFixed(2)} ${units[unitIndex]}';
  }

  /// Formats a [DateTime] into a localized date string.
  ///
  /// Output example: `Jan 31, 2026`
  static String formatDate(DateTime date) {
    return DateFormat.yMMMd().format(date);
  }

  /// Formats a monetary [amount] with the given [currency] code.
  ///
  /// Defaults to USD. Uses `intl` for locale-aware formatting.
  static String formatCurrency(double amount, {String currency = 'USD'}) {
    final format = NumberFormat.currency(
      symbol: _currencySymbol(currency),
      decimalDigits: 2,
    );
    return format.format(amount);
  }

  /// Formats a [value] between 0 and 1 (or 0-100) as a percentage string.
  ///
  /// Values <= 1.0 are treated as ratios and multiplied by 100.
  /// Values > 1.0 are treated as already being percentages.
  static String formatPercentage(double value) {
    final percentage = value <= 1.0 ? value * 100 : value;
    return '${percentage.toStringAsFixed(1)}%';
  }

  /// Returns the symbol for common currency codes, falling back to the code itself.
  static String _currencySymbol(String currency) {
    const symbols = {
      'USD': '\$',
      'EUR': '\u20AC',
      'GBP': '\u00A3',
      'RUB': '\u20BD',
      'UAH': '\u20B4',
      'TRY': '\u20BA',
      'JPY': '\u00A5',
      'CNY': '\u00A5',
    };
    return symbols[currency.toUpperCase()] ?? currency;
  }
}
