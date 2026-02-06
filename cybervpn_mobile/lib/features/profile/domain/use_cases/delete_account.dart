import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for permanently deleting the user's account
///
/// This is an irreversible action. Requires password confirmation
/// and a TOTP code if two-factor authentication is enabled.
class DeleteAccountUseCase {
  final ProfileRepository _repository;

  const DeleteAccountUseCase(this._repository);

  /// Deletes the account after validating the provided credentials.
  ///
  /// [password] is always required for confirmation.
  /// [totpCode] is required when [is2FAEnabled] is true.
  ///
  /// Throws [ArgumentError] if password is empty or totpCode is
  /// required but missing/invalid.
  Future<Result<void>> call({
    required String password,
    required bool is2FAEnabled,
    String? totpCode,
  }) async {
    if (password.isEmpty) {
      throw ArgumentError('Password is required to delete account');
    }
    if (is2FAEnabled) {
      if (totpCode == null || totpCode.isEmpty) {
        throw ArgumentError('TOTP code is required when 2FA is enabled');
      }
      if (totpCode.length != 6 || !RegExp(r'^\d{6}$').hasMatch(totpCode)) {
        throw ArgumentError('TOTP code must be exactly 6 digits');
      }
    }
    return _repository.deleteAccount(password, totpCode: totpCode);
  }
}
