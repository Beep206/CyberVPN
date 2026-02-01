import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';

abstract class AuthRepository {
  Future<(UserEntity, String)> login({required String email, required String password});
  Future<(UserEntity, String)> register({required String email, required String password, String? referralCode});
  Future<String> refreshToken(String refreshToken);
  Future<void> logout();
  Future<UserEntity?> getCurrentUser();
  Future<bool> isAuthenticated();
}
