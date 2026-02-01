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

    return null;
  }

  /// Validates a password with the following requirements:
  /// - Minimum 8 characters
  /// - At least one uppercase letter
  /// - At least one lowercase letter
  /// - At least one digit
  static String? validatePassword(String? value) {
    if (value == null || value.isEmpty) {
      return 'Password is required';
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
