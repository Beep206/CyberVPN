import 'package:freezed_annotation/freezed_annotation.dart';

part 'antiphishing_code.freezed.dart';

/// Represents a user's antiphishing code used to verify legitimate emails.
///
/// The antiphishing code is displayed in official emails from CyberVPN to help
/// users identify genuine communications and avoid phishing attempts.
@freezed
sealed class AntiphishingCode with _$AntiphishingCode {
  const factory AntiphishingCode({
    /// The user's antiphishing code (null if not set, max 50 characters).
    required String? code,
  }) = _AntiphishingCode;

  const AntiphishingCode._();

  /// Whether the user has set an antiphishing code.
  bool get isSet => code != null && code!.isNotEmpty;

  /// Returns a masked version of the code for display (e.g., "••••••••").
  String get maskedCode => isSet ? '•' * code!.length : '';
}
