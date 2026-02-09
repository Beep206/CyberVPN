import 'dart:ui' show Locale;

import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/locale_config.dart';

void main() {
  group('LocaleConfig', () {
    test('supportedLocaleCodes has 36 locales', () {
      expect(LocaleConfig.supportedLocaleCodes.length, equals(38));
    });

    test('defaultLocaleCode is en', () {
      expect(LocaleConfig.defaultLocaleCode, equals('en'));
    });

    test('rtlLocaleCodes contains ar, he, fa, ur, ku', () {
      expect(
        LocaleConfig.rtlLocaleCodes,
        containsAll(['ar', 'he', 'fa', 'ur', 'ku']),
      );
      expect(LocaleConfig.rtlLocaleCodes.length, equals(5));
    });

    test('localeFromCode handles simple language codes', () {
      final locale = LocaleConfig.localeFromCode('en');
      expect(locale, equals(const Locale('en')));
    });

    test('isRtl returns true for RTL locales', () {
      expect(LocaleConfig.isRtl('ar'), isTrue);
      expect(LocaleConfig.isRtl('he'), isTrue);
      expect(LocaleConfig.isRtl('fa'), isTrue);
      expect(LocaleConfig.isRtl('ur'), isTrue);
      expect(LocaleConfig.isRtl('ku'), isTrue);
    });

    test('isRtl returns false for LTR locales', () {
      expect(LocaleConfig.isRtl('en'), isFalse);
      expect(LocaleConfig.isRtl('ru'), isFalse);
      expect(LocaleConfig.isRtl('zh'), isFalse);
      expect(LocaleConfig.isRtl('hi'), isFalse);
    });

    test('da and zh_Hant are NOT present', () {
      expect(LocaleConfig.supportedLocaleCodes.contains('da'), isFalse);
      expect(LocaleConfig.supportedLocaleCodes.contains('zh_Hant'), isFalse);
    });

    test('all 38 expected locale codes are present', () {
      final expected = [
        // High priority
        'en', 'hi', 'id', 'ru', 'zh',
        // Medium priority
        'ar', 'fa', 'tr', 'vi', 'ur',
        // Low priority
        'th', 'bn', 'ms', 'es', 'kk', 'be', 'my', 'uz',
        // Non-viable
        'ha', 'yo', 'ku', 'am', 'fr', 'tk',
        // Additional (14)
        'ja', 'ko', 'he', 'de', 'pt', 'it', 'nl', 'pl',
        'fil', 'uk', 'cs', 'ro', 'hu', 'sv',
      ];
      // User listed 36, but Additional group actually has 14 items = 38 total
      expect(expected.length, equals(38));
      for (final code in expected) {
        expect(
          LocaleConfig.supportedLocaleCodes.contains(code),
          isTrue,
          reason: 'Missing locale code: $code',
        );
      }
    });

    test('localeFromCode produces valid Locale for each supported code', () {
      for (final code in LocaleConfig.supportedLocaleCodes) {
        final locale = LocaleConfig.localeFromCode(code);
        expect(locale.languageCode, isNotEmpty,
            reason: 'Invalid locale for code: $code');
      }
    });
  });
}
