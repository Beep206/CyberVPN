import 'package:cybervpn_mobile/core/utils/input_validators.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';

class LoginUseCase {
  final AuthRepository _repository;

  const LoginUseCase(this._repository);

  Future<(UserEntity, String)> call({required String email, required String password}) async {
    final emailError = InputValidators.validateEmail(email);
    if (emailError != null) {
      throw ArgumentError(emailError);
    }
    final passwordError = InputValidators.validatePassword(password);
    if (passwordError != null) {
      throw ArgumentError(passwordError);
    }
    return _repository.login(email: email, password: password);
  }
}
