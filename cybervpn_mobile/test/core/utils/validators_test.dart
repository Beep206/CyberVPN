import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/utils/input_validators.dart';

void main() {
  // ===========================================================================
  // Email validator tests
  // ===========================================================================

  group('InputValidators.validateEmail', () {
    test('returns null for valid simple email', () {
      expect(InputValidators.validateEmail('user@example.com'), isNull);
    });

    test('returns null for email with subdomain', () {
      expect(InputValidators.validateEmail('user@mail.example.co.uk'), isNull);
    });

    test('returns null for email with plus tag', () {
      expect(InputValidators.validateEmail('user+tag@domain.com'), isNull);
    });

    test('returns null for email with dots in local part', () {
      expect(InputValidators.validateEmail('first.last@domain.com'), isNull);
    });

    test('returns error for null input', () {
      expect(InputValidators.validateEmail(null), isNotNull);
      expect(InputValidators.validateEmail(null), contains('required'));
    });

    test('returns error for empty string', () {
      expect(InputValidators.validateEmail(''), isNotNull);
      expect(InputValidators.validateEmail(''), contains('required'));
    });

    test('returns error for whitespace-only', () {
      expect(InputValidators.validateEmail('   '), isNotNull);
    });

    test('returns error for email without @', () {
      expect(InputValidators.validateEmail('userdomain.com'), isNotNull);
      expect(
        InputValidators.validateEmail('userdomain.com'),
        contains('valid email'),
      );
    });

    test('returns error for email without domain', () {
      expect(InputValidators.validateEmail('user@'), isNotNull);
    });

    test('returns error for email with spaces', () {
      expect(InputValidators.validateEmail('user @domain.com'), isNotNull);
    });

    test('trims whitespace before validation', () {
      // Leading/trailing whitespace should be trimmed
      expect(InputValidators.validateEmail('  user@example.com  '), isNull);
    });
  });

  // ===========================================================================
  // Password validator tests
  // ===========================================================================

  group('InputValidators.validatePassword', () {
    test('returns null for valid password', () {
      expect(InputValidators.validatePassword('Abcdef1g'), isNull);
    });

    test('returns null for strong password', () {
      expect(InputValidators.validatePassword('MyP@ssw0rd!'), isNull);
    });

    test('returns error for null input', () {
      expect(InputValidators.validatePassword(null), isNotNull);
      expect(InputValidators.validatePassword(null), contains('required'));
    });

    test('returns error for empty string', () {
      expect(InputValidators.validatePassword(''), isNotNull);
    });

    test('returns error for password shorter than 8 characters', () {
      expect(InputValidators.validatePassword('Ab1cdef'), isNotNull);
      expect(
        InputValidators.validatePassword('Ab1cdef'),
        contains('8 characters'),
      );
    });

    test('returns null for password with exactly 8 characters', () {
      expect(InputValidators.validatePassword('Abcdefg1'), isNull);
    });

    test('returns error for password without uppercase', () {
      expect(InputValidators.validatePassword('abcdefg1'), isNotNull);
      expect(
        InputValidators.validatePassword('abcdefg1'),
        contains('uppercase'),
      );
    });

    test('returns error for password without lowercase', () {
      expect(InputValidators.validatePassword('ABCDEFG1'), isNotNull);
      expect(
        InputValidators.validatePassword('ABCDEFG1'),
        contains('lowercase'),
      );
    });

    test('returns error for password without digit', () {
      expect(InputValidators.validatePassword('Abcdefgh'), isNotNull);
      expect(
        InputValidators.validatePassword('Abcdefgh'),
        contains('digit'),
      );
    });

    test('returns error for 7-character password (boundary)', () {
      // 7 chars with upper, lower, digit
      expect(InputValidators.validatePassword('Abcde1f'), isNotNull);
    });

    test('returns null for long valid password', () {
      expect(
        InputValidators.validatePassword('A' * 50 + 'a' * 50 + '1'),
        isNull,
      );
    });
  });

  // ===========================================================================
  // Name validator tests
  // ===========================================================================

  group('InputValidators.validateName', () {
    test('returns null for valid name', () {
      expect(InputValidators.validateName('John Doe'), isNull);
    });

    test('returns null for name with hyphen', () {
      expect(InputValidators.validateName('Mary-Jane'), isNull);
    });

    test('returns null for name with apostrophe', () {
      expect(InputValidators.validateName("O'Brien"), isNull);
    });

    test('returns error for null input', () {
      expect(InputValidators.validateName(null), isNotNull);
    });

    test('returns error for empty string', () {
      expect(InputValidators.validateName(''), isNotNull);
    });

    test('returns error for single character', () {
      expect(InputValidators.validateName('A'), isNotNull);
      expect(InputValidators.validateName('A'), contains('2 characters'));
    });

    test('returns null for exactly 2 characters', () {
      expect(InputValidators.validateName('Jo'), isNull);
    });

    test('returns error for name longer than 50 characters', () {
      expect(InputValidators.validateName('A' * 51), isNotNull);
      expect(InputValidators.validateName('A' * 51), contains('50'));
    });

    test('returns null for exactly 50 characters', () {
      expect(InputValidators.validateName('A' * 50), isNull);
    });

    test('returns error for name with digits', () {
      expect(InputValidators.validateName('John123'), isNotNull);
    });

    test('returns error for name with special characters', () {
      expect(InputValidators.validateName('John@Doe'), isNotNull);
    });
  });

  // ===========================================================================
  // Referral code validator tests
  // ===========================================================================

  group('InputValidators.validateReferralCode', () {
    test('returns null for valid 6-char alphanumeric code', () {
      expect(InputValidators.validateReferralCode('ABC123'), isNull);
    });

    test('returns null for valid 20-char code', () {
      expect(InputValidators.validateReferralCode('A' * 20), isNull);
    });

    test('returns null for lowercase input (converted to uppercase)', () {
      // The validator converts to uppercase before matching
      expect(InputValidators.validateReferralCode('abc123'), isNull);
    });

    test('returns error for null input', () {
      expect(InputValidators.validateReferralCode(null), isNotNull);
      expect(
        InputValidators.validateReferralCode(null),
        contains('required'),
      );
    });

    test('returns error for empty string', () {
      expect(InputValidators.validateReferralCode(''), isNotNull);
    });

    test('returns error for code shorter than 6 characters', () {
      expect(InputValidators.validateReferralCode('ABC12'), isNotNull);
    });

    test('returns error for code longer than 20 characters', () {
      expect(InputValidators.validateReferralCode('A' * 21), isNotNull);
    });

    test('returns error for code with special characters', () {
      expect(InputValidators.validateReferralCode('ABC-12'), isNotNull);
    });

    test('returns error for code with spaces', () {
      expect(InputValidators.validateReferralCode('ABC 12'), isNotNull);
    });
  });

  // ===========================================================================
  // Promo code validator tests
  // ===========================================================================

  group('InputValidators.validatePromoCode', () {
    test('returns null for valid promo code', () {
      expect(InputValidators.validatePromoCode('SAVE20'), isNull);
    });

    test('returns null for promo code with hyphens', () {
      expect(InputValidators.validatePromoCode('WINTER-2025'), isNull);
    });

    test('returns null for promo code with underscores', () {
      expect(InputValidators.validatePromoCode('NEW_USER'), isNull);
    });

    test('returns null for 4-char code (minimum)', () {
      expect(InputValidators.validatePromoCode('SAVE'), isNull);
    });

    test('returns null for 30-char code (maximum)', () {
      expect(InputValidators.validatePromoCode('A' * 30), isNull);
    });

    test('returns error for null input', () {
      expect(InputValidators.validatePromoCode(null), isNotNull);
    });

    test('returns error for empty string', () {
      expect(InputValidators.validatePromoCode(''), isNotNull);
    });

    test('returns error for code shorter than 4 characters', () {
      expect(InputValidators.validatePromoCode('ABC'), isNotNull);
    });

    test('returns error for code longer than 30 characters', () {
      expect(InputValidators.validatePromoCode('A' * 31), isNotNull);
    });

    test('returns error for code with spaces', () {
      expect(InputValidators.validatePromoCode('SAVE 20'), isNotNull);
    });

    test('returns error for code with special characters', () {
      expect(InputValidators.validatePromoCode('SAVE@20'), isNotNull);
    });
  });
}
