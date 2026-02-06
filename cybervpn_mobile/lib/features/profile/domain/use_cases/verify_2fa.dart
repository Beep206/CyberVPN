import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for verifying a TOTP code during 2FA setup
///
/// After the user configures their authenticator app, they must
/// verify a code to confirm 2FA is working correctly.
@immutable
class Verify2FAUseCase {
  final ProfileRepository _repository;

  const Verify2FAUseCase(this._repository);

  /// Verifies the provided [code] and returns true if valid.
  ///
  /// The [code] must be a 6-digit TOTP code from the authenticator app.
  /// Throws [ArgumentError] if the code format is invalid.
  Future<Result<bool>> call(String code) async {
    if (code.isEmpty || code.length != 6 || !RegExp(r'^\d{6}$').hasMatch(code)) {
      throw ArgumentError('TOTP code must be exactly 6 digits');
    }
    return _repository.verify2FA(code);
  }
}
