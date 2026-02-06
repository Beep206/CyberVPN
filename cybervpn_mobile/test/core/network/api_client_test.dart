import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';

void main() {
  group('ApiClient - HTTPS enforcement', () {
    test('throws StateError for HTTP URL when isProd is true', () {
      // EnvironmentConfig defaults to prod when no --dart-define is set
      expect(EnvironmentConfig.isProd, isTrue);

      expect(
        () => ApiClient(baseUrl: 'http://api.cybervpn.com'),
        throwsA(isA<StateError>().having(
          (e) => e.message,
          'message',
          contains('Production API base URL must use HTTPS'),
        )),
      );
    });

    test('throws StateError for HTTP localhost in production', () {
      expect(EnvironmentConfig.isProd, isTrue);

      expect(
        () => ApiClient(baseUrl: 'http://localhost:8000'),
        throwsA(isA<StateError>()),
      );
    });

    test('accepts HTTPS URL in production', () {
      expect(EnvironmentConfig.isProd, isTrue);

      // Should not throw
      final client = ApiClient(baseUrl: 'https://api.cybervpn.com');
      expect(client, isNotNull);
    });
  });
}
