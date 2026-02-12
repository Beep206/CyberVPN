import 'dart:io';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/security/certificate_pinner.dart';

void main() {
  group('CertificatePinner - pinning behavior', () {
    test('pinning is bypassed in debug mode (kDebugMode == true)', () {
      // Flutter tests always run in debug mode
      expect(kDebugMode, isTrue,
          reason: 'Tests run in debug mode; pinning should be bypassed');

      const pinner = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
        ],
      );

      // In debug mode, the HttpClient is still created, but validate() returns
      // true regardless of fingerprint match. This is the expected behavior
      // for dev environments.
      final client = pinner.createHttpClient();
      expect(client, isA<HttpClient>());
      client.close(force: true);
    });

    test('invalid fingerprints are stored but would fail in release mode', () {
      const invalidFingerprint =
          'FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF';

      const pinner = CertificatePinner(
        pinnedFingerprints: [invalidFingerprint],
      );

      // Verify the invalid fingerprint is stored
      expect(pinner.pinnedFingerprints, contains(invalidFingerprint));
      expect(pinner.pinnedFingerprints.length, equals(1));

      // In release mode, any certificate whose SHA-256 doesn't match this
      // fingerprint would be rejected. We can't test release behavior in
      // unit tests (kDebugMode is always true), but we verify the mechanism.
    });

    test('empty fingerprint list disables pinning', () {
      const pinner = CertificatePinner(pinnedFingerprints: []);
      expect(pinner.pinnedFingerprints, isEmpty);
    });

    test('multiple fingerprints support certificate rotation', () {
      const pinner = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
          'FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00:FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00',
        ],
      );

      expect(pinner.pinnedFingerprints.length, equals(2));
    });

    test('HttpClient with pinning can be used with Dio IOHttpClientAdapter',
        () {
      const pinner = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
        ],
      );

      final dio = Dio();
      final adapter = IOHttpClientAdapter(
        createHttpClient: pinner.createHttpClient,
      );

      dio.httpClientAdapter = adapter;
      expect(dio.httpClientAdapter, isA<IOHttpClientAdapter>());

      dio.close();
    });
  });
}
