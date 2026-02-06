import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/profile/data/datasources/profile_remote_ds.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/domain/repositories/profile_repository.dart';

/// Repository implementation for user profile management.
///
/// Delegates to [ProfileRemoteDataSource] for all network calls and uses
/// [NetworkErrorHandler] to convert infrastructure exceptions into domain
/// [Failure] types with retry logic for transient errors.
///
/// All methods return [Result<T>] instead of throwing, enabling callers
/// to handle success and failure explicitly via pattern matching.
class ProfileRepositoryImpl
    with NetworkErrorHandler
    implements ProfileRepository {
  final ProfileRemoteDataSource _remoteDataSource;
  final NetworkInfo _networkInfo;

  ProfileRepositoryImpl({
    required ProfileRemoteDataSource remoteDataSource,
    required NetworkInfo networkInfo,
  })  : _remoteDataSource = remoteDataSource,
        _networkInfo = networkInfo;

  // -- Profile --

  @override
  Future<Result<Profile>> getProfile() async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      return Success(await _remoteDataSource.getProfile());
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  // -- Two-Factor Authentication --

  @override
  Future<Result<Setup2FAResult>> setup2FA() async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      return Success(await _remoteDataSource.setup2FA());
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<bool>> verify2FA(String code) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      return Success(await _remoteDataSource.verify2FA(code));
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<bool>> validate2FA(String code) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      return Success(await _remoteDataSource.validate2FA(code));
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> disable2FA(String code) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await _remoteDataSource.disable2FA(code);
      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  // -- OAuth Provider Linking --

  @override
  Future<Result<String>> getOAuthAuthorizationUrl(
    OAuthProvider provider,
  ) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      return Success(
        await _remoteDataSource.getOAuthAuthorizationUrl(provider),
      );
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> completeOAuthLink(
    OAuthProvider provider,
    String code,
  ) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await _remoteDataSource.completeOAuthLink(provider, code);
      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> unlinkOAuth(OAuthProvider provider) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await _remoteDataSource.unlinkOAuth(provider);
      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  // -- Device / Session Management --

  @override
  Future<Result<List<Device>>> getDevices() async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      return Success(await _remoteDataSource.getDevices());
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<Device>> registerDevice({
    required String deviceName,
    required String platform,
    required String deviceId,
  }) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      return Success(await _remoteDataSource.registerDevice(
        deviceName: deviceName,
        platform: platform,
        deviceId: deviceId,
      ));
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<void>> removeDevice(String id) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await _remoteDataSource.removeDevice(id);
      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }

  // -- Account Deletion --

  @override
  Future<Result<void>> deleteAccount(
    String password, {
    String? totpCode,
  }) async {
    if (!await _networkInfo.isConnected) {
      return const Failure(NetworkFailure(message: 'No internet connection'));
    }
    try {
      await _remoteDataSource.deleteAccount(password, totpCode: totpCode);
      return const Success(null);
    } on AppException catch (e) {
      return Failure(mapExceptionToFailure(e));
    } catch (e, st) {
      AppLogger.warning('Unexpected error in ProfileRepository', error: e, stackTrace: st);
      return Failure(UnknownFailure(message: e.toString()));
    }
  }
}
