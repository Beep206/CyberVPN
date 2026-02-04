import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';

abstract class AuthRepository {
  Future<(UserEntity, String)> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  });
  Future<(UserEntity, String)> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  });
  Future<String> refreshToken({
    required String refreshToken,
    required String deviceId,
  });
  Future<void> logout({
    required String refreshToken,
    required String deviceId,
  });
  Future<UserEntity?> getCurrentUser();
  Future<bool> isAuthenticated();
}
