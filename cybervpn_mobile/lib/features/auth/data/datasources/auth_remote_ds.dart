import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';

abstract class AuthRemoteDataSource {
  Future<(UserModel, TokenModel)> login({required String email, required String password});
  Future<(UserModel, TokenModel)> register({required String email, required String password, String? referralCode});
  Future<TokenModel> refreshToken(String refreshToken);
  Future<UserModel> getCurrentUser();
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ApiClient _apiClient;

  AuthRemoteDataSourceImpl(this._apiClient);

  @override
  Future<(UserModel, TokenModel)> login({required String email, required String password}) async {
    final response = await _apiClient.post('/auth/login', data: {'email': email, 'password': password});
    final data = response.data as Map<String, dynamic>;
    return (UserModel.fromJson(data['user'] as Map<String, dynamic>), TokenModel.fromJson(data['tokens'] as Map<String, dynamic>));
  }

  @override
  Future<(UserModel, TokenModel)> register({required String email, required String password, String? referralCode}) async {
    final response = await _apiClient.post('/auth/register', data: {
      'email': email, 'password': password, if (referralCode != null) 'referral_code': referralCode,
    });
    final data = response.data as Map<String, dynamic>;
    return (UserModel.fromJson(data['user'] as Map<String, dynamic>), TokenModel.fromJson(data['tokens'] as Map<String, dynamic>));
  }

  @override
  Future<TokenModel> refreshToken(String refreshToken) async {
    final response = await _apiClient.post('/auth/refresh', data: {'refresh_token': refreshToken});
    return TokenModel.fromJson(response.data as Map<String, dynamic>);
  }

  @override
  Future<UserModel> getCurrentUser() async {
    final response = await _apiClient.get('/auth/me');
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }
}
