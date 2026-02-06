import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
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
  Future<Result<(UserEntity, String)>> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  }) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final (userModel, tokenModel) = await _remoteDataSource.login(
        email: email,
        password: password,
        device: device,
        rememberMe: rememberMe,
      );
      await _localDataSource.cacheToken(tokenModel);
      await _localDataSource.cacheUser(userModel);
      return Success((userModel.toEntity(), tokenModel.accessToken));
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<(UserEntity, String)>> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  }) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      final (userModel, tokenModel) = await _remoteDataSource.register(
        email: email,
        password: password,
        device: device,
        referralCode: referralCode,
      );
      await _localDataSource.cacheToken(tokenModel);
      await _localDataSource.cacheUser(userModel);
      return Success((userModel.toEntity(), tokenModel.accessToken));
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<String>> refreshToken({
    required String refreshToken,
    required String deviceId,
  }) async {
    try {
      final tokenModel = await _remoteDataSource.refreshToken(
        refreshToken: refreshToken,
        deviceId: deviceId,
      );
      await _localDataSource.cacheToken(tokenModel);
      return Success(tokenModel.accessToken);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e) {
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> logout({
    required String refreshToken,
    required String deviceId,
  }) async {
    try {
      await _remoteDataSource.logout(
        refreshToken: refreshToken,
        deviceId: deviceId,
      );
    } catch (_) {
      // Swallow remote errors; always clear local auth below.
    } finally {
      await _localDataSource.clearAuth();
    }
    return const Success(null);
  }

  @override
  Future<Result<UserEntity?>> getCurrentUser() async {
    try {
      final cached = await _localDataSource.getCachedUser();
      if (cached != null) return Success(cached.toEntity());
      if (!await _networkInfo.isConnected) return const Success(null);
      final userModel = await _remoteDataSource.getCurrentUser();
      await _localDataSource.cacheUser(userModel);
      return Success(userModel.toEntity());
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (_) {
      return const Success(null);
    }
  }

  @override
  Future<Result<bool>> isAuthenticated() async {
    final token = await _localDataSource.getCachedToken();
    return Success(token != null);
  }
}
