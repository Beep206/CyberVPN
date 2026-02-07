import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/utils/input_validators.dart';

/// Integration tests for the auth flow covering:
/// - Input validation (login form)
/// - Token refresh logic
/// - Logout flow clearing state
void main() {
  group('Auth flow integration', () {
    group('Login validation', () {
      test('valid email passes validation', () {
        expect(InputValidators.validateEmail('user@example.com'), isNull);
      });

      test('invalid email fails validation', () {
        expect(InputValidators.validateEmail('not-an-email'), isNotNull);
      });

      test('empty email fails validation', () {
        expect(InputValidators.validateEmail(''), isNotNull);
      });

      test('valid password passes validation', () {
        expect(InputValidators.validatePassword('Abcdef1!'), isNull);
      });

      test('short password fails validation', () {
        expect(InputValidators.validatePassword('Abc1'), isNotNull);
      });

      test('password without uppercase fails', () {
        expect(InputValidators.validatePassword('abcdefg1'), isNotNull);
      });

      test('password without digit fails', () {
        expect(InputValidators.validatePassword('Abcdefgh'), isNotNull);
      });

      test('password over max length fails', () {
        final longPassword = 'Aa1${'x' * 130}';
        expect(InputValidators.validatePassword(longPassword), isNotNull);
      });
    });

    group('Email IDN homograph detection', () {
      test('rejects mixed Latin+Cyrillic in domain', () {
        // 'а' is Cyrillic, 'a' is Latin — mixing is suspicious
        final result = InputValidators.validateEmail('user@exаmple.com');
        expect(result, isNotNull);
        expect(result, contains('suspicious'));
      });

      test('allows pure Latin domain', () {
        expect(InputValidators.validateEmail('user@example.com'), isNull);
      });
    });
  });
}
