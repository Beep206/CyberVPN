import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/input_validators.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';

class LoginUseCase {
  final AuthRepository _repository;

  const LoginUseCase(this._repository);

  Future<Result<(UserEntity, String)>> call({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  }) async {
    final emailError = InputValidators.validateEmail(email);
    if (emailError != null) {
      throw ArgumentError(emailError);
    }
    final passwordError = InputValidators.validatePassword(password);
    if (passwordError != null) {
      throw ArgumentError(passwordError);
    }
    return _repository.login(
      email: email,
      password: password,
      device: device,
      rememberMe: rememberMe,
    );
  }
}
