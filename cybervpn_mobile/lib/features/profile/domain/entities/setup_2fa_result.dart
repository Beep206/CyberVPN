import 'package:freezed_annotation/freezed_annotation.dart';

part 'setup_2fa_result.freezed.dart';

/// Result of initiating 2FA setup
///
/// Contains the secret key and QR code data needed for the user
/// to configure their authenticator app.
@freezed
sealed class Setup2FAResult with _$Setup2FAResult {
  const factory Setup2FAResult({
    /// The TOTP secret key for manual entry
    required String secret,

    /// The otpauth:// URI for QR code generation
    required String qrCodeUri,
  }) = _Setup2FAResult;
}
