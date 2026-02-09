/// Utility class providing static validation methods for form inputs
/// throughout the CyberVPN application.
///
/// Each validator returns `null` when the input is valid, or an error
/// message [String] describing the validation failure.
class InputValidators {
  const InputValidators._();

  /// Validates an email address.
  ///
  /// Checks for non-empty input and a valid email pattern.
  static String? validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Email is required';
    }

    final trimmed = value.trim();

    // RFC 5322 simplified pattern
    final emailRegex = RegExp(
      r'^[a-zA-Z0-9.!#$%&*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$',
    );

    if (!emailRegex.hasMatch(trimmed)) {
      return 'Please enter a valid email address';
    }

    // IDN homograph attack detection: reject emails with mixed-script characters
    // that could impersonate legitimate domains (e.g. using Cyrillic 'а' for Latin 'a').
    if (_containsMixedScripts(trimmed.split('@').last)) {
      return 'Email domain contains suspicious characters';
    }

    return null;
  }

  /// Detects mixed Unicode scripts (potential IDN homograph attack).
  ///
  /// Returns `true` if the string contains both Latin and Cyrillic characters,
  /// which is a common homograph attack vector.
  static bool _containsMixedScripts(String domain) {
    final hasLatin = RegExp(r'[a-zA-Z]').hasMatch(domain);
    // Cyrillic range: U+0400-U+04FF
    final hasCyrillic = RegExp(r'[\u0400-\u04FF]').hasMatch(domain);
    return hasLatin && hasCyrillic;
  }

  /// Maximum allowed password length to prevent ReDoS and memory issues.
  static const int maxPasswordLength = 128;

  /// Validates a password with the following requirements:
  /// - Minimum 8 characters, maximum 128
  /// - At least one uppercase letter
  /// - At least one lowercase letter
  /// - At least one digit
  static String? validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Password is required';
    }

    if (value.length > maxPasswordLength) {
      return 'Password must be at most $maxPasswordLength characters';
    }

    if (value.length < 8) {
      return 'Password must be at least 8 characters';
    }

    if (!value.contains(RegExp(r'[A-Z]'))) {
      return 'Password must contain at least one uppercase letter';
    }

    if (!value.contains(RegExp(r'[a-z]'))) {
      return 'Password must contain at least one lowercase letter';
    }

    if (!value.contains(RegExp(r'[0-9]'))) {
      return 'Password must contain at least one digit';
    }

    return null;
  }

  /// Validates a user display name.
  ///
  /// Must be non-empty, between 2 and 50 characters, and contain only
  /// letters, spaces, hyphens, and apostrophes.
  static String? validateName(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Name is required';
    }

    final trimmed = value.trim();

    if (trimmed.length < 2) {
      return 'Name must be at least 2 characters';
    }

    if (trimmed.length > 50) {
      return 'Name must be at most 50 characters';
    }

    final nameRegex = RegExp(r"^[a-zA-Z\s\-']+$");
    if (!nameRegex.hasMatch(trimmed)) {
      return 'Name can only contain letters, spaces, hyphens, and apostrophes';
    }

    return null;
  }

  /// Validates a referral code.
  ///
  /// Must be non-empty and consist of 6-20 alphanumeric characters
  /// (uppercase letters and digits).
  static String? validateReferralCode(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Referral code is required';
    }

    final trimmed = value.trim();

    final codeRegex = RegExp(r'^[A-Z0-9]{6,20}$');
    if (!codeRegex.hasMatch(trimmed.toUpperCase())) {
      return 'Referral code must be 6-20 alphanumeric characters';
    }

    return null;
  }

  /// Validates a username for username-only registration.
  ///
  /// Must be 3-32 characters, containing only alphanumeric characters
  /// and underscores.
  static String? validateUsername(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Username is required';
    }

    final trimmed = value.trim();

    final usernameRegex = RegExp(r'^[a-zA-Z0-9_]{3,32}$');
    if (!usernameRegex.hasMatch(trimmed)) {
      return 'Username must be 3-32 characters: letters, numbers, underscores';
    }

    return null;
  }

  /// Validates a promotional code.
  ///
  /// Must be non-empty and consist of 4-30 alphanumeric characters,
  /// hyphens, or underscores.
  static String? validatePromoCode(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Promo code is required';
    }

    final trimmed = value.trim();

    final promoRegex = RegExp(r'^[A-Za-z0-9\-_]{4,30}$');
    if (!promoRegex.hasMatch(trimmed)) {
      return 'Promo code must be 4-30 characters (letters, digits, hyphens, underscores)';
    }

    return null;
  }
}
