import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('EnvironmentConfig - Sentry contract', () {
    test('reads environment, DSN and release from dart-define', () {
      const configuredEnvironment = String.fromEnvironment('API_ENV');
      if (configuredEnvironment.isEmpty) {
        expect(EnvironmentConfig.environment, equals('prod'));
        expect(EnvironmentConfig.sentryDsn, isEmpty);
        expect(EnvironmentConfig.sentryRelease, isEmpty);
        return;
      }

      expect(EnvironmentConfig.environment, equals('staging'));
      expect(
        EnvironmentConfig.sentryDsn,
        equals('https://mobile@example.com/1'),
      );
      expect(
        EnvironmentConfig.sentryRelease,
        equals('cybervpn-mobile@1.0.0+1'),
      );
    });
  });
}
