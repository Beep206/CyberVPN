import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Use case for initiating two-factor authentication setup
///
/// Returns a [Setup2FAResult] containing the TOTP secret and QR code URI
/// that the user needs to configure their authenticator app.
@immutable
class Setup2FAUseCase {
  final ProfileRepository _repository;

  const Setup2FAUseCase(this._repository);

  Future<Result<Setup2FAResult>> call() async {
    return _repository.setup2FA();
  }
}
