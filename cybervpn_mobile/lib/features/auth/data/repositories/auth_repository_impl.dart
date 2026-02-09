import 'dart:async';

import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
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
    } catch (e, st) {
      AppLogger.warning('Logout remote call failed', error: e, stackTrace: st);
    } finally {
      await _localDataSource.clearAuth();
    }
    return const Success(null);
  }

  @override
  Future<Result<UserEntity?>> getCurrentUser() async {
    try {
      // Return cached user immediately for fast startup, then validate
      // the session against the server in the background.
      final cached = await _localDataSource.getCachedUser();
      if (cached != null) {
        // Fire-and-forget background validation so splash doesn't block.
        unawaited(_validateSessionInBackground());
        return Success(cached.toEntity());
      }

      // No cached user — must go remote.
      if (await _networkInfo.isConnected) {
        try {
          final userModel = await _remoteDataSource.getCurrentUser();
          await _localDataSource.cacheUser(userModel);
          return Success(userModel.toEntity());
        } catch (e) {
          final token = await _localDataSource.getCachedToken();
          if (token == null) return const Success(null);
          AppLogger.warning('getCurrentUser remote failed, no cache', error: e);
        }
      }

      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('getCurrentUser unexpected error', error: e, stackTrace: st);
      return const Success(null);
    }
  }

  /// Validates the current session in the background.
  /// If the server returns 401 and token refresh fails, clears auth state.
  Future<void> _validateSessionInBackground() async {
    try {
      if (!await _networkInfo.isConnected) return;
      final userModel = await _remoteDataSource.getCurrentUser();
      await _localDataSource.cacheUser(userModel);
    } catch (e) {
      final token = await _localDataSource.getCachedToken();
      if (token == null) {
        AppLogger.info('Background session validation: tokens invalidated', category: 'auth');
      } else {
        AppLogger.warning('Background session validation failed (transient)', error: e, category: 'auth');
      }
    }
  }

  @override
  Future<Result<bool>> isAuthenticated() async {
    final token = await _localDataSource.getCachedToken();
    return Success(token != null);
  }
}
