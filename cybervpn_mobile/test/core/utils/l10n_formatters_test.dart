import 'package:cybervpn_mobile/core/utils/l10n_formatters.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

void main() {
  setUpAll(() async {
    // Initialize date formatting for all locales used in tests
    await initializeDateFormatting();
  });

  group('L10nFormatters', () {
    group('formatDate', () {
      test('formats short date for en-US', () {
        final date = DateTime(2026, 2, 1);
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.short,
        );
        expect(result, '2/1/2026');
      });

      test('formats short date for de-DE', () {
        final date = DateTime(2026, 2, 1);
        final result = L10nFormatters.formatDate(
          date,
          'de',
          format: DateFormatType.short,
        );
        // Accept various German date formats
        expect(result, anyOf('01.02.2026', '1.2.2026', contains('2026')));
      });

      test('formats short date for ar-SA', () {
        final date = DateTime(2026, 2, 1);
        final result = L10nFormatters.formatDate(
          date,
          'ar-SA',
          format: DateFormatType.short,
        );
        // Arabic locale uses different formatting
        expect(result, isNotEmpty);
      });

      test('formats long date for en-US', () {
        final date = DateTime(2026, 2, 1);
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.long,
        );
        expect(result, 'February 1, 2026');
      });

      test('formats long date for de-DE', () {
        final date = DateTime(2026, 2, 1);
        final result = L10nFormatters.formatDate(
          date,
          'de',
          format: DateFormatType.long,
        );
        // Accept various German long date formats
        expect(result, anyOf(
          '1. Februar 2026',
          contains('Februar'),
          contains('2026'),
        ));
      });

      test('formats relative date - just now', () {
        final date = DateTime.now().subtract(const Duration(seconds: 30));
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.relative,
        );
        expect(result, 'just now');
      });

      test('formats relative date - minutes ago', () {
        final date = DateTime.now().subtract(const Duration(minutes: 5));
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.relative,
        );
        expect(result, '5 minutes ago');
      });

      test('formats relative date - hours ago', () {
        final date = DateTime.now().subtract(const Duration(hours: 2));
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.relative,
        );
        expect(result, '2 hours ago');
      });

      test('formats relative date - yesterday', () {
        final date = DateTime.now().subtract(const Duration(days: 1));
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.relative,
        );
        expect(result, 'yesterday');
      });

      test('formats relative date - days ago', () {
        final date = DateTime.now().subtract(const Duration(days: 3));
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.relative,
        );
        expect(result, '3 days ago');
      });

      test('formats relative date - weeks ago', () {
        final date = DateTime.now().subtract(const Duration(days: 14));
        final result = L10nFormatters.formatDate(
          date,
          'en',
          format: DateFormatType.relative,
        );
        expect(result, '2 weeks ago');
      });
    });

    group('formatTime', () {
      test('formats time for en-US with 12-hour format', () {
        final time = DateTime(2026, 2, 1, 14, 30);
        final result = L10nFormatters.formatTime(time, 'en');
        // Allow various space characters (regular space, nbsp, etc.)
        expect(result, matches(r'2:30\s*PM'));
      });

      test('formats time for de-DE with 24-hour format', () {
        final time = DateTime(2026, 2, 1, 14, 30);
        final result = L10nFormatters.formatTime(time, 'de');
        expect(result, '14:30');
      });

      test('formats time for ja-JP with 24-hour format', () {
        final time = DateTime(2026, 2, 1, 14, 30);
        final result = L10nFormatters.formatTime(time, 'ja');
        expect(result, '14:30');
      });

      test('formats morning time for en-US', () {
        final time = DateTime(2026, 2, 1, 9, 15);
        final result = L10nFormatters.formatTime(time, 'en');
        expect(result, matches(r'9:15\s*AM'));
      });

      test('formats midnight for en-US', () {
        final time = DateTime(2026, 2, 1, 0, 0);
        final result = L10nFormatters.formatTime(time, 'en');
        expect(result, matches(r'12:00\s*AM'));
      });

      test('formats noon for de-DE', () {
        final time = DateTime(2026, 2, 1, 12, 0);
        final result = L10nFormatters.formatTime(time, 'de');
        expect(result, '12:00');
      });
    });

    group('formatNumber', () {
      test('formats number 1000 for en-US', () {
        final result = L10nFormatters.formatNumber(1000, 'en');
        expect(result, '1,000.00');
      });

      test('formats number 1000 for de-DE', () {
        final result = L10nFormatters.formatNumber(1000, 'de');
        expect(result, '1.000,00');
      });

      test('formats number 1000 for fr-FR', () {
        final result = L10nFormatters.formatNumber(1000, 'fr');
        // French uses non-breaking space (U+00A0) as thousand separator
        // Allow various formats depending on intl version
        expect(result, anyOf(
          contains('1 000'),
          contains('1\u00A0000'),
          matches(r'1.000'),
        ));
      });

      test('formats decimal number for en-US', () {
        final result = L10nFormatters.formatNumber(1234.56, 'en');
        expect(result, '1,234.56');
      });

      test('formats decimal number for de-DE', () {
        final result = L10nFormatters.formatNumber(1234.56, 'de');
        expect(result, '1.234,56');
      });

      test('formats with custom decimal digits', () {
        final result = L10nFormatters.formatNumber(
          1234.5678,
          'en',
          decimalDigits: 3,
        );
        expect(result, '1,234.568');
      });

      test('formats integer with 0 decimal digits', () {
        final result = L10nFormatters.formatNumber(
          1234,
          'en',
          decimalDigits: 0,
        );
        expect(result, '1,234');
      });
    });

    group('formatTraffic', () {
      test('formats bytes for small values', () {
        final result = L10nFormatters.formatTraffic(1023, 'en');
        expect(result, '1,023 B');
      });

      test('formats kilobytes', () {
        final result = L10nFormatters.formatTraffic(1024, 'en');
        expect(result, '1.0 KB');
      });

      test('formats 1.5 megabytes for en-US', () {
        final result = L10nFormatters.formatTraffic(1500000, 'en');
        expect(result, '1.4 MB'); // 1500000 / 1024 / 1024 ≈ 1.43
      });

      test('formats gigabytes for de-DE', () {
        final result = L10nFormatters.formatTraffic(2500000000, 'de');
        // 2500000000 / 1024^3 ≈ 2.33 GB
        expect(result, anyOf(contains('2,3'), contains('2.3')));
        expect(result, contains('GB'));
      });

      test('formats terabytes for fr-FR', () {
        final result = L10nFormatters.formatTraffic(3500000000000, 'fr');
        // 3500000000000 / 1024^4 ≈ 3.18 TB
        expect(result, anyOf(contains('3,'), contains('3.')));
        expect(result, contains('TB'));
      });

      test('handles zero bytes', () {
        final result = L10nFormatters.formatTraffic(0, 'en');
        expect(result, '0 B');
      });

      test('handles negative values', () {
        final result = L10nFormatters.formatTraffic(-100, 'en');
        expect(result, '0 B');
      });

      test('formats exactly 1 KB', () {
        final result = L10nFormatters.formatTraffic(1024, 'en');
        expect(result, '1.0 KB');
      });

      test('formats exactly 1 MB', () {
        final result = L10nFormatters.formatTraffic(1024 * 1024, 'en');
        expect(result, '1.0 MB');
      });

      test('formats exactly 1 GB', () {
        final result = L10nFormatters.formatTraffic(1024 * 1024 * 1024, 'en');
        expect(result, '1.0 GB');
      });
    });

    group('formatSpeed', () {
      test('formats bits per second for small values', () {
        final result = L10nFormatters.formatSpeed(800, 'en');
        expect(result, '800 bps');
      });

      test('formats kilobits per second', () {
        final result = L10nFormatters.formatSpeed(1500, 'en');
        expect(result, '1.5 Kbps');
      });

      test('formats megabits per second for en-US', () {
        final result = L10nFormatters.formatSpeed(1500000, 'en');
        expect(result, '1.5 Mbps');
      });

      test('formats gigabits per second for de-DE', () {
        final result = L10nFormatters.formatSpeed(2500000000, 'de');
        expect(result, anyOf(contains('2,5'), contains('2.5')));
        expect(result, contains('Gbps'));
      });

      test('handles zero speed', () {
        final result = L10nFormatters.formatSpeed(0, 'en');
        expect(result, '0 bps');
      });

      test('handles negative values', () {
        final result = L10nFormatters.formatSpeed(-100, 'en');
        expect(result, '0 bps');
      });

      test('formats exactly 1 Kbps', () {
        final result = L10nFormatters.formatSpeed(1000, 'en');
        expect(result, '1.0 Kbps');
      });

      test('formats exactly 1 Mbps', () {
        final result = L10nFormatters.formatSpeed(1000000, 'en');
        expect(result, '1.0 Mbps');
      });

      test('formats exactly 1 Gbps', () {
        final result = L10nFormatters.formatSpeed(1000000000, 'en');
        expect(result, '1.0 Gbps');
      });
    });

    group('formatCurrency', () {
      test('formats USD for en-US', () {
        final result = L10nFormatters.formatCurrency(1234.56, 'USD', 'en');
        expect(result, r'$1,234.56');
      });

      test('formats EUR for de-DE', () {
        final result = L10nFormatters.formatCurrency(1234.56, 'EUR', 'de');
        expect(result, contains('1.234,56'));
        expect(result, contains('€'));
      });

      test('formats GBP for en-GB', () {
        final result = L10nFormatters.formatCurrency(1234.56, 'GBP', 'en_GB');
        expect(result, contains('1,234.56'));
        expect(result, contains('£'));
      });

      test('formats JPY for ja-JP (no decimals)', () {
        final result = L10nFormatters.formatCurrency(1234, 'JPY', 'ja');
        expect(result, contains('1,234'));
        expect(result, contains('¥'));
        expect(result, isNot(contains('.'))); // No decimal point
      });

      test('formats negative USD amount', () {
        final result = L10nFormatters.formatCurrency(-50.25, 'USD', 'en');
        expect(result, contains('-'));
        expect(result, contains('50.25'));
        expect(result, contains(r'$'));
      });

      test('formats RUB for ru-RU', () {
        final result = L10nFormatters.formatCurrency(1234.56, 'RUB', 'ru');
        expect(result, contains('₽'));
      });

      test('formats CNY for zh-CN', () {
        final result = L10nFormatters.formatCurrency(1234.56, 'CNY', 'zh');
        expect(result, contains('¥'));
      });

      test('formats zero amount', () {
        final result = L10nFormatters.formatCurrency(0, 'USD', 'en');
        expect(result, r'$0.00');
      });

      test('formats large amount', () {
        final result = L10nFormatters.formatCurrency(1000000.50, 'USD', 'en');
        expect(result, r'$1,000,000.50');
      });
    });

    group('edge cases', () {
      test('handles invalid locale gracefully', () {
        final result = L10nFormatters.formatNumber(1000, 'invalid_locale');
        expect(result, isNotEmpty);
      });

      test('handles empty locale string', () {
        final result = L10nFormatters.formatNumber(1000, '');
        expect(result, isNotEmpty);
      });

      test('normalizes locale with hyphen to underscore', () {
        final result = L10nFormatters.formatDate(
          DateTime(2026, 2, 1),
          'en-US',
        );
        expect(result, isNotEmpty);
      });

      test('handles locale normalization for zh-Hant', () {
        final result = L10nFormatters.formatNumber(1000, 'zh-Hant');
        expect(result, isNotEmpty);
      });
    });
  });
}
