import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';

abstract class AuthRepository {
  Future<Result<(UserEntity, String)>> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  });
  Future<Result<(UserEntity, String)>> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  });
  Future<Result<String>> refreshToken({
    required String refreshToken,
    required String deviceId,
  });
  Future<Result<void>> logout({
    required String refreshToken,
    required String deviceId,
  });
  Future<Result<UserEntity?>> getCurrentUser();
  Future<Result<bool>> isAuthenticated();
}
