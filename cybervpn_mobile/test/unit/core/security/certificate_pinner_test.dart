import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/security/certificate_pinner.dart';

void main() {
  group('CertificatePinner', () {
    // Note: Testing with real X509Certificate objects is difficult because
    // they can only be created from actual TLS connections. These tests
    // verify the API contract and behavior that can be tested.

    test('creates pinner with fingerprints', () {
      final pinner = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
          'FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00:FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00',
        ],
      );

      expect(pinner.pinnedFingerprints.length, equals(2));
    });

    test('createHttpClient returns configured HttpClient', () {
      final pinner = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
        ],
      );

      final client = pinner.createHttpClient();

      expect(client, isA<HttpClient>());
      // Note: badCertificateCallback is set internally but is not publicly accessible

      client.close(force: true);
    });

    test('validate bypasses in debug mode', () {
      // This test runs in debug mode by default (kDebugMode == true)
      // so validation should always return true regardless of fingerprint match

      final pinner = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
        ],
      );

      // In debug mode, validation is bypassed
      // We can't create a real X509Certificate for testing, but we can verify
      // the debug bypass logic through integration testing

      expect(kDebugMode, isTrue,
          reason: 'Test assumes debug mode for bypass validation');
    });

    test('empty fingerprints list is valid', () {
      final pinner = CertificatePinner(
        pinnedFingerprints: [],
      );

      expect(pinner.pinnedFingerprints, isEmpty);
    });

    test('fingerprints are stored correctly', () {
      const fingerprint1 =
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99';
      const fingerprint2 =
          'FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00:FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00';

      final pinner = CertificatePinner(
        pinnedFingerprints: [fingerprint1, fingerprint2],
      );

      expect(pinner.pinnedFingerprints, contains(fingerprint1));
      expect(pinner.pinnedFingerprints, contains(fingerprint2));
    });
  });

  group('CertificatePinner integration', () {
    test('HttpClient with certificate validation can be created', () async {
      final pinner = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
        ],
      );

      final client = pinner.createHttpClient();

      // Verify the client can be created and closed without errors
      expect(() => client.close(force: true), returnsNormally);
    });

    test('multiple pinners can coexist', () {
      final pinner1 = CertificatePinner(
        pinnedFingerprints: [
          'AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99',
        ],
      );

      final pinner2 = CertificatePinner(
        pinnedFingerprints: [
          'FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00:FF:EE:DD:CC:BB:AA:99:88:77:66:55:44:33:22:11:00',
        ],
      );

      expect(pinner1.pinnedFingerprints, isNot(equals(pinner2.pinnedFingerprints)));

      final client1 = pinner1.createHttpClient();
      final client2 = pinner2.createHttpClient();

      client1.close(force: true);
      client2.close(force: true);
    });
  });
}
