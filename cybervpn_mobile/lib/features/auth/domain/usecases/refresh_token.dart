import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';

class RefreshTokenUseCase {
  final AuthRepository _repository;

  const RefreshTokenUseCase(this._repository);

  Future<String> call(String refreshToken) async {
    if (refreshToken.isEmpty) {
      throw ArgumentError('Refresh token cannot be empty');
    }
    return _repository.refreshToken(refreshToken);
  }
}
