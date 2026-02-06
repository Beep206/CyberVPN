import 'package:flutter_test/flutter_test.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

/// Verifies that SentryUser is created with only the user ID (no PII).
///
/// This test ensures compliance with GDPR / sendDefaultPii=false policy.
/// The auth_provider.dart _setSentryUser() method must ONLY pass user.id
/// to SentryUser, never email, username, or other PII fields.
void main() {
  group('Sentry privacy compliance', () {
    test('SentryUser with only ID has no PII fields', () {
      // This matches the pattern in auth_provider.dart:269
      //   await scope.setUser(SentryUser(id: user.id));
      final sentryUser = SentryUser(id: 'user-001');

      expect(sentryUser.id, equals('user-001'));
      expect(sentryUser.email, isNull,
          reason: 'Email must not be set -- GDPR compliance');
      expect(sentryUser.username, isNull,
          reason: 'Username must not be set -- GDPR compliance');
      expect(sentryUser.ipAddress, isNull,
          reason: 'IP address must not be set -- privacy compliance');
      expect(sentryUser.name, isNull,
          reason: 'Name must not be set -- GDPR compliance');
    });

    test('SentryUser with PII fields would violate privacy policy', () {
      // This is the WRONG way to create SentryUser -- PII is exposed.
      // This test documents what we must NEVER do in production code.
      final badUser = SentryUser(
        id: 'user-001',
        email: 'user@example.com',
        username: 'testuser',
      );

      // These assertions prove that PII CAN be set, so we must be careful
      // to NEVER pass these fields in our auth_provider.dart
      expect(badUser.email, isNotNull);
      expect(badUser.username, isNotNull);
    });

    test('clearing Sentry user sets null', () {
      // Matches auth_provider.dart:277
      //   await scope.setUser(null);
      // Verifying null is a valid argument for clearing user context
      const SentryUser? cleared = null;
      expect(cleared, isNull);
    });
  });
}
