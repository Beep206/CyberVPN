import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/utils/data_formatters.dart';

void main() {
  // ===========================================================================
  // formatBytes tests
  // ===========================================================================

  group('DataFormatters.formatBytes', () {
    test('returns "0 B" for zero bytes', () {
      expect(DataFormatters.formatBytes(0), equals('0 B'));
    });

    test('returns "0 B" for negative bytes', () {
      expect(DataFormatters.formatBytes(-100), equals('0 B'));
    });

    test('formats bytes (< 1024) without decimals', () {
      expect(DataFormatters.formatBytes(1), equals('1 B'));
      expect(DataFormatters.formatBytes(512), equals('512 B'));
      expect(DataFormatters.formatBytes(1023), equals('1023 B'));
    });

    test('formats exactly 1024 bytes as KB', () {
      expect(DataFormatters.formatBytes(1024), equals('1.0 KB'));
    });

    test('formats KB with one decimal', () {
      expect(DataFormatters.formatBytes(1536), equals('1.5 KB'));
      expect(DataFormatters.formatBytes(10240), equals('10.0 KB'));
    });

    test('formats exactly 1 MB', () {
      expect(DataFormatters.formatBytes(1048576), equals('1.00 MB'));
    });

    test('formats MB with two decimals', () {
      // 1.5 MB = 1_572_864 bytes
      expect(DataFormatters.formatBytes(1572864), equals('1.50 MB'));
    });

    test('formats exactly 1 GB', () {
      expect(DataFormatters.formatBytes(1073741824), equals('1.00 GB'));
    });

    test('formats GB with two decimals', () {
      // 2.5 GB = 2_684_354_560
      expect(DataFormatters.formatBytes(2684354560), equals('2.50 GB'));
    });

    test('formats exactly 1 TB', () {
      expect(DataFormatters.formatBytes(1099511627776), equals('1.00 TB'));
    });

    test('handles very large values (multiple TB)', () {
      // 5 TB
      final result = DataFormatters.formatBytes(5497558138880);
      expect(result, contains('TB'));
      expect(result, startsWith('5.00'));
    });
  });

  // ===========================================================================
  // formatDuration tests
  // ===========================================================================

  group('DataFormatters.formatDuration', () {
    test('returns "0s" for zero duration', () {
      expect(DataFormatters.formatDuration(Duration.zero), equals('0s'));
    });

    test('returns "0s" for negative duration', () {
      expect(
        DataFormatters.formatDuration(const Duration(seconds: -5)),
        equals('0s'),
      );
    });

    test('formats seconds only', () {
      expect(
        DataFormatters.formatDuration(const Duration(seconds: 45)),
        equals('45s'),
      );
    });

    test('formats minutes and seconds', () {
      expect(
        DataFormatters.formatDuration(const Duration(minutes: 5, seconds: 12)),
        equals('5m 12s'),
      );
    });

    test('formats hours, minutes, and seconds', () {
      expect(
        DataFormatters.formatDuration(
          const Duration(hours: 2, minutes: 15, seconds: 30),
        ),
        equals('2h 15m 30s'),
      );
    });

    test('formats days, hours, minutes, and seconds', () {
      expect(
        DataFormatters.formatDuration(
          const Duration(days: 1, hours: 3, minutes: 45, seconds: 10),
        ),
        equals('1d 3h 45m 10s'),
      );
    });

    test('omits zero components', () {
      // 1 hour exactly
      expect(
        DataFormatters.formatDuration(const Duration(hours: 1)),
        equals('1h'),
      );
      // 1 day and 30 seconds, no hours or minutes
      expect(
        DataFormatters.formatDuration(
          const Duration(days: 1, seconds: 30),
        ),
        equals('1d 30s'),
      );
    });

    test('handles exactly 1 day', () {
      expect(
        DataFormatters.formatDuration(const Duration(days: 1)),
        equals('1d'),
      );
    });
  });

  // ===========================================================================
  // formatSpeed tests
  // ===========================================================================

  group('DataFormatters.formatSpeed', () {
    test('returns "0 B/s" for zero speed', () {
      expect(DataFormatters.formatSpeed(0), equals('0 B/s'));
    });

    test('returns "0 B/s" for negative speed', () {
      expect(DataFormatters.formatSpeed(-100), equals('0 B/s'));
    });

    test('formats bytes per second without decimals', () {
      expect(DataFormatters.formatSpeed(512), equals('512 B/s'));
      expect(DataFormatters.formatSpeed(1023), equals('1023 B/s'));
    });

    test('formats exactly 1 KB/s', () {
      expect(DataFormatters.formatSpeed(1024), equals('1.00 KB/s'));
    });

    test('formats KB/s with two decimals', () {
      expect(DataFormatters.formatSpeed(1536), equals('1.50 KB/s'));
    });

    test('formats exactly 1 MB/s', () {
      expect(DataFormatters.formatSpeed(1048576), equals('1.00 MB/s'));
    });

    test('formats GB/s for very high speeds', () {
      // 1 GB/s = 1_073_741_824
      expect(DataFormatters.formatSpeed(1073741824), equals('1.00 GB/s'));
    });

    test('formats fractional MB/s', () {
      // 2.5 MB/s = 2_621_440 bytes/s
      expect(DataFormatters.formatSpeed(2621440), equals('2.50 MB/s'));
    });
  });

  // ===========================================================================
  // formatDate tests
  // ===========================================================================

  group('DataFormatters.formatDate', () {
    test('formats a known date', () {
      final date = DateTime(2026, 1, 31);
      final result = DataFormatters.formatDate(date);
      // DateFormat.yMMMd() produces "Jan 31, 2026" in en_US
      expect(result, contains('Jan'));
      expect(result, contains('31'));
      expect(result, contains('2026'));
    });

    test('formats another date', () {
      final date = DateTime(2025, 12, 25);
      final result = DataFormatters.formatDate(date);
      expect(result, contains('Dec'));
      expect(result, contains('25'));
      expect(result, contains('2025'));
    });

    test('formats date at epoch', () {
      final date = DateTime(1970, 1, 1);
      final result = DataFormatters.formatDate(date);
      expect(result, contains('1970'));
    });
  });

  // ===========================================================================
  // formatCurrency tests
  // ===========================================================================

  group('DataFormatters.formatCurrency', () {
    test('formats USD by default', () {
      final result = DataFormatters.formatCurrency(9.99);
      expect(result, contains('9.99'));
      expect(result, contains('\$'));
    });

    test('formats zero amount', () {
      final result = DataFormatters.formatCurrency(0);
      expect(result, contains('0.00'));
    });

    test('formats EUR currency', () {
      final result = DataFormatters.formatCurrency(19.99, currency: 'EUR');
      expect(result, contains('19.99'));
    });

    test('formats large amount', () {
      final result = DataFormatters.formatCurrency(1234567.89);
      expect(result, anyOf(contains('1234567.89'), contains('1,234,567.89')));
    });
  });

  // ===========================================================================
  // formatPercentage tests
  // ===========================================================================

  group('DataFormatters.formatPercentage', () {
    test('formats ratio (0.0 to 1.0) as percentage', () {
      expect(DataFormatters.formatPercentage(0.5), equals('50.0%'));
      expect(DataFormatters.formatPercentage(1.0), equals('100.0%'));
      expect(DataFormatters.formatPercentage(0.0), equals('0.0%'));
    });

    test('formats already-percentage values (> 1.0)', () {
      expect(DataFormatters.formatPercentage(75.0), equals('75.0%'));
      expect(DataFormatters.formatPercentage(100.0), equals('100.0%'));
    });

    test('formats fractional percentages', () {
      expect(DataFormatters.formatPercentage(0.333), equals('33.3%'));
    });
  });
}
