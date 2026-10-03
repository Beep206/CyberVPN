import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/utils/country_code_detector.dart';

void main() {
  group('CountryCodeDetector', () {
    test('detects from flag emojis', () {
      final de = CountryCodeDetector.detect('🇩🇪 Germany Premium 01');
      expect(de.code, 'DE');
      expect(de.name, 'Germany');

      final nl = CountryCodeDetector.detect('Fast-Node 🇳🇱 Amsterdam');
      expect(nl.code, 'NL');
      expect(nl.name, 'Netherlands');

      final ru = CountryCodeDetector.detect('🇷🇺 Москва VIP');
      expect(ru.code, 'RU');
      expect(ru.name, 'Russia');

      final us = CountryCodeDetector.detect('🇺🇸 USA East');
      expect(us.code, 'US');
      expect(us.name, 'United States');
    });

    test('detects from bracketed / tagged ISO codes', () {
      final de = CountryCodeDetector.detect('[DE] Frankfurt-01');
      expect(de.code, 'DE');
      expect(de.name, 'Germany');

      final nl = CountryCodeDetector.detect('(NL) High Speed');
      expect(nl.code, 'NL');
      expect(nl.name, 'Netherlands');

      final fi = CountryCodeDetector.detect('|FI| Helsinki');
      expect(fi.code, 'FI');
      expect(fi.name, 'Finland');
    });

    test('detects from country names in Russian and English', () {
      final ru = CountryCodeDetector.detect('Сервер Россия Санкт-Петербург');
      expect(ru.code, 'RU');
      expect(ru.name, 'Russia');

      final tr = CountryCodeDetector.detect('Турция Стамбул Оптимальный');
      expect(tr.code, 'TR');
      expect(tr.name, 'Turkey');

      final kz = CountryCodeDetector.detect('Казахстан Алматы');
      expect(kz.code, 'KZ');
      expect(kz.name, 'Kazakhstan');

      final jp = CountryCodeDetector.detect('Japan Tokyo Gaming');
      expect(jp.code, 'JP');
      expect(jp.name, 'Japan');
    });

    test('returns XX / Custom when country cannot be determined', () {
      final unknown = CountryCodeDetector.detect('Server 12345 Fast');
      expect(unknown.code, 'XX');
      expect(unknown.name, 'Custom');
      expect(unknown.isIdentified, false);

      final empty = CountryCodeDetector.detect('');
      expect(empty.code, 'XX');
      expect(empty.name, 'Custom');
    });
  });
}
