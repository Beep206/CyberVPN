import 'dart:ui' show Locale;

import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/locale_config.dart';

void main() {
  group('LocaleConfig', () {
    test('supportedLocaleCodes has 27 locales', () {
      expect(LocaleConfig.supportedLocaleCodes.length, equals(27));
    });

    test('defaultLocaleCode is en', () {
      expect(LocaleConfig.defaultLocaleCode, equals('en'));
    });

    test('rtlLocaleCodes contains ar, he, fa', () {
      expect(LocaleConfig.rtlLocaleCodes, containsAll(['ar', 'he', 'fa']));
      expect(LocaleConfig.rtlLocaleCodes.length, equals(3));
    });

    test('localeFromCode handles simple language codes', () {
      final locale = LocaleConfig.localeFromCode('en');
      expect(locale, equals(const Locale('en')));
    });

    test('localeFromCode handles script-based codes (zh_Hant)', () {
      final locale = LocaleConfig.localeFromCode('zh_Hant');
      expect(locale.languageCode, equals('zh'));
      expect(locale.scriptCode, equals('Hant'));
    });

    test('isRtl returns true for RTL locales', () {
      expect(LocaleConfig.isRtl('ar'), isTrue);
      expect(LocaleConfig.isRtl('he'), isTrue);
      expect(LocaleConfig.isRtl('fa'), isTrue);
    });

    test('isRtl returns false for LTR locales', () {
      expect(LocaleConfig.isRtl('en'), isFalse);
      expect(LocaleConfig.isRtl('ru'), isFalse);
      expect(LocaleConfig.isRtl('zh'), isFalse);
    });

    test('all expected locale codes are present', () {
      final expected = [
        'en', 'ru', 'de', 'fr', 'es', 'pt', 'it', 'nl', 'pl', 'uk',
        'tr', 'ja', 'ko', 'zh', 'zh_Hant', 'ar', 'he', 'fa', 'hi',
        'th', 'vi', 'id', 'ms', 'ro', 'cs', 'sv', 'da',
      ];
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
