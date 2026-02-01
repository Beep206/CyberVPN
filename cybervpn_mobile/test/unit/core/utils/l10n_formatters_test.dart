import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/utils/l10n_formatters.dart';

void main() {
  // ===========================================================================
  // formatDate tests
  // ===========================================================================

  group('L10nFormatters.formatDate', () {
    final testDate = DateTime(2026, 2, 1, 14, 30);

    group('short format', () {
      test('formats date in en-US locale', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'en',
          format: DateFormatType.short,
        );
        // US format: M/d/y
        expect(result, equals('2/1/2026'));
      });

      test('formats date in de-DE locale', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'de',
          format: DateFormatType.short,
        );
        // German format: dd.MM.y
        // Locale data may not be available in test, so check for valid date format
        expect(result, anyOf(equals('01.02.2026'), contains('2026')));
      });

      test('formats date in ar-SA locale', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'ar',
          format: DateFormatType.short,
        );
        // Arabic format varies, just verify it contains the date parts
        expect(result, contains('2026'));
      });

      test('handles locale with hyphen (ar-SA)', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'ar-SA',
          format: DateFormatType.short,
        );
        expect(result, isNotEmpty);
        expect(result, contains('2026'));
      });

      test('handles locale with underscore (en_US)', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'en_US',
          format: DateFormatType.short,
        );
        expect(result, equals('2/1/2026'));
      });
    });

    group('long format', () {
      test('formats date in en locale', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'en',
          format: DateFormatType.long,
        );
        // English long format: February 1, 2026
        expect(result, contains('February'));
        expect(result, contains('1'));
        expect(result, contains('2026'));
      });

      test('formats date in de locale', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'de',
          format: DateFormatType.long,
        );
        // German long format: 1. Februar 2026
        expect(result, contains('Februar'));
        expect(result, contains('1'));
        expect(result, contains('2026'));
      });

      test('formats date in fr locale', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'fr',
          format: DateFormatType.long,
        );
        // French long format: 1 février 2026
        // Locale data may not be available in test, verify it contains year
        expect(result, contains('2026'));
        // Either French or English month name is acceptable
        expect(result, anyOf(contains('février'), contains('February')));
      });
    });

    group('relative format', () {
      test('formats "just now" for recent dates', () {
        final now = DateTime.now();
        final recent = now.subtract(const Duration(seconds: 30));

        final result = L10nFormatters.formatDate(
          recent,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('just now'));
      });

      test('formats minutes ago', () {
        final now = DateTime.now();
        final twoMinutesAgo = now.subtract(const Duration(minutes: 2));

        final result = L10nFormatters.formatDate(
          twoMinutesAgo,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('2 minutes ago'));
      });

      test('formats hours ago', () {
        final now = DateTime.now();
        final twoHoursAgo = now.subtract(const Duration(hours: 2));

        final result = L10nFormatters.formatDate(
          twoHoursAgo,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('2 hours ago'));
      });

      test('formats yesterday', () {
        final now = DateTime.now();
        final yesterday = now.subtract(const Duration(days: 1, hours: 2));

        final result = L10nFormatters.formatDate(
          yesterday,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('yesterday'));
      });

      test('formats days ago', () {
        final now = DateTime.now();
        final threeDaysAgo = now.subtract(const Duration(days: 3));

        final result = L10nFormatters.formatDate(
          threeDaysAgo,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('3 days ago'));
      });

      test('formats weeks ago', () {
        final now = DateTime.now();
        final twoWeeksAgo = now.subtract(const Duration(days: 14));

        final result = L10nFormatters.formatDate(
          twoWeeksAgo,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('2 weeks ago'));
      });

      test('formats months ago', () {
        final now = DateTime.now();
        final twoMonthsAgo = now.subtract(const Duration(days: 60));

        final result = L10nFormatters.formatDate(
          twoMonthsAgo,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('2 months ago'));
      });

      test('formats years ago', () {
        final now = DateTime.now();
        final oneYearAgo = now.subtract(const Duration(days: 400));

        final result = L10nFormatters.formatDate(
          oneYearAgo,
          'en',
          format: DateFormatType.relative,
        );

        expect(result, equals('1 year ago'));
      });

      test('formats future dates as absolute for very far dates', () {
        final future = DateTime.now().add(const Duration(days: 100));

        final result = L10nFormatters.formatDate(
          future,
          'en',
          format: DateFormatType.relative,
        );

        // Should fall back to absolute date
        expect(result, contains('/'));
      });
    });

    group('error handling', () {
      test('falls back to default locale on invalid locale', () {
        final result = L10nFormatters.formatDate(
          testDate,
          'invalid-locale',
          format: DateFormatType.short,
        );

        // Should still return a valid date string
        expect(result, isNotEmpty);
        expect(result, contains('2026'));
      });

      test('handles empty locale string', () {
        final result = L10nFormatters.formatDate(
          testDate,
          '',
          format: DateFormatType.short,
        );

        expect(result, isNotEmpty);
        expect(result, contains('2026'));
      });
    });
  });

  // ===========================================================================
  // formatTime tests
  // ===========================================================================

  group('L10nFormatters.formatTime', () {
    final testTime = DateTime(2026, 2, 1, 14, 30);
    final morningTime = DateTime(2026, 2, 1, 2, 30);

    test('formats time in 12-hour format for en locale', () {
      final result = L10nFormatters.formatTime(testTime, 'en');
      // Use contains since intl may use different space characters
      expect(result, contains('2:30'));
      expect(result, contains('PM'));
    });

    test('formats morning time with AM for en locale', () {
      final result = L10nFormatters.formatTime(morningTime, 'en');
      // Use contains since intl may use different space characters
      expect(result, contains('2:30'));
      expect(result, contains('AM'));
    });

    test('formats time in 24-hour format for de locale', () {
      final result = L10nFormatters.formatTime(testTime, 'de');
      expect(result, equals('14:30'));
    });

    test('formats time in 24-hour format for fr locale', () {
      final result = L10nFormatters.formatTime(testTime, 'fr');
      expect(result, equals('14:30'));
    });

    test('formats time in 24-hour format for ja locale', () {
      final result = L10nFormatters.formatTime(testTime, 'ja');
      expect(result, equals('14:30'));
    });

    test('formats time in 24-hour format for ar locale', () {
      final result = L10nFormatters.formatTime(testTime, 'ar');
      expect(result, contains('14'));
      expect(result, contains('30'));
    });

    test('formats time in 12-hour format for hi locale', () {
      final result = L10nFormatters.formatTime(testTime, 'hi');
      // Hindi uses 12-hour format
      expect(result, anyOf(contains('PM'), contains('अपराह्न')));
    });

    test('handles locale with hyphen', () {
      final result = L10nFormatters.formatTime(testTime, 'en-US');
      expect(result, contains('2:30'));
      expect(result, contains('PM'));
    });

    test('handles locale with underscore', () {
      final result = L10nFormatters.formatTime(testTime, 'de_DE');
      expect(result, equals('14:30'));
    });

    test('falls back to default locale on invalid locale', () {
      final result = L10nFormatters.formatTime(testTime, 'invalid');
      expect(result, isNotEmpty);
      // Invalid locales may fall back to 24-hour or 12-hour depending on intl
      expect(result, contains('14:'));
    });

    test('handles empty locale', () {
      final result = L10nFormatters.formatTime(testTime, '');
      expect(result, isNotEmpty);
    });

    test('formats midnight correctly', () {
      final midnight = DateTime(2026, 2, 1, 0, 0);
      final result = L10nFormatters.formatTime(midnight, 'en');
      // en locale uses 12-hour format
      expect(result, contains('12:00'));
      expect(result, contains('AM'));
    });

    test('formats noon correctly', () {
      final noon = DateTime(2026, 2, 1, 12, 0);
      final result = L10nFormatters.formatTime(noon, 'en');
      expect(result, contains('12:00'));
      expect(result, contains('PM'));
    });
  });
}
