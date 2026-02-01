import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/config/environment_config.dart';

void main() {
  group('EnvironmentConfig', () {
    test('baseUrl returns default when no dart-define is provided', () {
      // When no --dart-define=API_BASE_URL is passed at compile time and
      // no .env file has been loaded, the getter must return the hard-coded
      // production URL.
      final url = EnvironmentConfig.baseUrl;
      expect(url, equals('https://api.cybervpn.com'));
    });

    test('environment returns "prod" by default', () {
      final env = EnvironmentConfig.environment;
      expect(env, equals('prod'));
    });

    test('isProd is true by default', () {
      expect(EnvironmentConfig.isProd, isTrue);
    });

    test('isDev is false by default', () {
      expect(EnvironmentConfig.isDev, isFalse);
    });

    test('isStaging is false by default', () {
      expect(EnvironmentConfig.isStaging, isFalse);
    });
  });
}
