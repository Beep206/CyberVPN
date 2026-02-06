import 'package:meta/meta.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';

@immutable
class RefreshTokenUseCase {
  final AuthRepository _repository;

  const RefreshTokenUseCase(this._repository);

  Future<Result<String>> call({
    required String refreshToken,
    required String deviceId,
  }) async {
    if (refreshToken.isEmpty) {
      throw ArgumentError('Refresh token cannot be empty');
    }
    if (deviceId.isEmpty) {
      throw ArgumentError('Device ID cannot be empty');
    }
    return _repository.refreshToken(
      refreshToken: refreshToken,
      deviceId: deviceId,
    );
  }
}
