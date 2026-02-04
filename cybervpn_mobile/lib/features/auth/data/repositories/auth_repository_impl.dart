import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_remote_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';

class AuthRepositoryImpl with NetworkErrorHandler implements AuthRepository {
  final AuthRemoteDataSource _remoteDataSource;
  final AuthLocalDataSource _localDataSource;
  final NetworkInfo _networkInfo;

  AuthRepositoryImpl({
    required AuthRemoteDataSource remoteDataSource,
    required AuthLocalDataSource localDataSource,
    required NetworkInfo networkInfo,
  })  : _remoteDataSource = remoteDataSource,
        _localDataSource = localDataSource,
        _networkInfo = networkInfo;

  @override
  Future<(UserEntity, String)> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  }) async {
    if (!await _networkInfo.isConnected) {
      throw const NetworkFailure(message: 'No internet connection');
    }
    final (userModel, tokenModel) = await _remoteDataSource.login(
      email: email,
      password: password,
      device: device,
      rememberMe: rememberMe,
    );
    await _localDataSource.cacheToken(tokenModel);
    await _localDataSource.cacheUser(userModel);
    return (userModel.toEntity(), tokenModel.accessToken);
  }

  @override
  Future<(UserEntity, String)> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  }) async {
    if (!await _networkInfo.isConnected) {
      throw const NetworkFailure(message: 'No internet connection');
    }
    final (userModel, tokenModel) = await _remoteDataSource.register(
      email: email,
      password: password,
      device: device,
      referralCode: referralCode,
    );
    await _localDataSource.cacheToken(tokenModel);
    await _localDataSource.cacheUser(userModel);
    return (userModel.toEntity(), tokenModel.accessToken);
  }

  @override
  Future<String> refreshToken({
    required String refreshToken,
    required String deviceId,
  }) async {
    final tokenModel = await _remoteDataSource.refreshToken(
      refreshToken: refreshToken,
      deviceId: deviceId,
    );
    await _localDataSource.cacheToken(tokenModel);
    return tokenModel.accessToken;
  }

  @override
  Future<void> logout({
    required String refreshToken,
    required String deviceId,
  }) async {
    try {
      await _remoteDataSource.logout(
        refreshToken: refreshToken,
        deviceId: deviceId,
      );
    } finally {
      await _localDataSource.clearAuth();
    }
  }

  @override
  Future<UserEntity?> getCurrentUser() async {
    final cached = await _localDataSource.getCachedUser();
    if (cached != null) return cached.toEntity();
    if (!await _networkInfo.isConnected) return null;
    try {
      final userModel = await _remoteDataSource.getCurrentUser();
      await _localDataSource.cacheUser(userModel);
      return userModel.toEntity();
    } catch (_) {
      return null;
    }
  }

  @override
  Future<bool> isAuthenticated() async {
    final token = await _localDataSource.getCachedToken();
    return token != null;
  }
}
