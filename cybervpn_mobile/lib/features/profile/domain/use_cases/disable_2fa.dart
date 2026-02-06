import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for disabling two-factor authentication
///
/// Requires a valid TOTP code to confirm the user has access
/// to their authenticator before removing 2FA protection.
@immutable
class Disable2FAUseCase {
  final ProfileRepository _repository;

  const Disable2FAUseCase(this._repository);

  /// Disables 2FA using the provided TOTP [code] for verification.
  ///
  /// Throws [ArgumentError] if the code format is invalid.
  Future<Result<void>> call(String code) async {
    if (code.isEmpty || code.length != 6 || !RegExp(r'^\d{6}$').hasMatch(code)) {
      throw ArgumentError('TOTP code must be exactly 6 digits');
    }
    return _repository.disable2FA(code);
  }
}
