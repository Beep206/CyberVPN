import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';

abstract class AuthRemoteDataSource {
  Future<(UserModel, TokenModel)> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  });
  Future<(UserModel, TokenModel)> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  });
  Future<TokenModel> refreshToken({
    required String refreshToken,
    required String deviceId,
  });
  Future<void> logout({
    required String refreshToken,
    required String deviceId,
  });
  Future<UserModel> getCurrentUser();
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ApiClient _apiClient;

  /// Base path for mobile auth endpoints.
  static const String _basePath = '/mobile/auth';

  AuthRemoteDataSourceImpl(this._apiClient);

  @override
  Future<(UserModel, TokenModel)> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_basePath/login',
      data: {
        'email': email,
        'password': password,
        'device': device.toJson(),
        'remember_me': rememberMe,
      },
    );
    final data = response.data as Map<String, dynamic>;
    return (
      UserModel.fromJson(data['user'] as Map<String, dynamic>),
      TokenModel.fromJson(data['tokens'] as Map<String, dynamic>),
    );
  }

  @override
  Future<(UserModel, TokenModel)> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_basePath/register',
      data: {
        'email': email,
        'password': password,
        'device': device.toJson(),
        if (referralCode != null) 'referral_code': referralCode,
      },
    );
    final data = response.data as Map<String, dynamic>;
    return (
      UserModel.fromJson(data['user'] as Map<String, dynamic>),
      TokenModel.fromJson(data['tokens'] as Map<String, dynamic>),
    );
  }

  @override
  Future<TokenModel> refreshToken({
    required String refreshToken,
    required String deviceId,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      '$_basePath/refresh',
      data: {
        'refresh_token': refreshToken,
        'device_id': deviceId,
      },
    );
    return TokenModel.fromJson(response.data as Map<String, dynamic>);
  }

  @override
  Future<void> logout({
    required String refreshToken,
    required String deviceId,
  }) async {
    await _apiClient.post<Map<String, dynamic>>(
      '$_basePath/logout',
      data: {
        'refresh_token': refreshToken,
        'device_id': deviceId,
      },
    );
  }

  @override
  Future<UserModel> getCurrentUser() async {
    final response = await _apiClient.get<Map<String, dynamic>>('$_basePath/me');
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }
}
