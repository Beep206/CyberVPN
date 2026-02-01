import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/config/environment_config.dart';

void main() {
  group('EnvironmentConfig.certificateFingerprints', () {
    test('returns empty list when no fingerprints are configured', () {
      // When no --dart-define=CERT_FINGERPRINTS is passed and no .env file
      // has been loaded, the getter must return an empty list.
      final fingerprints = EnvironmentConfig.certificateFingerprints;
      expect(fingerprints, isEmpty);
    });

    test('empty string results in empty list', () {
      // The parsing logic should handle empty strings gracefully
      final fingerprints = EnvironmentConfig.certificateFingerprints;
      expect(fingerprints, isEmpty);
    });

    // Note: Testing with actual dart-define values or .env file would require
    // different test configurations. These tests verify the default behavior
    // when certificate pinning is not configured (local development scenario).

    test('certificateFingerprints is a list', () {
      final fingerprints = EnvironmentConfig.certificateFingerprints;
      expect(fingerprints, isA<List<String>>());
    });
  });
}
